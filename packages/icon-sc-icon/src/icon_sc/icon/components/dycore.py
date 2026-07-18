"""``NonhydroSolver(DynamicalCore)`` — icon4py ``solve_nonhydro`` hosted on ICON-sc (S12).

The icon4py nonhydrostatic solver + velocity advection as **one** ICON-sc component
(architecture §4.3): the predictor-corrector is the stage structure, ``ndyn_substeps``
is the super-fast tier, slow physics enters through the tendency-bus port, and the
two prognostic time levels plus the velocity-advection carry-over are component-private
state behind the restart/functional-state protocols.

Hosting policy (wrap-don't-rewrite, §4.4): the ~50 predictor/corrector stencil programs
stay icon4py granule internals (REFERENCES.lock ``icon4py-solve-nonhydro``); ICON-sc
invokes ``run_predictor_step``/``run_corrector_step`` exactly the way icon4py's own
integration tests and driver do (REFERENCES.lock ``icon4py-solve-nonhydro-tests``,
``icon4py-driver-dyn-substepping``).

**Tier nesting (declared deviation from the S04 default orchestration).** The base
:class:`~icon_sc.core.components.dycore.DynamicalCore` unrolls Fig. 3.10 stage-outer
(each stage runs its own substep block). ICON nests the other way round: each of the
``ndyn_substeps`` substeps runs the full predictor→corrector stage pair
(``mo_nh_stepping.f90::perform_dyn_substepping``, REFERENCES.lock
``icon-fortran-solve-nonhydro-stepping``). ``NonhydroSolver`` therefore overrides
``array_call`` — the base class explicitly routes *tier orchestration* through that
method — while keeping the frozen S04 subclass hooks: ``substep_array_call(stage,
substep, ...)`` executes one stage of one substep and ``stage_array_call`` is its
degenerate single-substep form. Data flows through the component-private icon4py
state objects (``communicates_internally=True``, §4.3): the hook ``inputs``/``outputs``
dicts are the boundary buffers ingested/egressed once per step by ``array_call``.

**Slow-tendency bus port** (tutorial §3.7.2, REFERENCES.lock
``icon-fortran-solve-nonhydro-stepping``): the slots ``icon:ddt_vn_phy`` and
``icon:ddt_exner_phy`` are ordinary input fields, held constant across the step and
consumed *inside* the substeps at the points ICON's numerics dictate — ``ddt_vn_phy``
in the vn update of every predictor and corrector (``mo_solve_nonhydro.f90`` l.1365,
l.1410), ``ddt_exner_phy`` in the explicit part of the vertically implicit solver
(l.2316/2340). Absent slots default to zeros so the S13 JW run needs no physics.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from datetime import timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Final

import numpy as np
import xarray as xr

from icon_sc.core.components.base import DataArrayDict
from icon_sc.core.components.dycore import DynamicalCore
from icon_sc.core.context import ComputeContext
from icon_sc.core.contracts.properties import PropertySpec
from icon_sc.core.coupling.concurrent import ConcurrentCoupling
from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.typing import FieldBuffer, Location
from icon_sc.icon import names as _names  # noqa: F401  (registry seed side effect)
from icon_sc.icon.grid.grid import IconGrid
from icon_sc.icon.grid.vertical import VerticalGrid

if TYPE_CHECKING:
    from icon_sc.core.plan.bind import PlanBuilder

__all__ = ["NonhydroConfig", "NonhydroSolver", "icon_namelist_origins"]

_CELL_K: Final = ("cell", "height")
_CELL_K_HALF: Final = ("cell", "height_interface")
_EDGE_K: Final = ("edge", "height")
_EDGE_K_HALF: Final = ("edge", "height_interface")


# --------------------------------------------------------------------------------------
# Configuration — the slice-relevant ICON namelist knobs, annotated with their origin.
# --------------------------------------------------------------------------------------


def _knob(default: Any, origin: str) -> Any:
    """A config field carrying its ICON namelist origin as dataclass metadata."""
    return dataclasses.field(default=default, metadata={"icon_namelist_origin": origin})


@dataclasses.dataclass(frozen=True)
class NonhydroConfig:
    """solve_nonhydro configuration (SPEC S12: mirrors icon4py ``NonHydrostaticConfig``).

    Every field carries an ``icon_namelist_origin`` annotation (dataclass metadata,
    machine-readable via :func:`icon_namelist_origins`). Defaults are icon4py v0.2.0
    defaults, which transcribe the ICON Fortran namelist defaults (REFERENCES.lock
    ``icon4py-solve-nonhydro``). The icon4py granule accepts only the operational
    slice (``itime_scheme=4``, ``iadv_rhotheta=2``, ``igradp_method=3``, Klemp
    Rayleigh damping, ``extra_diffu=True``); :meth:`to_icon4py` re-runs its
    validation, so an unsupported knob fails at component construction.
    """

    # -- nonhydrostatic_nml ------------------------------------------------------------
    itime_scheme: int = _knob(4, "nonhydrostatic_nml:itime_scheme")
    iadv_rhotheta: int = _knob(2, "nonhydrostatic_nml:iadv_rhotheta")
    igradp_method: int = _knob(3, "nonhydrostatic_nml:igradp_method")
    rayleigh_type: int = _knob(2, "nonhydrostatic_nml:rayleigh_type")  # 2 = Klemp
    divdamp_order: int = _knob(24, "nonhydrostatic_nml:divdamp_order")
    divdamp_type: int = _knob(3, "nonhydrostatic_nml:divdamp_type")
    #: The super-fast tier ratio N: Δτ = Δt/N (the DynamicalCore ``substeps`` default).
    ndyn_substeps: int = _knob(5, "nonhydrostatic_nml:ndyn_substeps")
    #: CFL-escalation bound for adaptive ratio providers (ICON caps at 12).
    ndyn_substeps_max: int = _knob(12, "mo_nonhydrostatic_config:ndyn_substeps_max")
    rhotheta_offctr: float = _knob(-0.1, "nonhydrostatic_nml:rhotheta_offctr")
    veladv_offctr: float = _knob(0.25, "nonhydrostatic_nml:veladv_offctr")
    divdamp_fac: float = _knob(0.0025, "nonhydrostatic_nml:divdamp_fac")
    divdamp_fac2: float = _knob(0.004, "nonhydrostatic_nml:divdamp_fac2")
    divdamp_fac3: float = _knob(0.004, "nonhydrostatic_nml:divdamp_fac3")
    divdamp_fac4: float = _knob(0.004, "nonhydrostatic_nml:divdamp_fac4")
    divdamp_z: float = _knob(32500.0, "nonhydrostatic_nml:divdamp_z")
    divdamp_z2: float = _knob(40000.0, "nonhydrostatic_nml:divdamp_z2")
    divdamp_z3: float = _knob(60000.0, "nonhydrostatic_nml:divdamp_z3")
    divdamp_z4: float = _knob(80000.0, "nonhydrostatic_nml:divdamp_z4")
    extra_diffu: bool = _knob(True, "nonhydrostatic_nml:lextra_diffu")
    # -- other namelists ---------------------------------------------------------------
    #: icon4py default = DEFAULT_DYNAMICS_TO_PHYSICS_TIMESTEP_RATIO(5) * 0.02.
    max_nudging_coefficient: float = _knob(0.1, "interpol_nml:nudge_max_coeff")
    l_vert_nested: bool = _knob(False, "run_nml:lvert_nest")
    deepatmos_mode: bool = _knob(False, "dynamics_nml:ldeepatmo")
    iau_init: bool = _knob(False, "initicon_nml:init_mode (MODE_IAU)")
    # -- runtime-derived quantities (not namelist knobs; origins name the source) -------
    #: ICON derives divdamp_fac_o2 from the spinup ramp at runtime; fixed per run here.
    second_order_divdamp_factor: float = _knob(
        0.032, "derived: mo_nonhydrostatic_config divdamp_fac_o2 (runtime spinup value)"
    )
    #: ICON derives lprep_adv from ltransport; S12 hosts no transport — default off.
    prepare_advection: bool = _knob(False, "derived: run_nml:ltransport -> lprep_adv")

    def __post_init__(self) -> None:
        # The icon4py granule *accepts* iau_init (it only gates program variants),
        # but this slice hard-wires is_iau_active=False / iau_wgt_dyn=0.0 into every
        # stage invocation (IAU is an S-later component, architecture §4.3) — a
        # request for IAU must fail loudly here, not silently no-op.
        if self.iau_init:
            raise NotImplementedError(
                "NonhydroConfig: iau_init=True is not supported in this slice — the "
                "hosted solver is always invoked with is_iau_active=False (the "
                "incremental analysis update arrives with its own component, "
                "architecture §4.3)."
            )

    def to_icon4py(self) -> Any:
        """The icon4py ``NonHydrostaticConfig`` (runs the granule's own validation)."""
        from icon4py.model.atmosphere.dycore import dycore_states, solve_nonhydro
        from icon4py.model.common import constants as i4_constants

        return solve_nonhydro.NonHydrostaticConfig(
            itime_scheme=dycore_states.TimeSteppingScheme(self.itime_scheme),
            iadv_rhotheta=dycore_states.RhoThetaAdvectionType(self.iadv_rhotheta),
            igradp_method=dycore_states.HorizontalPressureDiscretizationType(self.igradp_method),
            rayleigh_type=i4_constants.RayleighType(self.rayleigh_type),
            divdamp_order=dycore_states.DivergenceDampingOrder(self.divdamp_order),
            divdamp_type=dycore_states.DivergenceDampingType(self.divdamp_type),
            l_vert_nested=self.l_vert_nested,
            deepatmos_mode=self.deepatmos_mode,
            iau_init=self.iau_init,
            extra_diffu=self.extra_diffu,
            rhotheta_offctr=self.rhotheta_offctr,
            veladv_offctr=self.veladv_offctr,
            max_nudging_coefficient=self.max_nudging_coefficient,
            fourth_order_divdamp_factor=self.divdamp_fac,
            fourth_order_divdamp_factor2=self.divdamp_fac2,
            fourth_order_divdamp_factor3=self.divdamp_fac3,
            fourth_order_divdamp_factor4=self.divdamp_fac4,
            fourth_order_divdamp_z=self.divdamp_z,
            fourth_order_divdamp_z2=self.divdamp_z2,
            fourth_order_divdamp_z3=self.divdamp_z3,
            fourth_order_divdamp_z4=self.divdamp_z4,
        )

    @classmethod
    def from_icon4py(
        cls,
        cfg: Any,
        *,
        ndyn_substeps: int,
        second_order_divdamp_factor: float = 0.032,
        prepare_advection: bool = False,
    ) -> NonhydroConfig:
        """Mirror an icon4py ``NonHydrostaticConfig`` (e.g. a datatest archive's)."""
        return cls(
            itime_scheme=int(cfg.itime_scheme),
            iadv_rhotheta=int(cfg.iadv_rhotheta),
            igradp_method=int(cfg.igradp_method),
            rayleigh_type=int(cfg.rayleigh_type),
            divdamp_order=int(cfg.divdamp_order),
            divdamp_type=int(cfg.divdamp_type),
            ndyn_substeps=int(ndyn_substeps),
            rhotheta_offctr=float(cfg.rhotheta_offctr),
            veladv_offctr=float(cfg.veladv_offctr),
            divdamp_fac=float(cfg.fourth_order_divdamp_factor),
            divdamp_fac2=float(cfg.fourth_order_divdamp_factor2),
            divdamp_fac3=float(cfg.fourth_order_divdamp_factor3),
            divdamp_fac4=float(cfg.fourth_order_divdamp_factor4),
            divdamp_z=float(cfg.fourth_order_divdamp_z),
            divdamp_z2=float(cfg.fourth_order_divdamp_z2),
            divdamp_z3=float(cfg.fourth_order_divdamp_z3),
            divdamp_z4=float(cfg.fourth_order_divdamp_z4),
            extra_diffu=bool(cfg.extra_diffu),
            max_nudging_coefficient=float(cfg.max_nudging_coefficient),
            l_vert_nested=bool(cfg.l_vert_nested),
            deepatmos_mode=bool(cfg.deepatmos_mode),
            iau_init=bool(cfg.iau_init),
            second_order_divdamp_factor=float(second_order_divdamp_factor),
            prepare_advection=bool(prepare_advection),
        )


def icon_namelist_origins(config: Any) -> dict[str, str]:
    """Field name -> ICON namelist origin, from the dataclass metadata annotations.

    Works for any origin-annotated config dataclass (``NonhydroConfig``, S13's
    ``DiffusionConfig``, ...) — a backward-compatible widening of the S12 signature
    (declared in the S13 STATUS).
    """
    return {
        field.name: str(field.metadata["icon_namelist_origin"])
        for field in dataclasses.fields(config)
    }


# --------------------------------------------------------------------------------------
# Static-state consumption lists — the S11 coordination point (SPEC S12 "enumerate").
# --------------------------------------------------------------------------------------

#: icon4py ``MetricStateNonHydro`` field -> ICON-sc registry name of the static input
#: (REFERENCES.lock ``icon4py-dycore-diffusion-static-state``; produced by
#: :func:`icon_sc.icon.grid.metrics`).
STATIC_METRIC_FIELDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "mask_prog_halo_c": "icon:mask_prog_halo_c",
        "rayleigh_w": "icon:rayleigh_w",
        "wgtfac_c": "icon:wgtfac_c",
        "wgtfacq_c": "icon:wgtfacq_c",
        "wgtfac_e": "icon:wgtfac_e",
        "wgtfacq_e": "icon:wgtfacq_e",
        "time_extrapolation_parameter_for_exner": "icon:exner_exfac",
        "reference_exner_at_cells_on_model_levels": "icon:exner_ref_mc",
        "reference_rho_at_cells_on_model_levels": "icon:rho_ref_mc",
        "reference_theta_at_cells_on_model_levels": "icon:theta_ref_mc",
        "reference_rho_at_edges_on_model_levels": "icon:rho_ref_me",
        "reference_theta_at_edges_on_model_levels": "icon:theta_ref_me",
        "reference_theta_at_cells_on_half_levels": "icon:theta_ref_ic",
        "ddz_of_reference_exner_at_cells_on_half_levels": "icon:d_exner_dz_ref_ic",
        "ddqz_z_half": "icon:ddqz_z_half",
        "d2dexdz2_fac1_mc": "icon:d2dexdz2_fac1_mc",
        "d2dexdz2_fac2_mc": "icon:d2dexdz2_fac2_mc",
        "ddxn_z_full": "icon:ddxn_z_full",
        "ddqz_z_full_e": "icon:ddqz_z_full_e",
        "ddxt_z_full": "icon:ddxt_z_full",
        "inv_ddqz_z_full": "icon:inv_ddqz_z_full",
        "vertoffset_gradp": "icon:vertoffset_gradp",
        "zdiff_gradp": "icon:zdiff_gradp",
        "nflat_gradp": "icon:nflat_gradp",
        "pg_exdist": "icon:pg_exdist",
        "exner_w_explicit_weight_parameter": "icon:vwind_expl_wgt",
        "exner_w_implicit_weight_parameter": "icon:vwind_impl_wgt",
        "horizontal_mask_for_3d_divdamp": "icon:hmask_dd3d",
        "scaling_factor_for_3d_divdamp": "icon:scalfac_dd3d",
        "coeff1_dwdz": "icon:coeff1_dwdz",
        "coeff2_dwdz": "icon:coeff2_dwdz",
        "coeff_gradekin": "icon:coeff_gradekin",
    }
)

#: icon4py ``InterpolationState`` field -> ICON-sc registry name (produced by
#: :func:`icon_sc.icon.grid.interpolation`).
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
        "c_lin_e": "icon:c_lin_e",
        "geofac_grdiv": "icon:geofac_grdiv",
        "rbf_vec_coeff_e": "icon:rbf_vec_coeff_e",
        "c_intp": "icon:c_intp",
        "geofac_rot": "icon:geofac_rot",
        "pos_on_tplane_e_1": "icon:pos_on_tplane_e_x",
        "pos_on_tplane_e_2": "icon:pos_on_tplane_e_y",
        "e_flx_avg": "icon:e_flx_avg",
    }
)

#: Every static-state name the constructor requires (frozen consumption list).
STATIC_FIELDS: Final[tuple[str, ...]] = tuple(
    sorted({*STATIC_METRIC_FIELDS.values(), *STATIC_INTERPOLATION_FIELDS.values()})
)


def _dim_map() -> dict[str, Any]:
    """ICON-sc dim name -> icon4py gt4py dimension (vertical + sparse included)."""
    from icon4py.model.common import dimension as i4_dims

    return {
        "cell": i4_dims.CellDim,
        "edge": i4_dims.EdgeDim,
        "vertex": i4_dims.VertexDim,
        "height": i4_dims.KDim,
        "height_interface": i4_dims.KDim,  # interface extent carried by the shape
        "e2c": i4_dims.E2CDim,
        "c2e": i4_dims.C2EDim,
        "c2e2co": i4_dims.C2E2CODim,
        "e2c2eo": i4_dims.E2C2EODim,
        "e2c2e": i4_dims.E2C2EDim,
        "v2e": i4_dims.V2EDim,
        "v2c": i4_dims.V2CDim,
    }


def _location_of(dims: tuple[str, ...]) -> Location:
    """Mesh location inferred from a dims tuple (scalar when none applies)."""
    horizontal = next((d for d in dims if d in ("cell", "edge", "vertex")), None)
    return Location(horizontal) if horizontal is not None else Location.SCALAR


# --------------------------------------------------------------------------------------
# Restart / functional-state schema (§4.5, §8.5) — both time levels + carry.
# --------------------------------------------------------------------------------------

#: (restart key, dims, units) of every private field, in a fixed order. ``getter``
#: paths into the icon4py state objects are resolved at runtime (`_restart_targets`).
_RESTART_SCHEMA: Final[tuple[tuple[str, tuple[str, ...], str], ...]] = (
    # -- the two prognostic time levels (SPEC: both) -----------------------------------
    ("nnow/vn", _EDGE_K, "m s-1"),
    ("nnow/w", _CELL_K_HALF, "m s-1"),
    ("nnow/rho", _CELL_K, "kg m-3"),
    ("nnow/exner", _CELL_K, "1"),
    ("nnow/theta_v", _CELL_K, "K"),
    ("nnew/vn", _EDGE_K, "m s-1"),
    ("nnew/w", _CELL_K_HALF, "m s-1"),
    ("nnew/rho", _CELL_K, "kg m-3"),
    ("nnew/exner", _CELL_K, "1"),
    ("nnew/theta_v", _CELL_K, "K"),
    # -- velocity-advection carry (ddt pairs are the MOST_EFFICIENT reuse buffers) ------
    ("carry/ddt_vn_apc_predictor", _EDGE_K, "m s-2"),
    ("carry/ddt_vn_apc_corrector", _EDGE_K, "m s-2"),
    ("carry/ddt_w_adv_predictor", _CELL_K_HALF, "m s-2"),
    ("carry/ddt_w_adv_corrector", _CELL_K_HALF, "m s-2"),
    ("carry/vt", _EDGE_K, "m s-1"),
    ("carry/vn_ie", _EDGE_K_HALF, "m s-1"),
    ("carry/w_concorr_c", _CELL_K_HALF, "m s-1"),
    ("carry/theta_v_ic", _CELL_K_HALF, "K"),
    ("carry/rho_ic", _CELL_K_HALF, "kg m-3"),
    ("carry/exner_pr", _CELL_K, "1"),
    ("carry/mass_fl_e", _EDGE_K, "kg m-1 s-1"),
    ("carry/exner_dyn_incr", _CELL_K, "1"),
    ("carry/max_vertical_cfl", (), "1"),
    # -- tracer-advection preparation accumulators -------------------------------------
    ("prep_adv/vn_traj", _EDGE_K, "m s-1"),
    ("prep_adv/mass_flx_me", _EDGE_K, "kg m-1 s-1"),
    ("prep_adv/mass_flx_ic", _CELL_K_HALF, "kg m-2 s-1"),
    ("prep_adv/vol_flx_ic", _CELL_K_HALF, "m s-1"),
    # -- predictor->corrector intermediates (rewritten every substep; serialized so a
    #    restored component is bitwise-identical even mid-experiment, and so the
    #    savepoint-replay tests can stage a corrector-only step) ------------------------
    ("z/gradh_exner", _EDGE_K, "1 m-1"),
    ("z/rho_e", _EDGE_K, "kg m-3"),
    ("z/theta_v_e", _EDGE_K, "K"),
    ("z/kin_hor_e", _EDGE_K, "m2 s-2"),
    ("z/vt_ie", _EDGE_K, "m s-1"),
    ("z/graddiv_vn", _EDGE_K, "m s-1"),
    ("z/dwdz_dd", _CELL_K, "s-1"),
    # -- substep bookkeeping -----------------------------------------------------------
    ("meta/at_initial_timestep", (), "1"),
    ("meta/steps_done", (), "1"),
)


class NonhydroSolver(DynamicalCore):
    """The ICON nonhydrostatic solver as a ICON-sc ``DynamicalCore`` (SPEC S12).

    ``NonhydroSolver(grid, vgrid, static, cfg, ctx, *, substeps=..., ...)`` —

    - ``grid``: a :class:`icon_sc.icon.grid.IconGrid` (production path: geometry and
      owner mask derived from it) **or** a raw icon4py ``IconGrid`` (host-grid path,
      as icon4py's own tests build it — then ``edge_geometry``/``cell_geometry``/
      ``owner_mask`` must be passed explicitly);
    - ``vgrid``: a :class:`icon_sc.icon.grid.VerticalGrid` or a raw icon4py
      ``VerticalGrid``;
    - ``static``: mapping of the :data:`STATIC_FIELDS` registry names to S11
      static-state DataArrays (``metrics(grid, vgrid) | interpolation(grid)``) or to
      ready icon4py fields (savepoint parity path — used as-is, zero conversion);
    - ``cfg``: :class:`NonhydroConfig` (namelist knobs, annotated origins);
    - substep tier: ``substeps`` fixes the ratio N (default ``cfg.ndyn_substeps``);
      ``ratio_provider(state) -> int`` makes it adaptive (called once per step, S04
      semantics; bounded by ``cfg.ndyn_substeps_max``). CFL exposure for adaptive
      providers is stubbed to the fixed ratio in this slice — the carry field
      ``carry/max_vertical_cfl`` (ICON ``max_vcfl_dyn``) is serialized and readable
      via :attr:`max_vertical_cfl`, but no provider ships until the CFL diagnostics
      land (declared, SPEC S12).

    The component is a first-class sympl-style citizen: constructible and callable
    without any federation (acceptance 5). One ``__call__`` advances one full Δt =
    N substeps of Δτ = Δt/N, each substep running predictor→corrector with the
    velocity-advection reuse of ICON's ``itime_scheme=4`` (``MOST_EFFICIENT``).
    """

    n_stages: ClassVar[int] = 2  # 0 = predictor, 1 = corrector
    substep_fraction: ClassVar[float] = 1.0
    #: ICON nests substeps outer (module docstring); the S14 plan compiler unrolls
    #: the step through the plan-hook quartet below (contract documented on
    #: ``DynamicalCore.substep_nesting``).
    substep_nesting: ClassVar[str] = "substep_outer"

    input_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": _EDGE_K, "units": "m s-1"},
        "upward_air_velocity_on_interface_levels": {"dims": _CELL_K_HALF, "units": "m s-1"},
        "air_density": {"dims": _CELL_K, "units": "kg m-3"},
        "icon:exner_function": {"dims": _CELL_K, "units": "1"},
        "icon:virtual_potential_temperature": {"dims": _CELL_K, "units": "K"},
        # slow-tendency bus port (zero-filled default injected by __call__).
        "icon:ddt_vn_phy": {"dims": _EDGE_K, "units": "m s-2"},
        "icon:ddt_exner_phy": {"dims": _CELL_K, "units": "s-1"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": _EDGE_K, "units": "m s-1"},
        "upward_air_velocity_on_interface_levels": {"dims": _CELL_K_HALF, "units": "m s-1"},
        "air_density": {"dims": _CELL_K, "units": "kg m-3"},
        "icon:exner_function": {"dims": _CELL_K, "units": "1"},
        "icon:virtual_potential_temperature": {"dims": _CELL_K, "units": "K"},
    }
    tendency_port: ClassVar[Mapping[str, str]] = {
        "icon:normal_wind": "icon:ddt_vn_phy",
        "icon:exner_function": "icon:ddt_exner_phy",
    }

    #: §4.3 table: halo exchanges happen inside the hosted granule.
    communicates_internally: ClassVar[bool] = True

    def __init__(
        self,
        grid: IconGrid | Any,
        vgrid: VerticalGrid | Any,
        static: Mapping[str, Any],
        cfg: NonhydroConfig | None = None,
        ctx: ComputeContext | None = None,
        *,
        substeps: int = 0,
        ratio_provider: Callable[[Mapping[str, Any]], int] | None = None,
        fast_tendency_component: ConcurrentCoupling | None = None,
        edge_geometry: Any | None = None,
        cell_geometry: Any | None = None,
        owner_mask: Any | None = None,
        exchange: Any | None = None,
        name: str | None = None,
    ) -> None:
        self.config = cfg if cfg is not None else NonhydroConfig()
        if ratio_provider is None and substeps == 0:
            substeps = self.config.ndyn_substeps
        super().__init__(
            fast_tendency_component=fast_tendency_component,
            substeps=substeps,
            ratio_provider=ratio_provider,
            ctx=ctx,
            name=name,
        )

        from icon_sc.core.ingress.gt4py import resolve_backend

        self._backend = resolve_backend(self.ctx.backend)

        missing = [f for f in STATIC_FIELDS if f not in static]
        if missing:
            raise ValueError(
                f"component {self.name!r}: static state is missing {missing!r} "
                f"(required: the S11 metrics/interpolation field set)."
            )

        # -- donor objects (wrap-don't-rewrite) ----------------------------------------
        if isinstance(grid, IconGrid):
            self._i4_grid = grid.icon4py_grid
            if edge_geometry is None or cell_geometry is None:
                built_cell, built_edge = _geometry_from_grid(grid)
                cell_geometry = cell_geometry if cell_geometry is not None else built_cell
                edge_geometry = edge_geometry if edge_geometry is not None else built_edge
            if owner_mask is None:
                owner_mask = _owner_mask_from_grid(grid, self._backend)
        else:
            self._i4_grid = grid
            if edge_geometry is None or cell_geometry is None or owner_mask is None:
                raise ValueError(
                    f"component {self.name!r}: hosting on a raw icon4py grid requires "
                    f"explicit edge_geometry, cell_geometry and owner_mask."
                )
        self._i4_vgrid = vgrid.icon4py_grid if isinstance(vgrid, VerticalGrid) else vgrid
        self._nlev = int(self._i4_grid.num_levels)

        metric_state, interpolation_state = self._build_static_states(static)

        from icon4py.model.atmosphere.dycore import solve_nonhydro as i4_solve_nh
        from icon4py.model.common.decomposition import definitions as i4_decomposition

        i4_config = self.config.to_icon4py()  # runs the granule's slice validation
        self._solve = i4_solve_nh.SolveNonhydro(
            grid=self._i4_grid,
            config=i4_config,
            params=i4_solve_nh.NonHydrostaticParams(i4_config),
            metric_state_nonhydro=metric_state,
            interpolation_state=interpolation_state,
            vertical_params=self._i4_vgrid,
            edge_geometry=edge_geometry,
            cell_geometry=cell_geometry,
            owner_mask=owner_mask,
            backend=self._backend.gt4py_backend,
            exchange=(exchange if exchange is not None else i4_decomposition.single_node_exchange),
        )
        self._exner_ref_mc = metric_state.reference_exner_at_cells_on_model_levels

        self._allocate_private_state()

        # -- substep bookkeeping (serialized via the restart protocol) ------------------
        self._at_initial_timestep = True
        self._steps_done = 0
        self._exner_pr_initialized = False
        self._current_call_substeps = self._substeps if self._substeps else 1

        #: Hook-order recording (acceptance 2): set to a list to record; None = off.
        self.hook_log: list[tuple[Any, ...]] | None = None
        #: Zero-filled default buffers for absent bus slots, cached per shape.
        self._zero_slots: dict[str, xr.DataArray] = {}

    # -- construction helpers ------------------------------------------------------------

    def _build_static_states(self, static: Mapping[str, Any]) -> tuple[Any, Any]:
        """icon4py Metric/Interpolation states from the S11 static mapping.

        Entries may be S11 DataArrays (converted to gt4py fields on this component's
        backend) or ready icon4py fields/scalars (used as-is — the savepoint path).
        """
        import gt4py.next as gtx
        from gt4py.next import common as gtx_common
        from icon4py.model.atmosphere.dycore import dycore_states

        def convert(registry_name: str) -> Any:
            value = static[registry_name]
            if registry_name == "icon:nflat_gradp":
                if isinstance(value, xr.DataArray):
                    return gtx.int32(int(np.asarray(value.data)))
                return gtx.int32(int(value))
            if isinstance(value, xr.DataArray):
                dim_map = _dim_map()
                dims = tuple(dim_map[d] for d in value.dims)
                data = value.data
                if isinstance(data, np.ndarray):
                    data = np.ascontiguousarray(data)
                if registry_name in ("icon:wgtfacq_c", "icon:wgtfacq_e"):
                    # The quadratic surface-extrapolation weights are 3-level fields
                    # whose K DOMAIN is [nlev-3, nlev): both the metrics factory and
                    # the serialized savepoint produce them domain-shifted, and the
                    # consuming stencils read K = nlev-3..nlev-1. Rebuilding them at
                    # K = [0, 3) sends every such read out of the field's domain
                    # (heap garbage — rebuild-dependent, unbounded): the root cause
                    # of the S12 "pentagon" trajectory contamination on factory-fed
                    # grids. Diagnosed + fixed in S13 (STATUS §5). Anchored at the
                    # surface: K-domain = [nlev - k_extent, nlev).
                    nlev = int(self._i4_grid.num_levels)
                    domain = gtx_common.domain(
                        {dims[0]: (0, data.shape[0]), dims[1]: (nlev - data.shape[1], nlev)}
                    )
                    return gtx.as_field(domain, data, allocator=self._backend.gt4py_backend)
                return gtx.as_field(dims, data, allocator=self._backend.gt4py_backend)
            return value  # a ready icon4py field

        metric = dycore_states.MetricStateNonHydro(
            **{field: convert(name) for field, name in STATIC_METRIC_FIELDS.items()}
        )
        interpolation = dycore_states.InterpolationState(
            **{field: convert(name) for field, name in STATIC_INTERPOLATION_FIELDS.items()}
        )
        return metric, interpolation

    def _allocate_private_state(self) -> None:
        """Private time levels + carry, allocated once (icon4py allocation helpers)."""
        from icon4py.model.atmosphere.dycore import dycore_states
        from icon4py.model.common import dimension as dims
        from icon4py.model.common import type_alias as ta
        from icon4py.model.common import utils as i4_utils
        from icon4py.model.common.states import prognostic_state as i4_prognostics
        from icon4py.model.common.utils import data_allocation as data_alloc

        grid = self._i4_grid
        allocator = self._backend.gt4py_backend

        def field(*fdims: Any, half: bool = False, dtype: Any = ta.wpfloat) -> Any:
            extend = {dims.KDim: 1} if half else None
            return data_alloc.zero_field(
                grid, *fdims, dtype=dtype, extend=extend, allocator=allocator
            )

        def prognostic() -> Any:
            return i4_prognostics.PrognosticState(
                vn=field(dims.EdgeDim, dims.KDim),
                w=field(dims.CellDim, dims.KDim, half=True),
                rho=field(dims.CellDim, dims.KDim),
                exner=field(dims.CellDim, dims.KDim),
                theta_v=field(dims.CellDim, dims.KDim),
            )

        self._prognostic_states = i4_utils.TimeStepPair(prognostic(), prognostic())

        self._diag_state = dycore_states.DiagnosticStateNonHydro(
            max_vertical_cfl=data_alloc.scalar_like_array(0.0, allocator),
            theta_v_at_cells_on_half_levels=field(dims.CellDim, dims.KDim, half=True),
            perturbed_exner_at_cells_on_model_levels=field(dims.CellDim, dims.KDim),
            rho_at_cells_on_half_levels=field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
            exner_tendency_due_to_slow_physics=field(dims.CellDim, dims.KDim, dtype=ta.vpfloat),
            grf_tend_rho=field(dims.CellDim, dims.KDim),
            grf_tend_thv=field(dims.CellDim, dims.KDim),
            grf_tend_w=field(dims.CellDim, dims.KDim, half=True),
            mass_flux_at_edges_on_model_levels=field(dims.EdgeDim, dims.KDim),
            normal_wind_tendency_due_to_slow_physics_process=field(
                dims.EdgeDim, dims.KDim, dtype=ta.vpfloat
            ),
            grf_tend_vn=field(dims.EdgeDim, dims.KDim),
            normal_wind_advective_tendency=i4_utils.PredictorCorrectorPair(
                field(dims.EdgeDim, dims.KDim, dtype=ta.vpfloat),
                field(dims.EdgeDim, dims.KDim, dtype=ta.vpfloat),
            ),
            vertical_wind_advective_tendency=i4_utils.PredictorCorrectorPair(
                field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
                field(dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat),
            ),
            tangential_wind=field(dims.EdgeDim, dims.KDim, dtype=ta.vpfloat),
            vn_on_half_levels=field(dims.EdgeDim, dims.KDim, half=True, dtype=ta.vpfloat),
            contravariant_correction_at_cells_on_half_levels=field(
                dims.CellDim, dims.KDim, half=True, dtype=ta.vpfloat
            ),
            rho_iau_increment=field(dims.CellDim, dims.KDim, dtype=ta.vpfloat),
            normal_wind_iau_increment=field(dims.EdgeDim, dims.KDim, dtype=ta.vpfloat),
            exner_iau_increment=field(dims.CellDim, dims.KDim, dtype=ta.vpfloat),
            exner_dynamical_increment=field(dims.CellDim, dims.KDim, dtype=ta.vpfloat),
        )

        self._prep_adv = dycore_states.PrepAdvection(
            vn_traj=field(dims.EdgeDim, dims.KDim),
            mass_flx_me=field(dims.EdgeDim, dims.KDim),
            dynamical_vertical_mass_flux_at_cells_on_half_levels=field(
                dims.CellDim, dims.KDim, half=True
            ),
            dynamical_vertical_volumetric_flux_at_cells_on_half_levels=field(
                dims.CellDim, dims.KDim, half=True
            ),
        )

    # -- introspection ---------------------------------------------------------------

    @property
    def max_vertical_cfl(self) -> float:
        """ICON ``max_vcfl_dyn`` — the CFL diagnostic an adaptive ratio provider reads."""
        return float(np.asarray(self._diag_state.max_vertical_cfl))

    def visit(self, plan_builder: PlanBuilder) -> None:
        """S05/S14 plan hook: unroll the ICON substep-outer nesting.

        ``substep_nesting = "substep_outer"`` routes the compiler to the S14
        per-substep op sequence (ingress → N x [carry swaps → predictor →
        corrector → time-level swap] → egress) via the plan-hook quartet; the
        component-private icon4py state never reaches the vault (§4.5, PLAN S14
        pitfall) — the vault sees only the boundary prognostics' step-level
        ping-pong.
        """
        plan_builder.visit_dynamical_core(self)

    # -- S14 plan hooks (contract: DynamicalCore.substep_nesting) -------------------------

    def plan_ingress(
        self,
        n_substeps: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta,
    ) -> None:
        """T1 step entry: boundary buffers → private time levels + bus (S14).

        Mirrors the ``array_call`` preamble exactly (the substep-count guards ran
        at bind; they are re-checked here so a mutated component fails loudly).
        """
        del outputs, timestep
        if not 1 <= n_substeps <= self.config.ndyn_substeps_max:
            raise ValueError(
                f"component {self.name!r}: bound substep count {n_substeps} is outside "
                f"[1, ndyn_substeps_max={self.config.ndyn_substeps_max}]."
            )
        self._current_call_substeps = n_substeps
        self._ingest(inputs)

    def plan_substep_begin(
        self,
        substep: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta,
    ) -> None:
        """T1 substep entry: the MOST_EFFICIENT advective-tendency pair swaps.

        Component-private carry swaps (never vault swaps); the initial-timestep
        exception lives in the private ``_at_initial_timestep`` flag exactly as
        at T0 (§4.5 restart semantics are preserved verbatim).
        """
        del inputs, outputs, timestep
        diag = self._diag_state
        at_first = substep == 0
        if not (self._at_initial_timestep and at_first):
            diag.vertical_wind_advective_tendency.swap()
            self._record("swap_w_adv_pair", substep)
        if not at_first:
            diag.normal_wind_advective_tendency.swap()
            self._record("swap_vn_adv_pair", substep)

    def plan_substep_end(
        self,
        substep: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta,
    ) -> None:
        """T1 inter-substep boundary: private nnow/nnew time-level swap."""
        del inputs, outputs, timestep
        self._prognostic_states.swap()
        self._record("swap_time_levels", substep)

    def plan_egress(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta,
    ) -> None:
        """T1 step exit: bookkeeping + private state → boundary output buffers."""
        del inputs, timestep
        self._at_initial_timestep = False
        self._steps_done += 1
        self._egress(outputs)

    # -- the call path -----------------------------------------------------------------

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, Any] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Advance one full Δt (= N substeps); returns ``(diagnostics, new_state)``.

        Bus slots absent from ``state`` are zero-filled (SPEC S12: the JW run needs
        no physics), then the S04 base handles negotiation/ingress/egress.
        """
        return super().__call__(self._with_default_bus_slots(state), timestep, out=out)

    def _with_default_bus_slots(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        slots = tuple(self.tendency_port.values())
        if all(slot in state for slot in slots):
            return state
        specs = self._parsed_properties["input_properties"]
        sizes: dict[str, int] = {}
        for value in state.values():
            if isinstance(value, xr.DataArray):
                for dim, size in value.sizes.items():
                    sizes[str(dim)] = int(size)
        augmented = dict(state)
        for slot in slots:
            if slot in augmented:
                continue
            cached = self._zero_slots.get(slot)
            spec = specs[slot]
            shape = tuple(sizes[d] for d in spec.dims)
            if cached is None or cached.data.shape != shape:
                buffer = self.ctx.require_allocator.empty(shape, np.dtype(np.float64))
                buffer[...] = 0.0
                cached = make_dataarray(
                    buffer,
                    name=slot,
                    dims=spec.dims,
                    units=spec.units,
                    location=spec.location.value,
                )
                self._zero_slots[slot] = cached
            augmented[slot] = cached
        return augmented

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        """ICON tier orchestration: substeps outer, predictor→corrector inner.

        Mirrors ``mo_nh_stepping.f90::perform_dyn_substepping`` and the icon4py
        driver ``_do_dyn_substepping`` (REFERENCES.lock
        ``icon-fortran-solve-nonhydro-stepping``, ``icon4py-driver-dyn-substepping``):
        Δτ = Δt/N; tendency-pair swaps implement the MOST_EFFICIENT velocity-advection
        reuse; nnow/nnew swap between substeps but not after the last.
        """
        assert timestep is not None  # timestep_required (base Stepper shape)
        n_substeps = self._resolved_substeps
        if n_substeps < 1:
            raise ValueError(
                f"component {self.name!r}: the substep tier is mandatory for the ICON "
                f"core; got a resolved substep count of {n_substeps}."
            )
        if n_substeps > self.config.ndyn_substeps_max:
            raise ValueError(
                f"component {self.name!r}: resolved substep count {n_substeps} exceeds "
                f"ndyn_substeps_max={self.config.ndyn_substeps_max} (ICON's CFL "
                f"escalation bound)."
            )
        self._current_call_substeps = n_substeps
        sub_dt = timestep / n_substeps
        # timedelta division quantizes to whole microseconds: for a Δt that N does
        # not divide, the granule would silently run with N·Δτ ≠ Δt (and a dtime
        # different from ICON's fp64 dt_dyn). Refuse inexact splits (the S05
        # cadence-mask precedent); adaptive-ratio Δt/N policy is an S13/S14 topic.
        if sub_dt * n_substeps != timestep:
            raise ValueError(
                f"component {self.name!r}: timestep {timestep} is not divisible into "
                f"{n_substeps} substeps at timedelta (microsecond) resolution; choose "
                f"a compatible Δt/ndyn_substeps pair."
            )

        self._ingest(inputs)
        diag = self._diag_state
        for substep in range(n_substeps):
            at_first = substep == 0
            # MOST_EFFICIENT reuse: last corrector tendencies become this predictor's.
            if not (self._at_initial_timestep and at_first):
                diag.vertical_wind_advective_tendency.swap()
                self._record("swap_w_adv_pair", substep)
            if not at_first:
                diag.normal_wind_advective_tendency.swap()
                self._record("swap_vn_adv_pair", substep)
            for stage in range(self.n_stages):
                effective = self._effective_bus(inputs, sub_dt, stage)
                if effective is not None:
                    self._load_bus(effective)
                self.substep_array_call(stage, substep, inputs, outputs, sub_dt)
            if substep != n_substeps - 1:
                self._prognostic_states.swap()
                self._record("swap_time_levels", substep)
        # ICON postpones the final nnow/nnew swap to the end of the integration step;
        # at the component boundary that final state is simply the egressed output.
        self._at_initial_timestep = False
        self._steps_done += 1
        self._egress(outputs)

    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        """One stage (0 = predictor, 1 = corrector) of one substep, Δτ = ``dt``.

        Data flows through the component-private icon4py states
        (``communicates_internally``); ``inputs``/``outputs`` are the step-level
        boundary buffers, ingested/egressed by :meth:`array_call`.
        """
        del inputs, outputs
        n_substeps = self._current_call_substeps
        at_first = substep == 0
        at_last = substep == n_substeps - 1
        dtime = dt.total_seconds()
        if stage == 0:
            self._record(
                "predictor",
                substep,
                dict(
                    at_first_substep=at_first,
                    at_initial_timestep=self._at_initial_timestep,
                ),
            )
            self._solve.run_predictor_step(
                diagnostic_state_nh=self._diag_state,
                prognostic_states=self._prognostic_states,
                z_fields=self._solve.intermediate_fields,
                dtime=dtime,
                at_initial_timestep=self._at_initial_timestep,
                at_first_substep=at_first,
                is_iau_active=False,
                iau_wgt_dyn=0.0,
            )
        elif stage == 1:
            self._record(
                "corrector",
                substep,
                dict(at_first_substep=at_first, at_last_substep=at_last),
            )
            self._solve.run_corrector_step(
                diagnostic_state_nh=self._diag_state,
                prognostic_states=self._prognostic_states,
                z_fields=self._solve.intermediate_fields,
                prep_adv=self._prep_adv,
                second_order_divdamp_factor=self.config.second_order_divdamp_factor,
                dtime=dtime,
                ndyn_substeps_var=n_substeps,
                lprep_adv=self.config.prepare_advection,
                at_first_substep=at_first,
                at_last_substep=at_last,
                is_iau_active=False,
                iau_wgt_dyn=0.0,
            )
            # The two fixups icon4py's time_step() performs after the corrector
            # (solve_nonhydro.py l.1047-1060): LAM boundary exner and halo θv/exner.
            if self._i4_grid.limited_area:
                self._solve._compute_exner_from_rhotheta_in_lateral_boundary(
                    rho=self._prognostic_states.next.rho,
                    theta_v=self._prognostic_states.next.theta_v,
                    exner=self._prognostic_states.next.exner,
                )
            self._solve._update_theta_and_exner_in_halo(
                rho_now=self._prognostic_states.current.rho,
                rho_new=self._prognostic_states.next.rho,
                theta_v_now=self._prognostic_states.current.theta_v,
                theta_v_new=self._prognostic_states.next.theta_v,
                exner_now=self._prognostic_states.current.exner,
                exner_new=self._prognostic_states.next.exner,
            )
        else:
            raise ValueError(f"{self.name}: stage must be 0 or 1, got {stage}.")

    def stage_array_call(
        self,
        stage: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        """Degenerate single-substep form of :meth:`substep_array_call` (S04 hook).

        Not used by the ICON orchestration (``array_call`` always substeps); provided
        so the frozen S04 subclass contract is complete.
        """
        self._current_call_substeps = 1
        self.substep_array_call(stage, 0, inputs, outputs, dt)

    # -- data plumbing -------------------------------------------------------------------

    def _ingest(self, inputs: dict[str, FieldBuffer]) -> None:
        """Boundary buffers -> private nnow/nnew time levels + bus fields."""
        current = self._prognostic_states.current
        following = self._prognostic_states.next
        for field_name, input_name in (
            ("vn", "icon:normal_wind"),
            ("w", "upward_air_velocity_on_interface_levels"),
            ("rho", "air_density"),
            ("exner", "icon:exner_function"),
            ("theta_v", "icon:virtual_potential_temperature"),
        ):
            buffer = inputs[input_name]
            getattr(current, field_name).ndarray[...] = buffer
            getattr(following, field_name).ndarray[...] = buffer
        self._load_bus(
            {
                "icon:ddt_vn_phy": inputs["icon:ddt_vn_phy"],
                "icon:ddt_exner_phy": inputs["icon:ddt_exner_phy"],
            }
        )
        if not self._exner_pr_initialized:
            # Cold start: exner_pr = exner - exner_ref (mo_nh_stepping.f90 l.396-400,
            # compute_exner_pert before the time loop; restarts restore it instead).
            self._diag_state.perturbed_exner_at_cells_on_model_levels.ndarray[...] = (
                inputs["icon:exner_function"] - self._exner_ref_mc.ndarray
            )
            self._exner_pr_initialized = True

    def _load_bus(self, values: Mapping[str, Any]) -> None:
        diag = self._diag_state
        diag.normal_wind_tendency_due_to_slow_physics_process.ndarray[...] = values[
            "icon:ddt_vn_phy"
        ]
        diag.exner_tendency_due_to_slow_physics.ndarray[...] = values["icon:ddt_exner_phy"]

    def _effective_bus(
        self, inputs: dict[str, FieldBuffer], sub_dt: timedelta, stage: int
    ) -> dict[str, Any] | None:
        """Slow port + one fast-coupling evaluation (the per-stage fast tier).

        Empty in the ICON preset (returns ``None``: the slow values loaded at ingress
        stand). With a ``fast_tendency_component``, its tendencies are evaluated on
        the **latest provisional state** (Fig. 3.9): the substep-start time level
        before the predictor (stage 0), the predictor's output before the corrector
        (stage 1) — and summed onto the slow values.
        """
        if self._fast is None:
            return None
        state = self._wrap_provisional_state(stage)
        tendencies, _diagnostics = self._fast(state, sub_dt)
        effective = {
            "icon:ddt_vn_phy": inputs["icon:ddt_vn_phy"],
            "icon:ddt_exner_phy": inputs["icon:ddt_exner_phy"],
        }
        for field_name, array in tendencies.items():
            slot = self.tendency_port[field_name]  # validated at construction (S04)
            effective[slot] = effective[slot] + array.data
        return effective

    def _wrap_provisional_state(self, stage: int) -> dict[str, Any]:
        """The latest provisional prognostics as boundary DataArrays (fast tier).

        At stage 0 (predictor) the latest provisional state is the substep-start
        time level (``current``); at stage 1 (corrector) it is the predictor's
        output (``next``) — the S04/Fig. 3.9 "latest provisional state" contract.
        """
        specs = self._parsed_properties["input_properties"]
        current = self._prognostic_states.next if stage == 1 else self._prognostic_states.current
        state: dict[str, Any] = {}
        for field_name, input_name in (
            ("vn", "icon:normal_wind"),
            ("w", "upward_air_velocity_on_interface_levels"),
            ("rho", "air_density"),
            ("exner", "icon:exner_function"),
            ("theta_v", "icon:virtual_potential_temperature"),
        ):
            spec = specs[input_name]
            state[input_name] = make_dataarray(
                getattr(current, field_name).ndarray,
                name=input_name,
                dims=spec.dims,
                units=spec.units,
                location=spec.location.value,
            )
        return state

    def _egress(self, outputs: dict[str, FieldBuffer]) -> None:
        following = self._prognostic_states.next
        for field_name, output_name in (
            ("vn", "icon:normal_wind"),
            ("w", "upward_air_velocity_on_interface_levels"),
            ("rho", "air_density"),
            ("exner", "icon:exner_function"),
            ("theta_v", "icon:virtual_potential_temperature"),
        ):
            outputs[output_name][...] = getattr(following, field_name).ndarray

    def _record(self, event: str, substep: int, flags: Mapping[str, Any] | None = None) -> None:
        if self.hook_log is not None:
            entry: tuple[Any, ...] = (event, substep)
            if flags is not None:
                entry = (*entry, dict(flags))
            self.hook_log.append(entry)

    # -- restart / functional state (§4.5, §8.5) -----------------------------------------

    def _restart_targets(self) -> dict[str, Any]:
        """Restart key -> the live buffer (gt4py field ``ndarray`` or 0-d value)."""
        current = self._prognostic_states.current
        following = self._prognostic_states.next
        diag = self._diag_state
        prep = self._prep_adv
        z_fields = self._solve.intermediate_fields
        return {
            "nnow/vn": current.vn.ndarray,
            "nnow/w": current.w.ndarray,
            "nnow/rho": current.rho.ndarray,
            "nnow/exner": current.exner.ndarray,
            "nnow/theta_v": current.theta_v.ndarray,
            "nnew/vn": following.vn.ndarray,
            "nnew/w": following.w.ndarray,
            "nnew/rho": following.rho.ndarray,
            "nnew/exner": following.exner.ndarray,
            "nnew/theta_v": following.theta_v.ndarray,
            "carry/ddt_vn_apc_predictor": diag.normal_wind_advective_tendency.predictor.ndarray,
            "carry/ddt_vn_apc_corrector": diag.normal_wind_advective_tendency.corrector.ndarray,
            "carry/ddt_w_adv_predictor": diag.vertical_wind_advective_tendency.predictor.ndarray,
            "carry/ddt_w_adv_corrector": diag.vertical_wind_advective_tendency.corrector.ndarray,
            "carry/vt": diag.tangential_wind.ndarray,
            "carry/vn_ie": diag.vn_on_half_levels.ndarray,
            "carry/w_concorr_c": (diag.contravariant_correction_at_cells_on_half_levels.ndarray),
            "carry/theta_v_ic": diag.theta_v_at_cells_on_half_levels.ndarray,
            "carry/rho_ic": diag.rho_at_cells_on_half_levels.ndarray,
            "carry/exner_pr": diag.perturbed_exner_at_cells_on_model_levels.ndarray,
            "carry/mass_fl_e": diag.mass_flux_at_edges_on_model_levels.ndarray,
            "carry/exner_dyn_incr": diag.exner_dynamical_increment.ndarray,
            "carry/max_vertical_cfl": diag.max_vertical_cfl,
            "prep_adv/vn_traj": prep.vn_traj.ndarray,
            "prep_adv/mass_flx_me": prep.mass_flx_me.ndarray,
            "prep_adv/mass_flx_ic": (
                prep.dynamical_vertical_mass_flux_at_cells_on_half_levels.ndarray
            ),
            "prep_adv/vol_flx_ic": (
                prep.dynamical_vertical_volumetric_flux_at_cells_on_half_levels.ndarray
            ),
            "z/gradh_exner": z_fields.horizontal_pressure_gradient.ndarray,
            "z/rho_e": z_fields.rho_at_edges_on_model_levels.ndarray,
            "z/theta_v_e": z_fields.theta_v_at_edges_on_model_levels.ndarray,
            "z/kin_hor_e": (z_fields.horizontal_kinetic_energy_at_edges_on_model_levels.ndarray),
            "z/vt_ie": z_fields.tangential_wind_on_half_levels.ndarray,
            "z/graddiv_vn": (z_fields.horizontal_gradient_of_normal_wind_divergence.ndarray),
            "z/dwdz_dd": z_fields.dwdz_at_cells_on_model_levels.ndarray,
        }

    def restart_state(self) -> dict[str, xr.DataArray]:
        """Both prognostic time levels + the velocity-advection carry (SPEC S12)."""
        result: dict[str, xr.DataArray] = {}
        targets = self._restart_targets()
        for key, dims, units in _RESTART_SCHEMA:
            if key == "meta/at_initial_timestep":
                value = np.asarray(float(self._at_initial_timestep))
            elif key == "meta/steps_done":
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
            if key == "meta/at_initial_timestep":
                self._at_initial_timestep = bool(data)
            elif key == "meta/steps_done":
                self._steps_done = int(data)
            elif key == "carry/max_vertical_cfl":
                self._diag_state.max_vertical_cfl[...] = data
            else:
                targets[key][...] = data
        self._exner_pr_initialized = True  # carry/exner_pr was just restored

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """The restart schema as PropertySpecs (F-tier declaration; consumption is P6)."""
        specs: dict[str, PropertySpec] = {}
        for key, dims, units in _RESTART_SCHEMA:
            specs[key] = PropertySpec(name=key, dims=dims, units=units, location=_location_of(dims))
        return MappingProxyType(specs)


# --------------------------------------------------------------------------------------
# Production geometry derivation (icon4py standalone-driver recipe; REFERENCES.lock
# ``icon4py-driver-dyn-substepping``).
# --------------------------------------------------------------------------------------


def _geometry_from_grid(grid: IconGrid) -> tuple[Any, Any]:
    """icon4py ``(CellParams, EdgeParams)`` from the S11 grid's geometry source."""
    from icon4py.model.common.grid import geometry_attributes as geometry_meta
    from icon4py.model.common.grid import states as grid_states
    from icon4py.model.common.states import factory as states_factory

    source = grid.icon4py_geometry
    cell_params = grid_states.CellParams(
        cell_center_lat=source.get(geometry_meta.CELL_LAT),
        cell_center_lon=source.get(geometry_meta.CELL_LON),
        area=source.get(geometry_meta.CELL_AREA),
        mean_cell_area=source.get(
            geometry_meta.MEAN_CELL_AREA, states_factory.RetrievalType.SCALAR
        ),
    )
    edge_params = grid_states.EdgeParams(
        tangent_orientation=source.get(geometry_meta.TANGENT_ORIENTATION),
        inverse_primal_edge_lengths=source.get(f"inverse_of_{geometry_meta.EDGE_LENGTH}"),
        inverse_dual_edge_lengths=source.get(f"inverse_of_{geometry_meta.DUAL_EDGE_LENGTH}"),
        inverse_vertex_vertex_lengths=source.get(
            f"inverse_of_{geometry_meta.VERTEX_VERTEX_LENGTH}"
        ),
        primal_normal_vert_x=source.get(geometry_meta.EDGE_NORMAL_VERTEX_U),
        primal_normal_vert_y=source.get(geometry_meta.EDGE_NORMAL_VERTEX_V),
        dual_normal_vert_x=source.get(geometry_meta.EDGE_TANGENT_VERTEX_U),
        dual_normal_vert_y=source.get(geometry_meta.EDGE_TANGENT_VERTEX_V),
        primal_normal_cell_x=source.get(geometry_meta.EDGE_NORMAL_CELL_U),
        dual_normal_cell_x=source.get(geometry_meta.EDGE_TANGENT_CELL_U),
        primal_normal_cell_y=source.get(geometry_meta.EDGE_NORMAL_CELL_V),
        dual_normal_cell_y=source.get(geometry_meta.EDGE_TANGENT_CELL_V),
        edge_areas=source.get(geometry_meta.EDGE_AREA),
        coriolis_frequency=source.get(geometry_meta.CORIOLIS_PARAMETER),
        edge_center_lat=source.get(geometry_meta.EDGE_LAT),
        edge_center_lon=source.get(geometry_meta.EDGE_LON),
        primal_normal_x=source.get(geometry_meta.EDGE_NORMAL_U),
        primal_normal_y=source.get(geometry_meta.EDGE_NORMAL_V),
    )
    return cell_params, edge_params


def _owner_mask_from_grid(grid: IconGrid, backend: Any) -> Any:
    """Cell owner mask from the grid's decomposition info (single node: all True)."""
    import gt4py.next as gtx
    from icon4py.model.common import dimension as i4_dims

    mask = grid.decomposition_info.owner_mask(i4_dims.CellDim)
    return gtx.as_field((i4_dims.CellDim,), mask, allocator=backend.gt4py_backend)
