"""``SaturationAdjustment(Stepper)`` — the icon4py satad granule on ICON-sc state (S07).

The scientific kernel is icon4py's saturation-adjustment granule (microphysics
package, REFERENCES.lock id ``icon4py-satad``): Newton iteration on T at
constant total density with the latent-heat closure ``lwdocvd = L_v(T)/cvd``
(cvd bookkeeping — satad's ICON path implies cvd, never cpd; ``mo_satad.f90``,
REFERENCES.lock id ``icon-fortran-satad``). ICON-sc does not re-plumb the
granule's internals: ``array_call`` builds zero-copy gt4py views of the
boundary buffers (:mod:`icon_sc.core.ingress.gt4py`) and invokes
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

Differentiability: ``differentiable: "custom"`` (architecture §8.6) — since S10
the granule is paired with a functional core co-located in this module
(:func:`_satad_functional`, invoked through ``functional_call``): the saturation
fixed point ``f(T*) = T* - T + (L(T)/cvd)·(qsat_rho(T*, rho) - qv) = 0`` is solved
by the granule's own masked Newton iteration (same per-point freeze/convergence
semantics, bounded ``while_loop``) wrapped in the
:func:`icon_sc.core.functional.rules.implicit_fixed_point` ``lax.custom_root``
rule, so both AD modes differentiate through the *implicit function* — the
adjoint of the Newton solve via the IFT, never through recorded iterations
(which also sidesteps ``while_loop``'s reverse-mode prohibition). Closures and
constants come from ``satad_constants.py`` (one scheme-constants module per
scheme, §11.8). jax imports stay inside the functional entry points.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, Final, cast

import numpy as np

from icon_sc.core.components.base import Stepper
from icon_sc.core.context import ComputeContext
from icon_sc.core.coupling.constraints import CouplingConstraints
from icon_sc.core.ingress.gt4py import Backend, resolve_backend
from icon_sc.core.typing import FieldBuffer
from icon_sc.icon import names as _names  # noqa: F401  (registry seed side effect)
from icon_sc.icon._constants import ALV, CLW, CVD, RV, TMELT
from icon_sc.icon.components.fast import satad_constants as sconst
from icon_sc.icon.components.fast._column_grid import column_icon4py_grid
from icon_sc.icon.grid.vertical import VerticalGrid

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

    - a :class:`icon_sc.icon.grid.vertical.VerticalGrid` (**column path**): the
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
            # icon_sc.icon; public exposure proposed in S07 STATUS.md).
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

    # -- the §8.6 functional core (S10, `custom` route) ------------------------------

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        """Pure JAX evaluation of one satad step (§8.6 ``custom``; SPEC S10).

        Same boundary as :meth:`array_call`; reverse/forward derivatives cross
        the saturation fixed point through the IFT ``custom_root`` rule, not the
        Newton iterations. No tunable ``params``: ``max_iter``/``tolerance`` are
        solver controls, not scheme physics.
        """
        del params
        return _satad_functional(
            dt=dt,
            temperature=inputs["air_temperature"],
            qv=inputs["specific_humidity"],
            qc=inputs["specific_cloud_content"],
            rho=inputs["air_density"],
            tolerance=self.config.tolerance,
            max_iter=self.config.max_iter,
            kstart_moist=int(self._i4_vertical.kstart_moist),
        )


# --------------------------------------------------------------------------------------
# The JAX functional core (S10) — a port of icon4py's satad stencils (REFERENCES.lock
# ``icon4py-satad-stencils``) with the fixed point differentiated implicitly.
# --------------------------------------------------------------------------------------


def _satad_functional(
    *,
    dt: float,
    temperature: Any,
    qv: Any,
    qc: Any,
    rho: Any,
    tolerance: float,
    max_iter: int,
    kstart_moist: int,
) -> dict[str, Any]:
    """One satad step on (cell, height) arrays — pure, traced, fp64."""
    import jax.numpy as jnp

    from icon_sc.core.functional.rules import implicit_fixed_point, masked_newton_solve

    C = sconst

    def latent_heat_vaporization(t: Any) -> Any:
        # Kirchhoff closure, the granule's local cp_v literal (NOT the model CPV).
        return ALV + (C.CP_V - CLW) * (t - TMELT) - RV * t

    def sat_pres_water(t: Any) -> Any:
        return C.TETENS_P0 * jnp.exp(C.TETENS_AW * (t - TMELT) / (t - C.TETENS_BW))

    def qsat_rho(t: Any) -> Any:
        return sat_pres_water(t) / (rho * RV * t)

    def dqsatdT_rho(t: Any, zqsat: Any) -> Any:
        beta = C.TETENS_DER / (t - C.TETENS_BW) ** 2 - 1.0 / t
        return beta * zqsat

    nlev = int(temperature.shape[-1])
    k_index = jnp.arange(nlev)
    moist = k_index >= kstart_moist  # (height,), broadcasts over (cell, height)

    # Subsaturated shortcut: evaporate all cloud water, check saturation there.
    lwdocvd = latent_heat_vaporization(temperature) / CVD
    t_all_evaporated = temperature - lwdocvd * qc
    subsaturated = qv + qc <= qsat_rho(t_all_evaporated)

    # The saturation fixed point, solved with the granule's own masked Newton
    # (per-point freeze at |ΔT| <= tolerance, global loop while any active,
    # bounded by max_iter) and differentiated through the IFT.
    def residual(t_new: Any) -> Any:
        return t_new - temperature + lwdocvd * (qsat_rho(t_new) - qv)

    def residual_prime(t_new: Any) -> Any:
        return 1.0 + lwdocvd * dqsatdT_rho(t_new, qsat_rho(t_new))

    def solve(_f: Any, x0: Any) -> Any:
        return masked_newton_solve(
            residual,
            residual_prime,
            x0,
            active0=~subsaturated & moist,
            tolerance=tolerance,
            max_iter=max_iter,
        )

    t_star = implicit_fixed_point(residual, temperature, solve)

    t_new = jnp.where(subsaturated, t_all_evaporated, t_star)
    t_tendency = (t_new - temperature) / dt
    qv_tendency = jnp.where(subsaturated, qc / dt, (qsat_rho(t_star) - qv) / dt)
    qc_tendency = jnp.where(
        subsaturated,
        -qc / dt,
        (jnp.maximum(qv + qc - qsat_rho(t_star), C.ZQWMIN) - qc) / dt,
    )

    # Moist-domain masking (granule domain [kstart_moist:nlev)): exact zeros above.
    t_tendency = jnp.where(moist, t_tendency, 0.0)
    qv_tendency = jnp.where(moist, qv_tendency, 0.0)
    qc_tendency = jnp.where(moist, qc_tendency, 0.0)

    # icon4py's own verification arithmetic: x_exit = x_init + dx/dt * dt.
    return {
        "air_temperature": temperature + t_tendency * dt,
        "specific_humidity": qv + qv_tendency * dt,
        "specific_cloud_content": qc + qc_tendency * dt,
    }
