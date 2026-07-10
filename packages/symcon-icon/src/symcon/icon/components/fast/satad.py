"""``SaturationAdjustment(Stepper)`` — the icon4py satad granule on symcon state (S07).

The scientific kernel is icon4py's saturation-adjustment granule (microphysics
package, REFERENCES.lock id ``icon4py-satad``): Newton iteration on T at
constant total density with the latent-heat closure ``lwdocvd = L_v(T)/cvd``
(cvd bookkeeping — satad's ICON path implies cvd, never cpd; ``mo_satad.f90``,
REFERENCES.lock id ``icon-fortran-satad``). symcon does not re-plumb the
granule's internals: ``array_call`` builds zero-copy gt4py views of the
boundary buffers (:mod:`symcon.core.ingress.gt4py`) and invokes
``granule.run(...)`` exactly as icon4py's own integration test does, then
applies the returned tendencies over the timestep — ``x_new = x + dx/dt·Δt`` is
icon4py's own verification arithmetic against the satad-exit savepoints.

Coupling position (tutorial §3.7.2, REFERENCES.lock id ``icon-tutorial-2025``):
fast physics is time-split ("also known as sequential-update split"); satad
appears **twice** in the NWP fast-physics sequence — after the surface-transfer
scheme, and again after microphysics so that vapor and liquid are in
equilibrium before the slow physics. Hence
``coupling_constraints.admissible_operators = {"sequential_update_splitting"}``:
satad as an adjustment-type ``Stepper`` enters SUS chains directly and is not
admissible under the tendency-summing operator families.

Differentiability: ``differentiable: "custom"`` is *declared* on the contract
now (architecture §8.6 — the fixed point differentiates through an implicit
custom rule, not through recorded Newton iterations); the actual rules are
deferred to S10.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, Final, cast

import numpy as np

from symcon.core.components.base import Stepper
from symcon.core.context import ComputeContext
from symcon.core.coupling.constraints import CouplingConstraints
from symcon.core.ingress.gt4py import Backend, resolve_backend
from symcon.core.typing import FieldBuffer
from symcon.icon import names as _names  # noqa: F401  (registry seed side effect)
from symcon.icon.components.fast._column_grid import column_icon4py_grid
from symcon.icon.grid.vertical import VerticalGrid

__all__ = ["SaturationAdjustment", "SaturationAdjustmentConfig"]

_COLUMN_DIMS: Final[tuple[str, str]] = ("cell", "height")


@dataclasses.dataclass(frozen=True)
class SaturationAdjustmentConfig:
    """satad configuration (mirrors icon4py ``SaturationAdjustmentConfig``).

    Defaults transcribed from icon4py v0.2.0 (REFERENCES.lock ``icon4py-satad``):
    "in ICON, 10 is always used for max iteration when subroutine satad_v_3D is
    called" / "1.e-3 is always used for the tolerance".
    """

    #: Maximum Newton iterations before ``ConvergenceError``.
    max_iter: int = 10
    #: Convergence tolerance on the iterated temperature [K].
    tolerance: float = 1.0e-3


class SaturationAdjustment(Stepper):
    """Saturation adjustment on the column/grid state (frozen interface, SPEC S07).

    ``SaturationAdjustment(grid_or_column, cfg, ctx)`` — ``grid_or_column`` is
    either

    - a :class:`symcon.icon.grid.vertical.VerticalGrid` (**column path**): the
      horizontal extent is discovered from the state at the first call and a
      trivial pointwise icon4py grid is built around it; or
    - an ``(icon4py_grid, icon4py_vertical_grid)`` pair (**host-grid path**):
      the granule is hosted on an existing icon4py grid exactly as icon4py's
      own tests build it (the L2 datatest path).

    State names are the S06 registry rows (``air_temperature``,
    ``specific_humidity``, ``specific_cloud_content``, ``air_density``); the
    T-based granule formulation was chosen because it is the variant with
    serialized ICON reference data (PLAN pitfall; the θv/exner-coupled variant
    does not exist as a granule — the muphys variant differs in physics, see
    REFERENCES.lock ``icon4py-muphys-satad``).

    Adjustment happens on levels ``kstart_moist ≤ k < nlev`` (moist physics
    domain); above it the outputs equal the inputs.
    """

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K"},
        "specific_humidity": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_cloud_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "air_density": {"dims": _COLUMN_DIMS, "units": "kg m-3"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K", "differentiable": "custom"},
        "specific_humidity": {"dims": _COLUMN_DIMS, "units": "1", "differentiable": "custom"},
        "specific_cloud_content": {
            "dims": _COLUMN_DIMS,
            "units": "1",
            "differentiable": "custom",
        },
    }

    #: tutorial §3.7.2: fast physics is sequential-update split; see module docstring.
    coupling_constraints: ClassVar[CouplingConstraints] = CouplingConstraints(
        admissible_operators=("sequential_update_splitting",)
    )

    def __init__(
        self,
        grid_or_column: VerticalGrid | tuple[Any, Any],
        cfg: SaturationAdjustmentConfig | None = None,
        ctx: ComputeContext | None = None,
        *,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        self.config = cfg if cfg is not None else SaturationAdjustmentConfig()
        self._backend: Backend = resolve_backend(self.ctx.backend)

        if isinstance(grid_or_column, VerticalGrid):
            self._vertical = grid_or_column
            # icon4py vertical-params adapter of the S06 grid (friend access within
            # symcon.icon; public exposure proposed in S07 STATUS.md).
            self._i4_vertical = grid_or_column._i4_grid
            self._i4_grid: Any | None = None  # built per horizontal extent, lazily
            self._nlev = grid_or_column.nlev
        else:
            i4_grid, i4_vertical = grid_or_column
            self._vertical = None
            self._i4_vertical = i4_vertical
            self._i4_grid = i4_grid
            self._nlev = int(i4_grid.num_levels)

        # granule + private tendency fields, built once per horizontal extent.
        self._bound: dict[int, tuple[Any, tuple[Any, Any, Any]]] = {}

    # -- granule hosting ---------------------------------------------------------

    def _granule(self, n_cell: int) -> tuple[Any, tuple[Any, Any, Any]]:
        bound = self._bound.get(n_cell)
        if bound is None:
            from icon4py.model.atmosphere.subgrid_scale_physics.microphysics import (
                saturation_adjustment as i4_satad,
            )
            from icon4py.model.common import dimension as i4_dims
            from icon4py.model.common.utils import data_allocation as data_alloc

            grid = self._i4_grid
            if grid is None:
                grid = column_icon4py_grid(n_cell, self._nlev)
            elif int(grid.num_cells) != n_cell:
                raise ValueError(
                    f"component {self.name!r}: state has {n_cell} cells but the "
                    f"hosting icon4py grid has {int(grid.num_cells)}."
                )
            gt4py_backend = self._backend.gt4py_backend

            def _cell_k_field(dtype: Any = np.float64) -> Any:
                return data_alloc.zero_field(
                    grid, i4_dims.CellDim, i4_dims.KDim, dtype=dtype, allocator=gt4py_backend
                )

            # ddqz_z_full is stored but not consumed by run() at icon4py v0.2.0
            # (REFERENCES.lock icon4py-satad); a zero field satisfies the ctor.
            metric_state = i4_satad.MetricStateSaturationAdjustment(ddqz_z_full=_cell_k_field())
            granule = i4_satad.SaturationAdjustment(
                config=i4_satad.SaturationAdjustmentConfig(
                    max_iter=self.config.max_iter, tolerance=self.config.tolerance
                ),
                grid=grid,
                vertical_params=self._i4_vertical,
                metric_state=metric_state,
                backend=gt4py_backend,
            )
            tendencies = (_cell_k_field(), _cell_k_field(), _cell_k_field())
            bound = (granule, tendencies)
            self._bound[n_cell] = bound
        return bound

    # -- the ABI hook --------------------------------------------------------------

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None  # Stepper: enforced by the base class
        temperature = inputs["air_temperature"]
        qv = inputs["specific_humidity"]
        qc = inputs["specific_cloud_content"]
        rho = inputs["air_density"]

        n_cell, n_lev = temperature.shape
        if n_lev != self._nlev:
            raise ValueError(
                f"component {self.name!r}: state has {n_lev} levels but the "
                f"vertical grid has {self._nlev}."
            )
        granule, (t_tend, qv_tend, qc_tend) = self._granule(int(n_cell))

        from icon4py.model.common import dimension as i4_dims

        dims = (i4_dims.CellDim, i4_dims.KDim)
        view = self._backend.as_field  # zero-copy §2.3 ingress (aliases the buffers)

        # The granule writes tendencies only on the moist domain
        # [start_cell_nudging:end_cell_local, kstart_moist:nlev]; zero the private
        # fields per call so outside points carry an exact zero tendency.
        for tend in (t_tend, qv_tend, qc_tend):
            tend.ndarray[...] = 0.0

        dtime = timestep.total_seconds()
        granule.run(
            dtime=dtime,
            rho=view(dims, rho),
            temperature=view(dims, temperature),
            qv=view(dims, qv),
            qc=view(dims, qc),
            temperature_tendency=t_tend,
            qv_tendency=qv_tend,
            qc_tendency=qc_tend,
        )

        # icon4py's own verification arithmetic (their integration test):
        # x_exit = x_init + dx/dt * dtime, everywhere on the field.
        out_t = cast(Any, outputs["air_temperature"])
        out_qv = cast(Any, outputs["specific_humidity"])
        out_qc = cast(Any, outputs["specific_cloud_content"])
        out_t[...] = cast(Any, temperature) + t_tend.ndarray * dtime
        out_qv[...] = cast(Any, qv) + qv_tend.ndarray * dtime
        out_qc[...] = cast(Any, qc) + qc_tend.ndarray * dtime
