"""S13: ``HorizontalDiffusion`` contracts on a stubbed granule (no data needed).

The component is constructed **for real** (icon4py ``Diffusion`` on the icon4py
``SimpleGrid`` with a zero static state — construction wires programs and the
ctor-time Smagorinsky profile but computes nothing else); the granule's ``run`` body
is then monkeypatched with a recorder, so these tests exercise exactly the ICON-sc
hosting layer: config/namelist contracts, static-state consumption lists, boundary
ingest/egress around the in-place granule, the explicit initial-stabilization entry,
restart/functional-state plumbing, and T1 bindability. Running the *real* granule
against serialized data is ``test_diffusion_datatest.py``.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta
from typing import Any

import numpy as np
import pytest
import xarray as xr

from icon_sc.core.context import ComputeContext
from icon_sc.core.state import canonical_units, make_dataarray
from icon_sc.icon.components import DiffusionConfig, HorizontalDiffusion, icon_namelist_origins
from icon_sc.icon.components.diffusion import (
    _RESTART_SCHEMA,
    STATIC_FIELDS,
    STATIC_INTERPOLATION_FIELDS,
    STATIC_METRIC_FIELDS,
)
from icon_sc.icon.grid import SLEVEConfig, VerticalGrid
from icon_sc.icon.grid.interpolation import INTERPOLATION_FIELDS
from icon_sc.icon.grid.metrics import METRICS_FIELDS

pytest.importorskip("icon4py.model.atmosphere.diffusion", reason="icon4py diffusion not installed")

NLEV = 10
DT = timedelta(seconds=300.0)

#: ICON-sc dims of every consumed static field (SimpleGrid sparse sizes below).
_STATIC_TABLE: dict[str, tuple[tuple[str, ...], Any]] = {
    "icon:theta_ref_mc": (("cell", "height"), float),
    "icon:wgtfac_c": (("cell", "height_interface"), float),
    "icon:zd_vertoffset": (("cell", "c2e2c", "height"), np.int32),
    "icon:zd_diffcoef": (("cell", "height"), float),
    "icon:zd_intcoef": (("cell", "c2e2c", "height"), float),
    "icon:e_bln_c_s": (("cell", "c2e"), float),
    "icon:rbf_vec_coeff_v1": (("vertex", "v2e"), float),
    "icon:rbf_vec_coeff_v2": (("vertex", "v2e"), float),
    "icon:geofac_div": (("cell", "c2e"), float),
    "icon:geofac_n2s": (("cell", "c2e2co"), float),
    "icon:geofac_grg_x": (("cell", "c2e2co"), float),
    "icon:geofac_grg_y": (("cell", "c2e2co"), float),
    "icon:nudgecoeff_e": (("edge",), float),
}


def _zero_static(grid: Any) -> dict[str, xr.DataArray]:
    sizes = {
        "cell": grid.num_cells,
        "edge": grid.num_edges,
        "vertex": grid.num_vertices,
        "height": NLEV,
        "height_interface": NLEV + 1,
        "c2e": 3,
        "c2e2c": 3,
        "c2e2co": 4,
        "v2e": 6,
    }
    return {
        name: xr.DataArray(
            np.zeros(tuple(sizes[d] for d in dims), dtype=dtype), dims=dims, name=name
        )
        for name, (dims, dtype) in _STATIC_TABLE.items()
    }


def _stub_geometry(grid: Any) -> tuple[Any, Any]:
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
    return cell_params, edge_params


def _make_diffusion(**kwargs: Any) -> HorizontalDiffusion:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    # a damping height below the default model top so the ctor-time
    # init_nabla2_factor_in_upper_damping_zone domain is non-degenerate at NLEV=10.
    vgrid = VerticalGrid.from_config(SLEVEConfig(num_levels=NLEV, rayleigh_damping_height=12000.0))
    cell_params, edge_params = _stub_geometry(i4_grid)
    cfg = kwargs.pop("cfg", DiffusionConfig())
    static = kwargs.pop("static", _zero_static(i4_grid))
    # gtfn_cpu, not embedded: the granule cannot even be *constructed* on the
    # embedded backend at the pinned versions (its ctor-time init programs use
    # concat_where — upstream xfails every diffusion datatest on embedded with
    # "Embedded backend does not support concat_where", filters.py v0.2.0).
    return HorizontalDiffusion(
        i4_grid,
        vgrid,
        static,
        cfg,
        ComputeContext(backend="gtfn_cpu"),
        cell_geometry=cell_params,
        edge_geometry=edge_params,
        **kwargs,
    )


def _stub_run(component: HorizontalDiffusion) -> list[dict[str, Any]]:
    """Replace the granule ``run`` with a recorder that shifts vn in place."""
    calls: list[dict[str, Any]] = []

    def run(
        *, diagnostic_state: Any, prognostic_state: Any, dtime: float, initial_run: bool = False
    ) -> None:
        calls.append({"dtime": dtime, "initial_run": initial_run})
        prognostic_state.vn.ndarray[...] += 1.0
        diagnostic_state.div_ic.ndarray[...] += 0.5

    component._diffusion.run = run
    return calls


def _state(component: HorizontalDiffusion) -> dict[str, Any]:
    grid = component._i4_grid
    n_cells, n_edges = grid.num_cells, grid.num_edges
    shapes = {
        "icon:normal_wind": (("edge", "height"), (n_edges, NLEV)),
        "upward_air_velocity_on_interface_levels": (
            ("cell", "height_interface"),
            (n_cells, NLEV + 1),
        ),
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
    return state


# -- configuration contracts ---------------------------------------------------------------


def test_config_carries_icon_namelist_origins() -> None:
    cfg = DiffusionConfig()
    origins = icon_namelist_origins(cfg)
    assert set(origins) == {f.name for f in dataclasses.fields(cfg)}
    assert origins["hdiff_efdt_ratio"] == "diffusion_nml:hdiff_efdt_ratio"
    assert origins["zdiffu_t"] == "nonhydrostatic_nml:l_zdiffu_t"
    assert origins["shear_type"] == "turbdiff_nml:itype_sher"


def test_config_defaults_match_icon4py() -> None:
    """Field-by-field equality with icon4py's DiffusionConfig defaults (v0.2.0)."""
    from icon4py.model.atmosphere.diffusion import diffusion as i4_diffusion

    ours = DiffusionConfig().to_icon4py()
    theirs = i4_diffusion.DiffusionConfig()
    for attr in (
        "diffusion_type",
        "apply_to_vertical_wind",
        "apply_to_horizontal_wind",
        "apply_to_temperature",
        "apply_smag_diff_to_vertical_wind",
        "compute_3d_smag_coeff",
        "type_vn_diffu",
        "type_t_diffu",
        "hdiff_efdt_ratio",
        "hdiff_w_efdt_ratio",
        "smagorinski_scaling_factor",
        "smagorinski_scaling_factor2",
        "smagorinski_scaling_factor3",
        "smagorinski_scaling_factor4",
        "smagorinski_scaling_height",
        "smagorinski_scaling_height2",
        "smagorinski_scaling_height3",
        "smagorinski_scaling_height4",
        "ndyn_substeps",
        "apply_zdiffusion_t",
        "velocity_boundary_diffusion_denominator",
        "temperature_boundary_diffusion_denominator",
        "max_nudging_coefficient",
        "shear_type",
        "iforcing",
        "a_hshr",
        "loutshs",
    ):
        assert getattr(ours, attr) == getattr(theirs, attr), attr


def test_config_roundtrip_from_icon4py() -> None:
    cfg = DiffusionConfig(hdiff_efdt_ratio=10.0, hdiff_temp=False, ndyn_substeps=2)
    assert DiffusionConfig.from_icon4py(cfg.to_icon4py()) == cfg


def test_config_rejects_unsupported_slice() -> None:
    """The granule's own validation runs at component construction (via to_icon4py)."""
    with pytest.raises(NotImplementedError):
        DiffusionConfig(diffusion_type=4).to_icon4py()
    with pytest.raises(NotImplementedError):
        DiffusionConfig(hdiff_smag_w=True).to_icon4py()
    with pytest.raises(NotImplementedError):
        DiffusionConfig(smag_3d=True).to_icon4py()
    with pytest.raises(NotImplementedError):
        DiffusionConfig(shear_type=3).to_icon4py()


# -- static-state consumption lists (the S11 coordination point) -----------------------------


def test_static_lists_cover_the_donor_dataclasses_exactly() -> None:
    from icon4py.model.atmosphere.diffusion import diffusion_states

    assert set(STATIC_METRIC_FIELDS) == {
        f.name for f in dataclasses.fields(diffusion_states.DiffusionMetricState)
    }
    assert set(STATIC_INTERPOLATION_FIELDS) == {
        f.name for f in dataclasses.fields(diffusion_states.DiffusionInterpolationState)
    }


def test_every_static_name_is_produced_by_the_s11_factories() -> None:
    produced = set(METRICS_FIELDS) | set(INTERPOLATION_FIELDS)
    for name in STATIC_FIELDS:
        assert name in produced, name


def test_missing_static_raises() -> None:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    static = _zero_static(i4_grid)
    static.pop("icon:zd_intcoef")
    with pytest.raises(ValueError, match="zd_intcoef"):
        _make_diffusion(static=static)


def test_raw_grid_requires_explicit_geometry() -> None:
    from icon4py.model.common.grid import simple

    i4_grid = simple.simple_grid(num_levels=NLEV)
    vgrid = VerticalGrid.from_config(SLEVEConfig(num_levels=NLEV))
    with pytest.raises(ValueError, match="edge_geometry"):
        HorizontalDiffusion(
            i4_grid,
            vgrid,
            _zero_static(i4_grid),
            DiffusionConfig(),
            ComputeContext(backend="gtfn_cpu"),
        )


# -- the call path ----------------------------------------------------------------------------


def test_standalone_call_ingests_and_egresses_around_the_granule() -> None:
    """One __call__ = one granule run over the full Δt; in-place mutation is
    egressed to the declared outputs; the caller's input buffers stay untouched."""
    component = _make_diffusion()
    calls = _stub_run(component)

    state = _state(component)
    before = {name: np.array(field.data) for name, field in state.items()}
    diagnostics, new_state = component(state, DT)

    assert calls == [{"dtime": DT.total_seconds(), "initial_run": False}]
    assert diagnostics == {}
    assert set(new_state) == set(component.output_properties)
    np.testing.assert_array_equal(
        np.asarray(new_state["icon:normal_wind"].data),
        before["icon:normal_wind"] + 1.0,
    )
    for name in (
        "upward_air_velocity_on_interface_levels",
        "icon:exner_function",
        "icon:virtual_potential_temperature",
    ):
        np.testing.assert_array_equal(np.asarray(new_state[name].data), before[name])
    for name, field in state.items():  # inputs not mutated
        np.testing.assert_array_equal(np.asarray(field.data), before[name])


def test_initial_stabilization_is_explicit_and_one_shot() -> None:
    """ICON's extra pre-timeloop call maps to initial_stabilization(); ordinary
    calls never pass initial_run=True (the driver's apply_initial_stabilization
    contract, REFERENCES.lock icon4py-driver-jw)."""
    component = _make_diffusion()
    calls = _stub_run(component)

    state = _state(component)
    _, stabilized = component.initial_stabilization(state, DT)
    component(state, DT)

    assert [c["initial_run"] for c in calls] == [True, False]
    assert set(stabilized) == set(component.output_properties)


def test_initial_stabilization_flag_resets_on_error() -> None:
    component = _make_diffusion()

    def boom(**kwargs: Any) -> None:
        raise RuntimeError("granule failure")

    component._diffusion.run = boom
    with pytest.raises(RuntimeError, match="granule failure"):
        component.initial_stabilization(_state(component), DT)
    calls = _stub_run(component)
    component(_state(component), DT)
    assert calls[-1]["initial_run"] is False


# -- restart / functional state ----------------------------------------------------------------


def test_restart_roundtrip_and_strict_schema() -> None:
    component = _make_diffusion()
    component._diag_state.hdef_ic.ndarray[...] = 3.5
    component._diag_state.dwdy.ndarray[...] = -1.25
    component._steps_done = 7

    blob = component.restart_state()
    assert set(blob) == {key for key, _, _ in _RESTART_SCHEMA}
    np.testing.assert_array_equal(np.asarray(blob["carry/hdef_ic"].data), 3.5)

    other = _make_diffusion()
    other.load_restart_state(blob)
    np.testing.assert_array_equal(np.asarray(other._diag_state.hdef_ic.ndarray), 3.5)
    np.testing.assert_array_equal(np.asarray(other._diag_state.dwdy.ndarray), -1.25)
    assert other._steps_done == 7

    incomplete = dict(blob)
    incomplete.pop("carry/div_ic")
    with pytest.raises(ValueError, match="carry/div_ic"):
        other.load_restart_state(incomplete)
    extra = dict(blob)
    extra["carry/bogus"] = blob["carry/div_ic"]
    with pytest.raises(ValueError, match="bogus"):
        other.load_restart_state(extra)


def test_functional_state_declares_the_restart_schema() -> None:
    component = _make_diffusion()
    specs = component.functional_state()
    assert set(specs) == {key for key, _, _ in _RESTART_SCHEMA}
    assert specs["carry/hdef_ic"].dims == ("cell", "height_interface")
    assert specs["carry/hdef_ic"].units == "s-2"


# -- T1 bindability -----------------------------------------------------------------------------


def test_plan_tier_binds_and_runs_the_component() -> None:
    """The S05 plan compiler accepts HorizontalDiffusion as an opaque Stepper op."""
    import dataclasses as _dataclasses

    from icon_sc.core.contracts.checkers import StateSchema
    from icon_sc.core.plan.bind import ExecutionPlan
    from icon_sc.core.state.vault import StateVault
    from icon_sc.core.time import datetime

    component = _make_diffusion()
    _stub_run(component)

    state = _state(component)
    state["time"] = datetime(2000, 1, 1)
    bind_ctx = _dataclasses.replace(component.ctx, tier="plan", timestep=DT)
    vault = StateVault.from_state(state)
    plan = ExecutionPlan.bind(component, StateSchema.from_state(state), bind_ctx)
    plan.run_step(vault, 0)

    facade = vault.facade()
    np.testing.assert_array_equal(
        np.asarray(facade["icon:normal_wind"].data),
        np.full_like(np.asarray(facade["icon:normal_wind"].data), 2.0),
    )
