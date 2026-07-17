"""``HorizontalDiffusion(Stepper)`` — icon4py ``Diffusion`` hosted on symcon (S13).

The ICON horizontal diffusion granule (Smagorinsky + 4th-order background,
``mo_nh_diffusion.f90`` / ``hdiff_order=5``) as one symcon component, following the
S12 hosting policy (wrap-don't-rewrite, architecture §4.4): the ~16 stencil programs
stay icon4py granule internals (REFERENCES.lock ``icon4py-diffusion``); symcon invokes
the granule's single public entry ``run(diagnostic_state, prognostic_state, dtime,
initial_run)`` exactly the way icon4py's own integration tests and driver do
(REFERENCES.lock ``icon4py-diffusion-tests``, ``icon4py-driver-jw``).

Boundary: prognostics in/out on their locations — ``icon:normal_wind`` (edgexK),
``upward_air_velocity_on_interface_levels`` (cellxK+1), ``icon:exner_function`` and
``icon:virtual_potential_temperature`` (cellxK). ``air_density`` is deliberately *not*
part of the boundary: the granule never reads or writes rho (its ``PrognosticState``
slot is satisfied by a private zero field). One ``__call__`` = one diffusion step over
the full Δt — ICON applies diffusion once per physics timestep, after the dynamics
substepping (driver ``_integrate_one_time_step``; ``mo_nh_stepping.f90``).

ICON's *initial stabilization run* ("for real-data runs, perform an extra diffusion
call before the first time step") is exposed as :meth:`initial_stabilization` — an
extra, explicitly requested call that uses the granule's ``initial_run=True`` special
coefficients; it never happens implicitly.

The turbulence-coupling diagnostics the granule accumulates (``hdef_ic``, ``div_ic``,
``dwdx``, ``dwdy``; consumed by NWP turbulence, a P3 component) are component-private
state behind the restart/functional-state protocols (§4.5), zero-initialized at
construction exactly like the icon4py driver does.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from datetime import timedelta
from types import MappingProxyType
from typing import Any, ClassVar, Final

import numpy as np
import xarray as xr

from symcon.core.components.base import DataArrayDict, Stepper
from symcon.core.context import ComputeContext
from symcon.core.contracts.properties import PropertySpec
from symcon.core.state.dataarray import make_dataarray
from symcon.core.typing import FieldBuffer, Location
from symcon.icon import names as _names  # noqa: F401  (registry seed side effect)
from symcon.icon.components.dycore import (
    _geometry_from_grid,
    icon_namelist_origins,
)
from symcon.icon.grid.grid import IconGrid
from symcon.icon.grid.vertical import VerticalGrid

__all__ = ["DiffusionConfig", "HorizontalDiffusion", "icon_namelist_origins"]

_CELL_K: Final = ("cell", "height")
_CELL_K_HALF: Final = ("cell", "height_interface")
_EDGE_K: Final = ("edge", "height")


def _knob(default: Any, origin: str) -> Any:
    """A config field carrying its ICON namelist origin as dataclass metadata."""
    return dataclasses.field(default=default, metadata={"icon_namelist_origin": origin})


#: icon4py defaults for hdiff_smag_fac2/z2 are *computed* expressions — transcribed
#: verbatim from ``diffusion.py`` (v0.2.0) and asserted equal to the granule's in tests.
_SMAG_FAC2_DEFAULT: Final[float] = 2e-6 * (1600.0 + 25000.0 + math.sqrt(1600.0 * (1600 + 50000.0)))
_SMAG_Z2_DEFAULT: Final[float] = 1600.0 + 50000.0 + math.sqrt(1600.0 * (1600 + 50000.0))


@dataclasses.dataclass(frozen=True)
class DiffusionConfig:
    """Horizontal-diffusion configuration (SPEC S13: mirrors icon4py ``DiffusionConfig``).

    Every field carries an ``icon_namelist_origin`` annotation (machine-readable via
    :func:`icon_namelist_origins`). Defaults are icon4py v0.2.0 defaults, which
    transcribe the ICON Fortran namelist defaults (REFERENCES.lock
    ``icon4py-diffusion``). The icon4py granule accepts only the operational slice
    (``diffusion_type=5``, ``type_vn_diffu=1``, ``type_t_diffu=2``, no Smagorinsky-w,
    no 3d Smagorinsky, ``shear_type in (0, 1, 2)``); :meth:`to_icon4py` re-runs its
    validation, so an unsupported knob fails at component construction.
    """

    # -- diffusion_nml -------------------------------------------------------------------
    diffusion_type: int = _knob(5, "diffusion_nml:hdiff_order")  # 5 = Smagorinsky + 4th order
    hdiff_w: bool = _knob(True, "diffusion_nml:lhdiff_w")
    hdiff_vn: bool = _knob(True, "diffusion_nml:lhdiff_vn")
    hdiff_temp: bool = _knob(True, "diffusion_nml:lhdiff_temp")
    hdiff_smag_w: bool = _knob(False, "diffusion_nml:lhdiff_smag_w")
    type_vn_diffu: int = _knob(1, "diffusion_nml:itype_vn_diffu")  # 1 = diamond vertices
    smag_3d: bool = _knob(False, "diffusion_nml:lsmag_3d")
    type_t_diffu: int = _knob(2, "diffusion_nml:itype_t_diffu")  # 2 = heterogeneous
    hdiff_efdt_ratio: float = _knob(36.0, "diffusion_nml:hdiff_efdt_ratio")
    hdiff_w_efdt_ratio: float = _knob(15.0, "diffusion_nml:hdiff_w_efdt_ratio")
    smagorinski_scaling_factor: float = _knob(0.015, "diffusion_nml:hdiff_smag_fac")
    smagorinski_scaling_factor2: float = _knob(_SMAG_FAC2_DEFAULT, "diffusion_nml:hdiff_smag_fac2")
    smagorinski_scaling_factor3: float = _knob(0.0, "diffusion_nml:hdiff_smag_fac3")
    smagorinski_scaling_factor4: float = _knob(1.0, "diffusion_nml:hdiff_smag_fac4")
    smagorinski_scaling_height: float = _knob(32500.0, "diffusion_nml:hdiff_smag_z")
    smagorinski_scaling_height2: float = _knob(_SMAG_Z2_DEFAULT, "diffusion_nml:hdiff_smag_z2")
    smagorinski_scaling_height3: float = _knob(50000.0, "diffusion_nml:hdiff_smag_z3")
    smagorinski_scaling_height4: float = _knob(90000.0, "diffusion_nml:hdiff_smag_z4")
    # -- other namelists -------------------------------------------------------------------
    #: The diffusion coefficients scale with the substep ratio (must equal the dycore's).
    ndyn_substeps: int = _knob(5, "nonhydrostatic_nml:ndyn_substeps")
    zdiffu_t: bool = _knob(True, "nonhydrostatic_nml:l_zdiffu_t")
    velocity_boundary_diffusion_denom: float = _knob(200.0, "gridref_nml:denom_diffu_v")
    temperature_boundary_diffusion_denom: float = _knob(135.0, "gridref_nml:denom_diffu_t")
    #: icon4py default = DEFAULT_DYNAMICS_TO_PHYSICS_TIMESTEP_RATIO(5) * 0.02.
    max_nudging_coefficient: float = _knob(0.1, "interpol_nml:nudge_max_coeff")
    shear_type: int = _knob(0, "turbdiff_nml:itype_sher")
    iforcing: int = _knob(0, "run_nml:iforcing")  # 0 = NO_FORCING
    a_hshr: float = _knob(1.0, "turbdiff_nml:a_hshr")
    loutshs: bool = _knob(False, "derived: mo_turbdiff_config loutshs (.NOT. ldynamics)")

    def to_icon4py(self) -> Any:
        """The icon4py ``DiffusionConfig`` (runs the granule's own slice validation)."""
        from icon4py.model.atmosphere.diffusion import diffusion as i4_diffusion

        return i4_diffusion.DiffusionConfig(
            diffusion_type=i4_diffusion.DiffusionType(self.diffusion_type),
            hdiff_w=self.hdiff_w,
            hdiff_vn=self.hdiff_vn,
            hdiff_temp=self.hdiff_temp,
            hdiff_smag_w=self.hdiff_smag_w,
            type_vn_diffu=i4_diffusion.SmagorinskyStencilType(self.type_vn_diffu),
            smag_3d=self.smag_3d,
            type_t_diffu=i4_diffusion.TemperatureDiscretizationType(self.type_t_diffu),
            hdiff_efdt_ratio=self.hdiff_efdt_ratio,
            hdiff_w_efdt_ratio=self.hdiff_w_efdt_ratio,
            smagorinski_scaling_factor=self.smagorinski_scaling_factor,
            smagorinski_scaling_factor2=self.smagorinski_scaling_factor2,
            smagorinski_scaling_factor3=self.smagorinski_scaling_factor3,
            smagorinski_scaling_factor4=self.smagorinski_scaling_factor4,
            smagorinski_scaling_height=self.smagorinski_scaling_height,
            smagorinski_scaling_height2=self.smagorinski_scaling_height2,
            smagorinski_scaling_height3=self.smagorinski_scaling_height3,
            smagorinski_scaling_height4=self.smagorinski_scaling_height4,
            n_substeps=self.ndyn_substeps,
            zdiffu_t=self.zdiffu_t,
            velocity_boundary_diffusion_denom=self.velocity_boundary_diffusion_denom,
            temperature_boundary_diffusion_denom=self.temperature_boundary_diffusion_denom,
            max_nudging_coefficient=self.max_nudging_coefficient,
            shear_type=i4_diffusion.TurbulenceShearForcingType(self.shear_type),
            iforcing=i4_diffusion.ForcingType(self.iforcing),
            a_hshr=self.a_hshr,
            loutshs=self.loutshs,
        )

    @classmethod
    def from_icon4py(cls, cfg: Any) -> DiffusionConfig:
        """Mirror an icon4py ``DiffusionConfig`` (e.g. a datatest archive's namelist)."""
        return cls(
            diffusion_type=int(cfg.diffusion_type),
            hdiff_w=bool(cfg.apply_to_vertical_wind),
            hdiff_vn=bool(cfg.apply_to_horizontal_wind),
            hdiff_temp=bool(cfg.apply_to_temperature),
            hdiff_smag_w=bool(cfg.apply_smag_diff_to_vertical_wind),
            type_vn_diffu=int(cfg.type_vn_diffu),
            smag_3d=bool(cfg.compute_3d_smag_coeff),
            type_t_diffu=int(cfg.type_t_diffu),
            hdiff_efdt_ratio=float(cfg.hdiff_efdt_ratio),
            hdiff_w_efdt_ratio=float(cfg.hdiff_w_efdt_ratio),
            smagorinski_scaling_factor=float(cfg.smagorinski_scaling_factor),
            smagorinski_scaling_factor2=float(cfg.smagorinski_scaling_factor2),
            smagorinski_scaling_factor3=float(cfg.smagorinski_scaling_factor3),
            smagorinski_scaling_factor4=float(cfg.smagorinski_scaling_factor4),
            smagorinski_scaling_height=float(cfg.smagorinski_scaling_height),
            smagorinski_scaling_height2=float(cfg.smagorinski_scaling_height2),
            smagorinski_scaling_height3=float(cfg.smagorinski_scaling_height3),
            smagorinski_scaling_height4=float(cfg.smagorinski_scaling_height4),
            ndyn_substeps=int(cfg.ndyn_substeps),
            zdiffu_t=bool(cfg.apply_zdiffusion_t),
            velocity_boundary_diffusion_denom=float(cfg.velocity_boundary_diffusion_denominator),
            temperature_boundary_diffusion_denom=float(
                cfg.temperature_boundary_diffusion_denominator
            ),
            max_nudging_coefficient=float(cfg.max_nudging_coefficient),
            shear_type=int(cfg.shear_type),
            iforcing=int(cfg.iforcing),
            a_hshr=float(cfg.a_hshr),
            loutshs=bool(cfg.loutshs),
        )


# ------------------------------------------------------------------------------------------
# Static-state consumption lists — the S11 coordination point (S12 pattern).
# ------------------------------------------------------------------------------------------

#: icon4py ``DiffusionMetricState`` field -> symcon registry name (produced by
#: :func:`symcon.icon.grid.metrics`; REFERENCES.lock ``icon4py-diffusion``).
STATIC_METRIC_FIELDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "theta_ref_mc": "icon:theta_ref_mc",
        "wgtfac_c": "icon:wgtfac_c",
        "zd_vertoffset": "icon:zd_vertoffset",
        "zd_diffcoef": "icon:zd_diffcoef",
        "zd_intcoef": "icon:zd_intcoef",
    }
)

#: icon4py ``DiffusionInterpolationState`` field -> symcon registry name (produced by
#: :func:`symcon.icon.grid.interpolation`).
STATIC_INTERPOLATION_FIELDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "e_bln_c_s": "icon:e_bln_c_s",
        "rbf_coeff_1": "icon:rbf_vec_coeff_v1",
        "rbf_coeff_2": "icon:rbf_vec_coeff_v2",
        "geofac_div": "icon:geofac_div",
        "geofac_n2s": "icon:geofac_n2s",
        "geofac_grg_x": "icon:geofac_grg_x",
        "geofac_grg_y": "icon:geofac_grg_y",
        "nudgecoeff_e": "icon:nudgecoeff_e",
    }
)

#: Every static-state name the constructor requires (frozen consumption list).
STATIC_FIELDS: Final[tuple[str, ...]] = tuple(
    sorted({*STATIC_METRIC_FIELDS.values(), *STATIC_INTERPOLATION_FIELDS.values()})
)


def _dim_map() -> dict[str, Any]:
    """symcon dim name -> icon4py gt4py dimension (incl. the diffusion sparse dims)."""
    from icon4py.model.common import dimension as i4_dims

    return {
        "cell": i4_dims.CellDim,
        "edge": i4_dims.EdgeDim,
        "vertex": i4_dims.VertexDim,
        "height": i4_dims.KDim,
        "height_interface": i4_dims.KDim,  # interface extent carried by the shape
        "c2e": i4_dims.C2EDim,
        "c2e2c": i4_dims.C2E2CDim,
        "c2e2co": i4_dims.C2E2CODim,
        "v2e": i4_dims.V2EDim,
    }


def _location_of(dims: tuple[str, ...]) -> Location:
    horizontal = next((d for d in dims if d in ("cell", "edge", "vertex")), None)
    return Location(horizontal) if horizontal is not None else Location.SCALAR


# ------------------------------------------------------------------------------------------
# Restart / functional-state schema (§4.5) — the turbulence-coupling diagnostics.
# ------------------------------------------------------------------------------------------

#: (restart key, dims, units). div_ic is a divergence [1/s]; hdef_ic the squared
#: horizontal wind deformation [1/s^2]; dwdx/dwdy vertical-wind gradients [1/s]
#: (ICON ``t_nh_diag`` — REFERENCES.lock ``icon4py-diffusion``).
_RESTART_SCHEMA: Final[tuple[tuple[str, tuple[str, ...], str], ...]] = (
    ("carry/hdef_ic", _CELL_K_HALF, "s-2"),
    ("carry/div_ic", _CELL_K_HALF, "s-1"),
    ("carry/dwdx", _CELL_K_HALF, "s-1"),
    ("carry/dwdy", _CELL_K_HALF, "s-1"),
    ("meta/steps_done", (), "1"),
)


class HorizontalDiffusion(Stepper):
    """The ICON horizontal diffusion as a symcon ``Stepper`` (SPEC S13).

    ``HorizontalDiffusion(grid, vgrid, static, cfg, ctx, *, ...)`` — constructor
    mirrors the S12 ``NonhydroSolver`` shape (architecture §5.1 sketches
    ``HorizontalDiffusion(grid, static, cfg.diffusion, ctx)``; the hosted granule
    additionally requires the vertical grid for its Smagorinsky enhancement profile,
    so ``vgrid`` sits in the S12 position):

    - ``grid``: a :class:`symcon.icon.grid.IconGrid` (production path — geometry
      derived from it) **or** a raw icon4py ``IconGrid`` (host-grid path, geometry
      passed explicitly — how the parity tests mirror upstream);
    - ``vgrid``: a :class:`symcon.icon.grid.VerticalGrid` or a raw icon4py
      ``VerticalGrid``;
    - ``static``: mapping of the :data:`STATIC_FIELDS` registry names to S11
      static-state DataArrays (``metrics(...) | interpolation(...)``) or ready
      icon4py fields (savepoint parity path — zero conversion);
    - ``cfg``: :class:`DiffusionConfig`.

    One ``__call__`` advances one full Δt (diffusion runs once per physics timestep,
    after the dynamics substepping — icon4py driver order). The granule mutates its
    state in place; symcon ingests/egresses the boundary buffers around it
    (``communicates_internally=True``: halo exchanges happen inside the granule).
    """

    input_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": _EDGE_K, "units": "m s-1"},
        "upward_air_velocity_on_interface_levels": {"dims": _CELL_K_HALF, "units": "m s-1"},
        "icon:exner_function": {"dims": _CELL_K, "units": "1"},
        "icon:virtual_potential_temperature": {"dims": _CELL_K, "units": "K"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": _EDGE_K, "units": "m s-1"},
        "upward_air_velocity_on_interface_levels": {"dims": _CELL_K_HALF, "units": "m s-1"},
        "icon:exner_function": {"dims": _CELL_K, "units": "1"},
        "icon:virtual_potential_temperature": {"dims": _CELL_K, "units": "K"},
    }

    #: §4.3 table: halo exchanges happen inside the hosted granule.
    communicates_internally: ClassVar[bool] = True

    def __init__(
        self,
        grid: IconGrid | Any,
        vgrid: VerticalGrid | Any,
        static: Mapping[str, Any],
        cfg: DiffusionConfig | None = None,
        ctx: ComputeContext | None = None,
        *,
        edge_geometry: Any | None = None,
        cell_geometry: Any | None = None,
        exchange: Any | None = None,
        name: str | None = None,
    ) -> None:
        self.config = cfg if cfg is not None else DiffusionConfig()
        super().__init__(ctx=ctx, name=name)

        from symcon.core.ingress.gt4py import resolve_backend

        self._backend = resolve_backend(self.ctx.backend)

        missing = [f for f in STATIC_FIELDS if f not in static]
        if missing:
            raise ValueError(
                f"component {self.name!r}: static state is missing {missing!r} "
                f"(required: the S11 metrics/interpolation diffusion field set)."
            )

        # -- donor objects (wrap-don't-rewrite) ---------------------------------------
        if isinstance(grid, IconGrid):
            self._i4_grid = grid.icon4py_grid
            if edge_geometry is None or cell_geometry is None:
                built_cell, built_edge = _geometry_from_grid(grid)
                cell_geometry = cell_geometry if cell_geometry is not None else built_cell
                edge_geometry = edge_geometry if edge_geometry is not None else built_edge
            # (the diffusion granule needs no owner mask)
        else:
            self._i4_grid = grid
            if edge_geometry is None or cell_geometry is None:
                raise ValueError(
                    f"component {self.name!r}: hosting on a raw icon4py grid requires "
                    f"explicit edge_geometry and cell_geometry."
                )
        self._i4_vgrid = vgrid.icon4py_grid if isinstance(vgrid, VerticalGrid) else vgrid
        self._nlev = int(self._i4_grid.num_levels)

        metric_state, interpolation_state = self._build_static_states(static)

        from icon4py.model.atmosphere.diffusion import diffusion as i4_diffusion
        from icon4py.model.common.decomposition import definitions as i4_decomposition

        i4_config = self.config.to_icon4py()  # runs the granule's slice validation
        self._diffusion = i4_diffusion.Diffusion(
            grid=self._i4_grid,
            config=i4_config,
            params=i4_diffusion.DiffusionParams(i4_config),
            vertical_grid=self._i4_vgrid,
            metric_state=metric_state,
            interpolation_state=interpolation_state,
            edge_params=edge_geometry,
            cell_params=cell_geometry,
            backend=self._backend.gt4py_backend,
            exchange=(exchange if exchange is not None else i4_decomposition.single_node_exchange),
        )

        self._allocate_private_state()
        self._steps_done = 0
        self._next_run_is_initial = False

    # -- construction helpers ---------------------------------------------------------

    def _build_static_states(self, static: Mapping[str, Any]) -> tuple[Any, Any]:
        """icon4py Diffusion metric/interpolation states from the S11 static mapping.

        Entries may be S11 DataArrays (converted to gt4py fields on this component's
        backend, dtype-preserving — ``zd_vertoffset`` is int32) or ready icon4py
        fields (used as-is — the savepoint path).
        """
        import gt4py.next as gtx
        from icon4py.model.atmosphere.diffusion import diffusion_states

        def convert(registry_name: str) -> Any:
            value = static[registry_name]
            if isinstance(value, xr.DataArray):
                dim_map = _dim_map()
                dims = tuple(dim_map[d] for d in value.dims)
                data = value.data
                if isinstance(data, np.ndarray):
                    data = np.ascontiguousarray(data)
                return gtx.as_field(dims, data, allocator=self._backend.gt4py_backend)
            return value  # a ready icon4py field

        metric = diffusion_states.DiffusionMetricState(
            **{field: convert(name) for field, name in STATIC_METRIC_FIELDS.items()}
        )
        interpolation = diffusion_states.DiffusionInterpolationState(
            **{field: convert(name) for field, name in STATIC_INTERPOLATION_FIELDS.items()}
        )
        return metric, interpolation

    def _allocate_private_state(self) -> None:
        """Private diagnostics + the granule's prognostic-state container.

        Diagnostics are zero-initialized exactly like the icon4py driver's
        ``initialize_diffusion_diagnostic_state``; the ``PrognosticState`` is the
        in-place buffer set the hosted granule mutates (``rho`` is a private zero
        field — diffusion never touches it).
        """
        from icon4py.model.atmosphere.diffusion import diffusion_states
        from icon4py.model.common import dimension as dims
        from icon4py.model.common import type_alias as ta
        from icon4py.model.common.states import prognostic_state as i4_prognostics
        from icon4py.model.common.utils import data_allocation as data_alloc

        grid = self._i4_grid
        allocator = self._backend.gt4py_backend

        def field(*fdims: Any, half: bool = False, dtype: Any = ta.wpfloat) -> Any:
            extend = {dims.KDim: 1} if half else None
            return data_alloc.zero_field(
                grid, *fdims, dtype=dtype, extend=extend, allocator=allocator
            )

        self._diag_state = diffusion_states.DiffusionDiagnosticState(
            hdef_ic=field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
            div_ic=field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
            dwdx=field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
            dwdy=field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
        )
        self._prognostic_state = i4_prognostics.PrognosticState(
            vn=field(dims.EdgeDim, dims.KDim),
            w=field(dims.CellDim, dims.KDim, half=True),
            rho=field(dims.CellDim, dims.KDim),  # never read/written by the granule
            exner=field(dims.CellDim, dims.KDim),
            theta_v=field(dims.CellDim, dims.KDim),
        )

    # -- the call path ------------------------------------------------------------------

    def initial_stabilization(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, Any] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """ICON's extra pre-timeloop diffusion call (``linit=.TRUE.``).

        "For real-data runs, perform an extra diffusion call before the first time
        step because no other filtering of the interpolated velocity field is done"
        (icon4py ``Diffusion.run`` docstring). Uses the granule's ``initial_run=True``
        coefficients (``setup_fields_for_initial_step``, ``smag_offset=0``); never
        invoked implicitly — the caller decides (driver ``apply_initial_stabilization``).
        """
        self._next_run_is_initial = True
        try:
            return self(state, timestep, out=out)
        finally:
            self._next_run_is_initial = False

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        """One diffusion step over the full Δt (granule ``run``, in-place)."""
        assert timestep is not None  # timestep_required (base Stepper shape)
        prognostic = self._prognostic_state
        for field_name, input_name in self._FIELD_MAP:
            getattr(prognostic, field_name).ndarray[...] = inputs[input_name]
        self._diffusion.run(
            diagnostic_state=self._diag_state,
            prognostic_state=prognostic,
            dtime=timestep.total_seconds(),
            initial_run=self._next_run_is_initial,
        )
        self._steps_done += 1
        for field_name, output_name in self._FIELD_MAP:
            outputs[output_name][...] = getattr(prognostic, field_name).ndarray

    _FIELD_MAP: ClassVar[tuple[tuple[str, str], ...]] = (
        ("vn", "icon:normal_wind"),
        ("w", "upward_air_velocity_on_interface_levels"),
        ("exner", "icon:exner_function"),
        ("theta_v", "icon:virtual_potential_temperature"),
    )

    # -- restart / functional state (§4.5, §8.5) ------------------------------------------

    def _restart_targets(self) -> dict[str, Any]:
        diag = self._diag_state
        return {
            "carry/hdef_ic": diag.hdef_ic.ndarray,
            "carry/div_ic": diag.div_ic.ndarray,
            "carry/dwdx": diag.dwdx.ndarray,
            "carry/dwdy": diag.dwdy.ndarray,
        }

    def restart_state(self) -> dict[str, xr.DataArray]:
        """The turbulence-coupling diagnostics the granule accumulates (SPEC S13)."""
        result: dict[str, xr.DataArray] = {}
        targets = self._restart_targets()
        for key, dims, units in _RESTART_SCHEMA:
            if key == "meta/steps_done":
                value = np.asarray(float(self._steps_done))
            else:
                value = targets[key]
                value = value.get() if hasattr(value, "get") else np.asarray(value)
                value = value.copy()
            result[key] = make_dataarray(
                value, name=key, dims=dims, units=units, location=_location_of(dims)
            )
        return result

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        """Restore the full private-state schema (strict: all keys, no extras)."""
        expected = {key for key, _, _ in _RESTART_SCHEMA}
        got = set(restart)
        if got != expected:
            missing, extra = sorted(expected - got), sorted(got - expected)
            raise ValueError(
                f"component {self.name!r}: restart schema mismatch "
                f"(missing {missing!r}, unknown {extra!r})."
            )
        targets = self._restart_targets()
        for key, _dims, _units in _RESTART_SCHEMA:
            data = np.asarray(restart[key].data)
            if key == "meta/steps_done":
                self._steps_done = int(data)
            else:
                targets[key][...] = data

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """The restart schema as PropertySpecs (F-tier declaration; consumption is P6)."""
        specs: dict[str, PropertySpec] = {}
        for key, dims, units in _RESTART_SCHEMA:
            specs[key] = PropertySpec(name=key, dims=dims, units=units, location=_location_of(dims))
        return MappingProxyType(specs)
