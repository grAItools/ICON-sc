"""S12 acceptance 2/5 (+ config/static/restart contracts): ``NonhydroSolver`` on a
stubbed granule.

The component is constructed **for real** (icon4py ``SolveNonhydro`` on the icon4py
``SimpleGrid`` with a zero static state — construction wires programs but computes
nothing beyond the ctor-time divdamp profile); the predictor/corrector stage bodies
are then monkeypatched with recorders, so these tests exercise exactly the symcon
orchestration layer: tier nesting, tendency-pair reuse swaps, time-level swaps, bus
zero-fill, restart/functional-state plumbing. The hand-written expected hook
sequences transcribe ICON's documented substepping (REFERENCES.lock
``icon-fortran-solve-nonhydro-stepping``, ``icon4py-driver-dyn-substepping``);
running the *real* stages against serialized data is ``test_nonhydro_datatest.py``.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest
import xarray as xr

from symcon.core.components.base import TendencyComponent
from symcon.core.context import ComputeContext
from symcon.core.coupling.concurrent import ConcurrentCoupling
from symcon.core.state import canonical_units, make_dataarray
from symcon.icon.components import NonhydroConfig, NonhydroSolver, icon_namelist_origins
from symcon.icon.components.dycore import (
    _RESTART_SCHEMA,
    STATIC_FIELDS,
    STATIC_INTERPOLATION_FIELDS,
    STATIC_METRIC_FIELDS,
)
from symcon.icon.grid import SleveConfig, VerticalGrid

pytest.importorskip("icon4py.model.atmosphere.dycore", reason="icon4py dycore not installed")

NLEV = 10
DT = timedelta(seconds=10.0)

#: symcon dims -> (SimpleGrid axis length resolver); sparse sizes are SimpleGrid's.
_STATIC_TABLE: dict[str, tuple[tuple[str, ...], Any]] = {
    "icon:mask_prog_halo_c": (("cell",), bool),
    "icon:rayleigh_w": (("height_interface",), float),
    "icon:wgtfac_c": (("cell", "height_interface"), float),
    "icon:wgtfacq_c": (("cell", "height"), float),
    "icon:wgtfac_e": (("edge", "height_interface"), float),
    "icon:wgtfacq_e": (("edge", "height"), float),
    "icon:exner_exfac": (("cell", "height"), float),
    "icon:exner_ref_mc": (("cell", "height"), float),
    "icon:rho_ref_mc": (("cell", "height"), float),
    "icon:theta_ref_mc": (("cell", "height"), float),
    "icon:rho_ref_me": (("edge", "height"), float),
    "icon:theta_ref_me": (("edge", "height"), float),
    "icon:theta_ref_ic": (("cell", "height_interface"), float),
    "icon:d_exner_dz_ref_ic": (("cell", "height_interface"), float),
    "icon:ddqz_z_half": (("cell", "height_interface"), float),
    "icon:d2dexdz2_fac1_mc": (("cell", "height"), float),
    "icon:d2dexdz2_fac2_mc": (("cell", "height"), float),
    "icon:ddxn_z_full": (("edge", "height"), float),
    "icon:ddqz_z_full_e": (("edge", "height"), float),
    "icon:ddxt_z_full": (("edge", "height"), float),
    "icon:inv_ddqz_z_full": (("cell", "height"), float),
    "icon:vertoffset_gradp": (("edge", "e2c", "height"), np.int32),
    "icon:zdiff_gradp": (("edge", "e2c", "height"), float),
    "icon:pg_exdist": (("edge", "height"), float),
    "icon:vwind_expl_wgt": (("cell",), float),
    "icon:vwind_impl_wgt": (("cell",), float),
    "icon:hmask_dd3d": (("edge",), float),
    "icon:scalfac_dd3d": (("height",), float),
    "icon:coeff1_dwdz": (("cell", "height"), float),
    "icon:coeff2_dwdz": (("cell", "height"), float),
    "icon:coeff_gradekin": (("edge", "e2c"), float),
    "icon:e_bln_c_s": (("cell", "c2e"), float),
    "icon:rbf_vec_coeff_v1": (("vertex", "v2e"), float),
    "icon:rbf_vec_coeff_v2": (("vertex", "v2e"), float),
    "icon:geofac_div": (("cell", "c2e"), float),
    "icon:geofac_n2s": (("cell", "c2e2co"), float),
    "icon:geofac_grg_x": (("cell", "c2e2co"), float),
    "icon:geofac_grg_y": (("cell", "c2e2co"), float),
    "icon:nudgecoeff_e": (("edge",), float),
    "icon:c_lin_e": (("edge", "e2c"), float),
    "icon:geofac_grdiv": (("edge", "e2c2eo"), float),
    "icon:rbf_vec_coeff_e": (("edge", "e2c2e"), float),
    "icon:c_intp": (("vertex", "v2c"), float),
    "icon:geofac_rot": (("vertex", "v2e"), float),
    "icon:pos_on_tplane_e_x": (("edge", "e2c"), float),
    "icon:pos_on_tplane_e_y": (("edge", "e2c"), float),
    "icon:e_flx_avg": (("edge", "e2c2eo"), float),
}


def _zero_static(grid: Any) -> dict[str, xr.DataArray]:
    sizes = {
        "cell": grid.num_cells,
        "edge": grid.num_edges,
        "vertex": grid.num_vertices,
        "height": NLEV,
        "height_interface": NLEV + 1,
        "e2c": 2,
        "c2e": 3,
        "c2e2co": 4,
        "e2c2eo": 5,
        "e2c2e": 4,
        "v2e": 6,
        "v2c": 6,
    }
    static: dict[str, xr.DataArray] = {
        name: xr.DataArray(
            np.zeros(tuple(sizes[d] for d in dims), dtype=dtype), dims=dims, name=name
        )
        for name, (dims, dtype) in _STATIC_TABLE.items()
    }
    static["icon:nflat_gradp"] = xr.DataArray(np.asarray(4, dtype=np.int32))
    return static


def _stub_geometry(grid: Any) -> tuple[Any, Any, Any]:
    import gt4py.next as gtx
    from icon4py.model.common import dimension as dims
    from icon4py.model.common.grid import states as grid_states

    def edge(sparse: Any = None, n: int = 0) -> Any:
        if sparse is None:
            return gtx.as_field((dims.EdgeDim,), np.zeros(grid.num_edges))
        return gtx.as_field((dims.EdgeDim, sparse), np.zeros((grid.num_edges, n)))

    def cell() -> Any:
        return gtx.as_field((dims.CellDim,), np.zeros(grid.num_cells))

    edge_params = grid_states.EdgeParams(
        tangent_orientation=edge(),
        inverse_primal_edge_lengths=edge(),
        inverse_dual_edge_lengths=edge(),
        inverse_vertex_vertex_lengths=edge(),
        primal_normal_vert_x=edge(dims.E2C2VDim, 4),
        primal_normal_vert_y=edge(dims.E2C2VDim, 4),
        dual_normal_vert_x=edge(dims.E2C2VDim, 4),
        dual_normal_vert_y=edge(dims.E2C2VDim, 4),
        primal_normal_cell_x=edge(dims.E2CDim, 2),
        dual_normal_cell_x=edge(dims.E2CDim, 2),
        primal_normal_cell_y=edge(dims.E2CDim, 2),
        dual_normal_cell_y=edge(dims.E2CDim, 2),
        edge_areas=edge(),
        coriolis_frequency=edge(),
        edge_center_lat=edge(),
        edge_center_lon=edge(),
        primal_normal_x=edge(),
        primal_normal_y=edge(),
    )
    cell_params = grid_states.CellParams(
        cell_center_lat=cell(), cell_center_lon=cell(), area=cell(), mean_cell_area=1.0
    )

    mask = gtx.as_field((dims.CellDim,), np.ones(grid.num_cells, dtype=bool))
    return cell_params, edge_params, mask


def _make_solver(**kwargs: Any) -> NonhydroSolver:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    vgrid = VerticalGrid.from_config(SleveConfig(num_levels=NLEV))
    cell_params, edge_params, mask = _stub_geometry(i4_grid)
    kwargs.setdefault("cfg", NonhydroConfig(ndyn_substeps=2))
    cfg = kwargs.pop("cfg")
    return NonhydroSolver(
        i4_grid,
        vgrid,
        _zero_static(i4_grid),
        cfg,
        ComputeContext(backend="embedded"),
        cell_geometry=cell_params,
        edge_geometry=edge_params,
        owner_mask=mask,
        **kwargs,
    )


def _stub_stages(solver: NonhydroSolver) -> list[dict[str, Any]]:
    """Replace the granule stage bodies with recorders; return the record list."""
    calls: list[dict[str, Any]] = []

    def predictor(**kwargs: Any) -> None:
        calls.append(
            {
                "stage": "predictor",
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k in ("at_initial_timestep", "at_first_substep", "dtime")
                },
            }
        )

    def corrector(**kwargs: Any) -> None:
        calls.append(
            {
                "stage": "corrector",
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k in ("at_first_substep", "at_last_substep", "dtime", "ndyn_substeps_var")
                },
            }
        )

    solver._solve.run_predictor_step = predictor
    solver._solve.run_corrector_step = corrector
    solver._solve._update_theta_and_exner_in_halo = lambda **kwargs: None
    return calls


def _state(solver: NonhydroSolver, *, bus: dict[str, float] | None = None) -> dict[str, Any]:
    grid = solver._i4_grid
    n_cells, n_edges = grid.num_cells, grid.num_edges
    shapes = {
        "icon:normal_wind": (("edge", "height"), (n_edges, NLEV)),
        "upward_air_velocity_on_interface_levels": (
            ("cell", "height_interface"),
            (n_cells, NLEV + 1),
        ),
        "air_density": (("cell", "height"), (n_cells, NLEV)),
        "icon:exner_function": (("cell", "height"), (n_cells, NLEV)),
        "icon:virtual_potential_temperature": (("cell", "height"), (n_cells, NLEV)),
    }
    state: dict[str, Any] = {}
    for index, (name, (dims, shape)) in enumerate(shapes.items()):
        values = np.full(shape, 1.0 + index, dtype=np.float64)
        state[name] = make_dataarray(
            values,
            name=name,
            dims=dims,
            units=canonical_units(name),
            location="edge" if dims[0] == "edge" else "cell",
        )
    for slot, value in (bus or {}).items():
        dims = ("edge", "height") if slot == "icon:ddt_vn_phy" else ("cell", "height")
        shape = (n_edges, NLEV) if dims[0] == "edge" else (n_cells, NLEV)
        state[slot] = make_dataarray(
            np.full(shape, value, dtype=np.float64),
            name=slot,
            dims=dims,
            units=canonical_units(slot),
            location=dims[0],
        )
    return state


# -- configuration contracts -------------------------------------------------------------


def test_config_carries_icon_namelist_origins() -> None:
    cfg = NonhydroConfig()
    origins = icon_namelist_origins(cfg)
    assert set(origins) == {f.name for f in dataclasses.fields(cfg)}
    assert origins["igradp_method"] == "nonhydrostatic_nml:igradp_method"
    assert origins["divdamp_order"] == "nonhydrostatic_nml:divdamp_order"
    assert origins["itime_scheme"] == "nonhydrostatic_nml:itime_scheme"
    assert origins["rayleigh_type"] == "nonhydrostatic_nml:rayleigh_type"
    assert origins["ndyn_substeps"] == "nonhydrostatic_nml:ndyn_substeps"
    # every origin names its namelist (or documents a runtime-derived source)
    assert all(
        "_nml:" in origin or "derived" in origin or "config" in origin
        for origin in origins.values()
    )


def test_config_defaults_match_icon4py() -> None:
    """Our literal defaults are icon4py v0.2.0 defaults (no silent drift)."""
    from icon4py.model.atmosphere.dycore import solve_nonhydro as i4_solve_nh

    ours = NonhydroConfig().to_icon4py()
    theirs = i4_solve_nh.NonHydrostaticConfig()
    for attr in (
        "itime_scheme",
        "iadv_rhotheta",
        "igradp_method",
        "rayleigh_type",
        "divdamp_order",
        "divdamp_type",
        "rhotheta_offctr",
        "veladv_offctr",
        "max_nudging_coefficient",
        "fourth_order_divdamp_factor",
        "fourth_order_divdamp_factor2",
        "fourth_order_divdamp_factor3",
        "fourth_order_divdamp_factor4",
        "fourth_order_divdamp_z",
        "fourth_order_divdamp_z2",
        "fourth_order_divdamp_z3",
        "fourth_order_divdamp_z4",
        "l_vert_nested",
        "deepatmos_mode",
        "iau_init",
        "extra_diffu",
    ):
        assert getattr(ours, attr) == getattr(theirs, attr), attr


def test_config_roundtrip_from_icon4py() -> None:
    from icon4py.model.atmosphere.dycore import solve_nonhydro as i4_solve_nh

    theirs = i4_solve_nh.NonHydrostaticConfig(veladv_offctr=0.3)
    cfg = NonhydroConfig.from_icon4py(theirs, ndyn_substeps=3)
    assert cfg.veladv_offctr == 0.3
    assert cfg.ndyn_substeps == 3
    assert cfg.to_icon4py().veladv_offctr == 0.3


def test_config_rejects_out_of_slice_knobs() -> None:
    """The icon4py granule validation runs at config translation time."""
    with pytest.raises(NotImplementedError):
        NonhydroConfig(itime_scheme=5).to_icon4py()
    with pytest.raises(NotImplementedError):
        NonhydroConfig(igradp_method=1).to_icon4py()


def test_config_rejects_iau() -> None:
    """iau_init=True fails loudly at construction: the icon4py granule would accept
    it, but this slice hard-wires is_iau_active=False into every stage invocation
    (review round 1, MINOR 1)."""
    with pytest.raises(NotImplementedError, match="iau_init"):
        NonhydroConfig(iau_init=True)


# -- static-state enumeration (the S11 coordination point) --------------------------------


def test_static_enumeration_covers_icon4py_state_dataclasses_exactly() -> None:
    from icon4py.model.atmosphere.dycore import dycore_states

    metric_fields = {f.name for f in dataclasses.fields(dycore_states.MetricStateNonHydro)}
    interp_fields = {f.name for f in dataclasses.fields(dycore_states.InterpolationState)}
    assert set(STATIC_METRIC_FIELDS) == metric_fields
    assert set(STATIC_INTERPOLATION_FIELDS) == interp_fields


def test_static_enumeration_is_the_s11_production_set() -> None:
    """Every required static name is produced by S11 metrics()/interpolation()."""
    from symcon.icon.grid import INTERPOLATION_FIELDS, METRICS_FIELDS

    produced = set(METRICS_FIELDS) | set(INTERPOLATION_FIELDS)
    assert set(STATIC_FIELDS) <= produced


def test_missing_static_field_raises() -> None:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    vgrid = VerticalGrid.from_config(SleveConfig(num_levels=NLEV))
    static = _zero_static(i4_grid)
    static.pop("icon:wgtfac_c")
    cell_params, edge_params, mask = _stub_geometry(i4_grid)
    with pytest.raises(ValueError, match="icon:wgtfac_c"):
        NonhydroSolver(
            i4_grid,
            vgrid,
            static,
            NonhydroConfig(ndyn_substeps=2),
            ComputeContext(backend="embedded"),
            cell_geometry=cell_params,
            edge_geometry=edge_params,
            owner_mask=mask,
        )


def test_raw_icon4py_grid_requires_explicit_geometry() -> None:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    vgrid = VerticalGrid.from_config(SleveConfig(num_levels=NLEV))
    with pytest.raises(ValueError, match="edge_geometry"):
        NonhydroSolver(
            i4_grid,
            vgrid,
            _zero_static(i4_grid),
            NonhydroConfig(ndyn_substeps=2),
            ComputeContext(backend="embedded"),
        )


# -- acceptance 2: stage/substep orchestration ---------------------------------------------


def test_hook_order_matches_icon_sequence_for_two_substeps() -> None:
    """Hand-written expected sequence, ndyn_substeps=2, initial + subsequent step.

    ICON semantics (perform_dyn_substepping + the icon4py driver): per substep
    predictor→corrector; the vertical-wind advective pair swaps before every substep
    except the very first of the initial step; the normal-wind pair swaps before
    every substep except the first of *each* step (velocity-advection reuse of
    itime_scheme=4); nnow/nnew swap between substeps, not after the last.
    """
    solver = _make_solver()
    calls = _stub_stages(solver)
    solver.hook_log = []

    solver(_state(solver), DT)
    expected_initial = [
        ("predictor", 0, {"at_first_substep": True, "at_initial_timestep": True}),
        ("corrector", 0, {"at_first_substep": True, "at_last_substep": False}),
        ("swap_time_levels", 0),
        ("swap_w_adv_pair", 1),
        ("swap_vn_adv_pair", 1),
        ("predictor", 1, {"at_first_substep": False, "at_initial_timestep": True}),
        ("corrector", 1, {"at_first_substep": False, "at_last_substep": True}),
    ]
    assert solver.hook_log == expected_initial

    solver.hook_log = []
    solver(_state(solver), DT)
    expected_subsequent = [
        # not the initial step: the w-advection pair swaps at the first substep too
        # (the previous step's last corrector tendency is reused), the vn pair not.
        ("swap_w_adv_pair", 0),
        ("predictor", 0, {"at_first_substep": True, "at_initial_timestep": False}),
        ("corrector", 0, {"at_first_substep": True, "at_last_substep": False}),
        ("swap_time_levels", 0),
        ("swap_w_adv_pair", 1),
        ("swap_vn_adv_pair", 1),
        ("predictor", 1, {"at_first_substep": False, "at_initial_timestep": False}),
        ("corrector", 1, {"at_first_substep": False, "at_last_substep": False}),
    ]
    # fix the last corrector flag: substep 1 of 2 is the last one
    expected_subsequent[-1] = (
        "corrector",
        1,
        {"at_first_substep": False, "at_last_substep": True},
    )
    assert solver.hook_log == expected_subsequent

    # The granule received the matching flags and the substep Δτ = Δt/N.
    assert [c["stage"] for c in calls] == ["predictor", "corrector"] * 4
    assert all(c["dtime"] == DT.total_seconds() / 2 for c in calls)
    correctors = [c for c in calls if c["stage"] == "corrector"]
    assert all(c["ndyn_substeps_var"] == 2 for c in correctors)


def test_ratio_provider_drives_substep_count() -> None:
    solver = _make_solver(
        cfg=NonhydroConfig(ndyn_substeps=2), substeps=0, ratio_provider=lambda state: 3
    )
    _stub_stages(solver)
    solver.hook_log = []
    solver(_state(solver), timedelta(seconds=9))  # divisible by the resolved ratio 3
    predictors = [entry for entry in solver.hook_log if entry[0] == "predictor"]
    assert [entry[1] for entry in predictors] == [0, 1, 2]


def test_ratio_provider_bounded_by_ndyn_substeps_max() -> None:
    solver = _make_solver(
        cfg=NonhydroConfig(ndyn_substeps=2, ndyn_substeps_max=4),
        substeps=0,
        ratio_provider=lambda state: 5,
    )
    _stub_stages(solver)
    with pytest.raises(ValueError, match="ndyn_substeps_max"):
        solver(_state(solver), DT)


# -- bus port -------------------------------------------------------------------------------


def test_bus_slots_default_to_zeros() -> None:
    """A state without physics tendencies is accepted; the granule sees zeros."""
    solver = _make_solver()
    seen: list[tuple[float, float]] = []

    def predictor(**kwargs: Any) -> None:
        diag = solver._diag_state
        seen.append(
            (
                float(
                    np.max(np.abs(diag.normal_wind_tendency_due_to_slow_physics_process.ndarray))
                ),
                float(np.max(np.abs(diag.exner_tendency_due_to_slow_physics.ndarray))),
            )
        )

    solver._solve.run_predictor_step = predictor
    solver._solve.run_corrector_step = lambda **kwargs: None
    solver._solve._update_theta_and_exner_in_halo = lambda **kwargs: None

    solver(_state(solver), DT)  # no icon:ddt_* in the state
    assert seen == [(0.0, 0.0), (0.0, 0.0)]


def test_bus_slots_reach_the_granule() -> None:
    solver = _make_solver()
    seen: list[tuple[float, float]] = []

    def predictor(**kwargs: Any) -> None:
        diag = solver._diag_state
        seen.append(
            (
                float(diag.normal_wind_tendency_due_to_slow_physics_process.ndarray[0, 0]),
                float(diag.exner_tendency_due_to_slow_physics.ndarray[0, 0]),
            )
        )

    solver._solve.run_predictor_step = predictor
    solver._solve.run_corrector_step = lambda **kwargs: None
    solver._solve._update_theta_and_exner_in_halo = lambda **kwargs: None

    solver(_state(solver, bus={"icon:ddt_vn_phy": 3.5e-4, "icon:ddt_exner_phy": -2.0e-6}), DT)
    assert seen == [(3.5e-4, -2.0e-6), (3.5e-4, -2.0e-6)]


class _ConstantVnTendency(TendencyComponent):
    """Per-stage fast-tier probe: a constant vn tendency."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": ("edge", "height"), "units": "m s-1"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": ("edge", "height"), "units": "m s-2"},
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {}

    def array_call(self, inputs: Any, outputs: Any, timestep: Any) -> None:
        outputs["icon:normal_wind"][...] = 2.0e-4


def test_fast_tendency_component_sums_onto_the_slow_port() -> None:
    """The per-stage fast tier (empty in the ICON preset) adds to the bus values."""
    solver = _make_solver(fast_tendency_component=ConcurrentCoupling([_ConstantVnTendency()]))
    seen: list[float] = []

    def predictor(**kwargs: Any) -> None:
        diag = solver._diag_state
        seen.append(float(diag.normal_wind_tendency_due_to_slow_physics_process.ndarray[0, 0]))

    solver._solve.run_predictor_step = predictor
    solver._solve.run_corrector_step = lambda **kwargs: None
    solver._solve._update_theta_and_exner_in_halo = lambda **kwargs: None

    solver(_state(solver, bus={"icon:ddt_vn_phy": 1.0e-4}), DT)
    assert seen == pytest.approx([3.0e-4, 3.0e-4])  # slow 1e-4 + fast 2e-4, each substep


class _VnDependentTendency(TendencyComponent):
    """State-dependent fast-tier probe: tendency = 0.1 · vn (per point)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": ("edge", "height"), "units": "m s-1"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        "icon:normal_wind": {"dims": ("edge", "height"), "units": "m s-2"},
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {}

    def array_call(self, inputs: Any, outputs: Any, timestep: Any) -> None:
        outputs["icon:normal_wind"][...] = 0.1 * inputs["icon:normal_wind"]


def test_fast_tendency_sees_the_latest_provisional_state() -> None:
    """Fig. 3.9 contract (review round 1, MINOR 3): the fast coupling is evaluated
    on the substep-start time level before the predictor and on the *predictor's
    output* before the corrector — observable with a state-dependent tendency."""
    solver = _make_solver(fast_tendency_component=ConcurrentCoupling([_VnDependentTendency()]))
    seen: list[tuple[str, float]] = []

    def predictor(**kwargs: Any) -> None:
        diag = solver._diag_state
        seen.append(
            ("P", float(diag.normal_wind_tendency_due_to_slow_physics_process.ndarray[0, 0]))
        )
        # the predictor's provisional output, visible to the corrector-stage fast call
        solver._prognostic_states.next.vn.ndarray[...] = 3.0

    def corrector(**kwargs: Any) -> None:
        diag = solver._diag_state
        seen.append(
            ("C", float(diag.normal_wind_tendency_due_to_slow_physics_process.ndarray[0, 0]))
        )

    solver._solve.run_predictor_step = predictor
    solver._solve.run_corrector_step = corrector
    solver._solve._update_theta_and_exner_in_halo = lambda **kwargs: None

    solver(_state(solver, bus={"icon:ddt_vn_phy": 1.0e-4}), DT)  # ingested vn = 1.0
    assert [label for label, _ in seen] == ["P", "C", "P", "C"]
    assert [value for _, value in seen] == pytest.approx(
        [
            1.0e-4 + 0.1 * 1.0,  # substep 0 predictor: substep-start vn = 1.0
            1.0e-4 + 0.1 * 3.0,  # substep 0 corrector: predictor output vn = 3.0
            1.0e-4 + 0.1 * 3.0,  # substep 1 predictor: swapped-in vn = 3.0
            1.0e-4 + 0.1 * 3.0,
        ]
    )


def test_inexact_substep_split_raises() -> None:
    """Δτ = Δt/N quantizes to whole microseconds (review round 1, MINOR 4): an
    inexact split would silently run the granule with N·Δτ ≠ Δt — refuse it."""
    solver = _make_solver(cfg=NonhydroConfig(ndyn_substeps=3))
    _stub_stages(solver)
    with pytest.raises(ValueError, match="not divisible"):
        solver(_state(solver), timedelta(seconds=1))  # 1 s / 3 is not whole microseconds
    # the exactly divisible case runs
    solver.hook_log = []
    solver(_state(solver), timedelta(seconds=3))
    assert len([e for e in solver.hook_log if e[0] == "predictor"]) == 3


# -- acceptance 5: standalone first-class component ----------------------------------------


def test_standalone_call_without_federation() -> None:
    """Constructible + callable directly (sympl first-class-component property)."""
    solver = _make_solver()
    _stub_stages(solver)

    # make the (stubbed) dynamics visible at the boundary: the corrector writes nnew
    def corrector(**kwargs: Any) -> None:
        solver._prognostic_states.next.vn.ndarray[...] = 42.0

    solver._solve.run_corrector_step = corrector

    diagnostics, new_state = solver(_state(solver), DT)
    assert diagnostics == {}
    assert set(new_state) == {
        "icon:normal_wind",
        "upward_air_velocity_on_interface_levels",
        "air_density",
        "icon:exner_function",
        "icon:virtual_potential_temperature",
    }
    np.testing.assert_array_equal(new_state["icon:normal_wind"].data, 42.0)
    # untouched prognostics pass through as ingested
    np.testing.assert_array_equal(new_state["air_density"].data, 3.0)


# -- restart / functional state -------------------------------------------------------------


def test_restart_roundtrip_and_functional_schema() -> None:
    solver = _make_solver()
    _stub_stages(solver)
    solver(_state(solver), DT)

    blob = solver.restart_state()
    assert set(blob) == {key for key, _, _ in _RESTART_SCHEMA}
    # both time levels + the velocity-advection carry are present (SPEC S12)
    assert {
        "nnow/vn",
        "nnew/vn",
        "carry/ddt_vn_apc_predictor",
        "carry/ddt_w_adv_corrector",
        "carry/vt",
        "carry/vn_ie",
        "meta/at_initial_timestep",
    } <= set(blob)
    assert float(blob["meta/at_initial_timestep"].data) == 0.0  # one step done

    # mutate, restore, compare bitwise
    reference = {key: np.array(array.data, copy=True) for key, array in blob.items()}
    solver._prognostic_states.current.vn.ndarray[...] = -1.0
    solver._diag_state.tangential_wind.ndarray[...] = -2.0
    solver.load_restart_state(blob)
    after = solver.restart_state()
    for key, expected in reference.items():
        np.testing.assert_array_equal(np.asarray(after[key].data), expected, err_msg=key)

    # functional_state declares exactly the same schema (F-tier consumption is P6)
    functional = solver.functional_state()
    assert set(functional) == set(blob)
    for key, spec in functional.items():
        assert spec.dims == blob[key].dims, key

    # restart snapshots are decoupled from the live buffers
    blob2 = solver.restart_state()
    solver._prognostic_states.current.vn.ndarray[...] = 7.0
    assert not np.any(np.asarray(blob2["nnow/vn"].data) == 7.0)


def test_load_restart_state_rejects_schema_mismatch() -> None:
    solver = _make_solver()
    blob = solver.restart_state()
    incomplete = dict(blob)
    incomplete.pop("carry/vt")
    with pytest.raises(ValueError, match="carry/vt"):
        solver.load_restart_state(incomplete)
    extra = dict(blob)
    extra["nope"] = blob["carry/vt"]
    with pytest.raises(ValueError, match="nope"):
        solver.load_restart_state(extra)


# -- T1 bindability (deviation 5: visit() compiles as an opaque Stepper op) -----------------


def test_plan_tier_binds_and_runs_the_component() -> None:
    """The S05 plan compiler accepts NonhydroSolver (opaque ``array_call`` op via
    the ``visit`` override) and ``run_step`` executes it (review round 1, MINOR 5).

    Under the plan tier the ``__call__`` zero-fill convenience is bypassed, so the
    bound state must carry the bus slots explicitly (declared in STATUS §2).
    """
    import dataclasses as _dataclasses

    from symcon.core.contracts.checkers import StateSchema
    from symcon.core.plan.bind import ExecutionPlan
    from symcon.core.state.vault import StateVault
    from symcon.core.time import datetime

    solver = _make_solver()
    _stub_stages(solver)

    def corrector(**kwargs: Any) -> None:
        solver._prognostic_states.next.vn.ndarray[...] = 42.0

    solver._solve.run_corrector_step = corrector

    state = _state(solver, bus={"icon:ddt_vn_phy": 0.0, "icon:ddt_exner_phy": 0.0})
    state["time"] = datetime(2000, 1, 1)
    bind_ctx = _dataclasses.replace(solver.ctx, tier="plan", timestep=DT)
    vault = StateVault.from_state(state)
    plan = ExecutionPlan.bind(solver, StateSchema.from_state(state), bind_ctx)
    plan.run_step(vault, 0)

    facade = vault.facade()
    np.testing.assert_array_equal(np.asarray(facade["icon:normal_wind"].data), 42.0)
