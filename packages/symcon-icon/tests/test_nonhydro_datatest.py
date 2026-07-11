"""S12 acceptance 1/3/4 (marker ``data``): ``NonhydroSolver`` savepoint parity.

icon4py's solve_nonhydro integration tests rerun through the symcon component:
experiment EXCLAIM_APE (``exclaim_ape_R02B04``, the archive already used by S11 —
solve-nonhydro savepoints at the first timestep 2000-01-01T00:00:02.000, ``linit``,
and the mid-run timestep 00:00:04.000, at substeps 1..2 of the archive's
``ndyn_substeps=2``). States are built from the savepoints exactly as icon4py's own
tests build them (REFERENCES.lock ``icon4py-solve-nonhydro-tests``): the static
state from the metrics/interpolation savepoints (ready icon4py fields — zero
conversion), the private carry loaded through the component's restart protocol, the
prognostics + bus slots through the public boundary state.

Tolerances are icon4py's own, cited per field from
``model/atmosphere/dycore/tests/dycore/integration_tests/test_solve_nonhydro.py``
at v0.2.0 (dallclose defaults ``rtol=1e-12, atol=0`` unless stated). Deviations
(documented in STATUS.md):

- the multi-substep tolerances come from upstream ``test_run_solve_nonhydro_multi_step``,
  which upstream runs for MCH_CH_R04B09 only — reused verbatim on EXCLAIM_APE;
- no ``embedded`` leg: upstream **xfails** every solve_nonhydro integration test on
  the embedded backend ("Embedded backend currently fails in remap function",
  ``icon4py.model.testing.filters``), so parity runs on gtfn_cpu (+ gpu-marked
  gtfn_gpu, which skips cleanly without a CUDA device).

First run compiles the dycore gt4py programs (persistent cache under
``~/.cache/symcon/gt4py``); the EXCLAIM_APE archive is the S11 one (~4.0 GB
compressed, cached under ``~/.cache/symcon/icon4py-testdata`` — no new downloads).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from symcon.core import ComputeContext
from symcon.core.ingress.gt4py import make_backend
from symcon.core.state import canonical_units, make_dataarray
from symcon.core.testing import assert_allclose
from symcon.icon.components import NonhydroConfig, NonhydroSolver
from symcon.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    from icon4py.model.testing import definitions as icon4py_definitions

    # Re-exported icon4py fixtures (fixture *names* are what pytest resolves; the
    # bridge sets the cache path before icon4py.model.testing reads the env).
    from icon4py.model.testing.fixtures import icon_grid  # noqa: F401
    from icon4py.model.testing.fixtures.datatest import (  # noqa: F401
        interpolation_savepoint,
        metrics_savepoint,
    )

    from symcon.icon.testing import (  # noqa: F401
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        process_props,
    )

    @pytest.fixture(params=[icon4py_definitions.Experiments.EXCLAIM_APE], ids=lambda e: e.name)
    def experiment_description(request: Any) -> Any:
        """Override the bridge default (GAUSS3D): the APE archive has the savepoints."""
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
]

#: The two dates the archive provides: model start (linit) and mid-run (SPEC: "the
#: first and a mid-run timestep").
DATE_FIRST = "2000-01-01T00:00:02.000"
DATE_MID = "2000-01-01T00:00:04.000"

#: Parity backends (see module docstring for the missing embedded leg).
BACKENDS = ["gtfn_cpu", pytest.param("gtfn_gpu", marks=pytest.mark.gpu)]

_PROGNOSTICS = (
    ("icon:normal_wind", "vn", ("edge", "height")),
    ("upward_air_velocity_on_interface_levels", "w", ("cell", "height_interface")),
    ("air_density", "rho", ("cell", "height")),
    ("icon:exner_function", "exner", ("cell", "height")),
    ("icon:virtual_potential_temperature", "theta_v", ("cell", "height")),
)


def _host(buffer: Any) -> np.ndarray:
    return buffer.get() if hasattr(buffer, "get") else np.asarray(buffer)


def _static_from_savepoints(
    metrics_savepoint: Any, interpolation_savepoint: Any, grid_savepoint: Any
) -> dict[str, Any]:
    """The S12 static state as ready icon4py fields, exactly as icon4py's own tests
    build ``MetricStateNonHydro``/``InterpolationState`` (dycore tests ``utils.py``)."""
    m, i = metrics_savepoint, interpolation_savepoint
    grg = i.geofac_grg()
    return {
        "icon:mask_prog_halo_c": m.mask_prog_halo_c(),
        "icon:rayleigh_w": m.rayleigh_w(),
        "icon:exner_exfac": m.exner_exfac(),
        "icon:exner_ref_mc": m.exner_ref_mc(),
        "icon:wgtfac_c": m.wgtfac_c(),
        "icon:wgtfacq_c": m.wgtfacq_c(),
        "icon:inv_ddqz_z_full": m.inv_ddqz_z_full(),
        "icon:rho_ref_mc": m.rho_ref_mc(),
        "icon:theta_ref_mc": m.theta_ref_mc(),
        "icon:vwind_expl_wgt": m.vwind_expl_wgt(),
        "icon:d_exner_dz_ref_ic": m.d_exner_dz_ref_ic(),
        "icon:ddqz_z_half": m.ddqz_z_half(),
        "icon:theta_ref_ic": m.theta_ref_ic(),
        "icon:d2dexdz2_fac1_mc": m.d2dexdz2_fac1_mc(),
        "icon:d2dexdz2_fac2_mc": m.d2dexdz2_fac2_mc(),
        "icon:rho_ref_me": m.rho_ref_me(),
        "icon:theta_ref_me": m.theta_ref_me(),
        "icon:ddxn_z_full": m.ddxn_z_full(),
        "icon:zdiff_gradp": m.zdiff_gradp(),
        "icon:vertoffset_gradp": m.vertoffset_gradp(),
        "icon:nflat_gradp": int(grid_savepoint.nflat_gradp()),
        "icon:pg_exdist": m.pg_exdist_dsl(),
        "icon:ddqz_z_full_e": m.ddqz_z_full_e(),
        "icon:ddxt_z_full": m.ddxt_z_full(),
        "icon:wgtfac_e": m.wgtfac_e(),
        "icon:wgtfacq_e": m.wgtfacq_e(),
        "icon:vwind_impl_wgt": m.vwind_impl_wgt(),
        "icon:hmask_dd3d": m.hmask_dd3d(),
        "icon:scalfac_dd3d": m.scalfac_dd3d(),
        "icon:coeff1_dwdz": m.coeff1_dwdz(),
        "icon:coeff2_dwdz": m.coeff2_dwdz(),
        "icon:coeff_gradekin": m.coeff_gradekin(),
        "icon:c_lin_e": i.c_lin_e(),
        "icon:c_intp": i.c_intp(),
        "icon:e_flx_avg": i.e_flx_avg(),
        "icon:geofac_grdiv": i.geofac_grdiv(),
        "icon:geofac_rot": i.geofac_rot(),
        "icon:pos_on_tplane_e_x": i.pos_on_tplane_e_x(),
        "icon:pos_on_tplane_e_y": i.pos_on_tplane_e_y(),
        "icon:rbf_vec_coeff_e": i.rbf_vec_coeff_e(),
        "icon:e_bln_c_s": i.e_bln_c_s(),
        "icon:rbf_vec_coeff_v1": i.rbf_vec_coeff_v1(),
        "icon:rbf_vec_coeff_v2": i.rbf_vec_coeff_v2(),
        "icon:geofac_div": i.geofac_div(),
        "icon:geofac_n2s": i.geofac_n2s(),
        "icon:geofac_grg_x": grg[0],
        "icon:geofac_grg_y": grg[1],
        "icon:nudgecoeff_e": i.nudgecoeff_e(),
    }


def _make_solver(
    *,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
    sp_init: Any,
    symcon_backend: str,
) -> NonhydroSolver:
    """Component construction mirroring icon4py's own solve_nonhydro test setup."""
    from icon4py.model.common.grid import vertical as v_grid

    n_substeps = int(experiment.config.diffusion.ndyn_substeps)
    # PLAN pitfall: the substep ratio is fixed by the data's provenance — assert it.
    assert n_substeps == 2, "EXCLAIM_APE archive was generated with ndyn_substeps=2"
    config = NonhydroConfig.from_icon4py(
        experiment.config.nonhydrostatic,
        ndyn_substeps=n_substeps,
        second_order_divdamp_factor=float(sp_init.divdamp_fac_o2()),
        prepare_advection=bool(sp_init.get_metadata("prep_adv").get("prep_adv")),
    )
    vertical_params = v_grid.VerticalGrid(
        config=experiment.config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )
    ctx = ComputeContext(backend=make_backend(symcon_backend))
    return NonhydroSolver(
        icon_grid,
        vertical_params,
        _static_from_savepoints(metrics_savepoint, interpolation_savepoint, grid_savepoint),
        config,
        ctx,
        edge_geometry=grid_savepoint.construct_edge_geometry(),
        cell_geometry=grid_savepoint.construct_cell_geometry(),
        owner_mask=grid_savepoint.c_owner_mask(),
    )


def _load_carry(
    solver: NonhydroSolver, sp_init: Any, *, at_initial: bool, swap_w_pair: bool
) -> None:
    """The private carry from the init savepoint, through the restart protocol.

    Mirrors icon4py's ``utils.construct_diagnostics`` / ``create_prognostic_states``:
    the advective-tendency pairs load in savepoint order, except ``swap_w_pair``
    (upstream ``swap_vertical_wind_advective_tendency=not linit`` in the multi-step
    test) which loads the vertical pair reversed so the component's internal
    first-substep swap reproduces upstream's.
    """
    carry = solver.restart_state()

    def put(key: str, value: Any) -> None:
        carry[key].data[...] = np.asarray(value.asnumpy() if hasattr(value, "asnumpy") else value)

    put("nnow/vn", sp_init.vn_now())
    put("nnow/w", sp_init.w_now())
    put("nnow/rho", sp_init.rho_now())
    put("nnow/exner", sp_init.exner_now())
    put("nnow/theta_v", sp_init.theta_v_now())
    put("nnew/vn", sp_init.vn_new())
    put("nnew/w", sp_init.w_new())
    put("nnew/rho", sp_init.rho_new())
    put("nnew/exner", sp_init.exner_new())
    put("nnew/theta_v", sp_init.theta_v_new())
    put("carry/ddt_vn_apc_predictor", sp_init.ddt_vn_apc_pc(0))
    put("carry/ddt_vn_apc_corrector", sp_init.ddt_vn_apc_pc(1))
    w_pred, w_corr = (1, 0) if swap_w_pair else (0, 1)
    put("carry/ddt_w_adv_predictor", sp_init.ddt_w_adv_pc(w_pred))
    put("carry/ddt_w_adv_corrector", sp_init.ddt_w_adv_pc(w_corr))
    put("carry/vt", sp_init.vt())
    put("carry/vn_ie", sp_init.vn_ie())
    put("carry/w_concorr_c", sp_init.w_concorr_c())
    put("carry/theta_v_ic", sp_init.theta_v_ic())
    put("carry/rho_ic", sp_init.rho_ic())
    put("carry/exner_pr", sp_init.exner_pr())
    put("carry/mass_fl_e", sp_init.mass_fl_e())
    put("carry/exner_dyn_incr", sp_init.exner_dyn_incr())
    carry["carry/max_vertical_cfl"].data[...] = 0.0
    put("prep_adv/vn_traj", sp_init.vn_traj())
    put("prep_adv/mass_flx_me", sp_init.mass_flx_me())
    put("prep_adv/mass_flx_ic", sp_init.mass_flx_ic())
    carry["prep_adv/vol_flx_ic"].data[...] = 0.0
    put("z/gradh_exner", sp_init.z_gradh_exner())
    put("z/rho_e", sp_init.z_rho_e())
    put("z/theta_v_e", sp_init.z_theta_v_e())
    put("z/kin_hor_e", sp_init.z_kin_hor_e())
    put("z/vt_ie", sp_init.z_vt_ie())
    put("z/graddiv_vn", sp_init.z_graddiv_vn())
    put("z/dwdz_dd", sp_init.z_dwdz_dd())
    carry["meta/at_initial_timestep"].data[...] = float(at_initial)
    carry["meta/steps_done"].data[...] = 0.0
    solver.load_restart_state(carry)


def _upload(ctx: ComputeContext, name: str, host: np.ndarray, dims: tuple[str, ...]) -> Any:
    buffer: Any = ctx.require_allocator.empty(host.shape, host.dtype)
    buffer[...] = host
    return make_dataarray(
        buffer,
        name=name,
        dims=dims,
        units=canonical_units(name),
        location="edge" if dims[0] == "edge" else "cell",
    )


def _state_from_savepoint(sp_init: Any, ctx: ComputeContext, *, bus: bool = True) -> dict[str, Any]:
    """The boundary state (prognostics + bus slots) from the init savepoint."""
    state: dict[str, Any] = {}
    for name, accessor, dims in _PROGNOSTICS:
        host = np.ascontiguousarray(getattr(sp_init, f"{accessor}_now")().asnumpy(), np.float64)
        state[name] = _upload(ctx, name, host, dims)
    if bus:
        for name, accessor, dims in (
            ("icon:ddt_vn_phy", "ddt_vn_phy", ("edge", "height")),
            ("icon:ddt_exner_phy", "ddt_exner_phy", ("cell", "height")),
        ):
            host = np.ascontiguousarray(getattr(sp_init, accessor)().asnumpy(), np.float64)
            state[name] = _upload(ctx, name, host, dims)
    return state


def _record_velocity_advection(solver: NonhydroSolver) -> list[tuple[Any, ...]]:
    """Wrap the hosted VelocityAdvection with an invocation recorder."""
    velocity_advection = solver._solve.velocity_advection
    calls: list[tuple[Any, ...]] = []
    original_predictor = velocity_advection.run_predictor_step
    original_corrector = velocity_advection.run_corrector_step

    def predictor(**kwargs: Any) -> Any:
        calls.append(("predictor", kwargs["skip_compute_predictor_vertical_advection"]))
        return original_predictor(**kwargs)

    def corrector(**kwargs: Any) -> Any:
        calls.append(("corrector",))
        return original_corrector(**kwargs)

    velocity_advection.run_predictor_step = predictor
    velocity_advection.run_corrector_step = corrector
    return calls


# -- data provenance ------------------------------------------------------------------------


def test_time_step_flags_and_provenance(data_provider: Any, experiment: Any) -> None:
    """icon4py's ``test_time_step_flags`` semantics hold on the APE archive; the
    archive's namelist fixes ndyn_substeps=2 (the config the parity tests assert)."""
    assert int(experiment.config.diffusion.ndyn_substeps) == 2
    assert int(experiment.config.nonhydrostatic.itime_scheme) == 4
    for date, expected_linit in ((DATE_FIRST, True), (DATE_MID, False)):
        for substep in (1, 2):
            sp = data_provider.from_savepoint_nonhydro_init(istep=1, date=date, substep=substep)
            assert sp.get_metadata("recompute").get("recompute") == (substep == 1)
            assert sp.get_metadata("clean_mflx").get("clean_mflx") == (substep == 1)
            assert sp.get_metadata("linit").get("linit") == (expected_linit and substep == 1)


# -- acceptance 1: savepoint parity -----------------------------------------------------------


@pytest.mark.parametrize("symcon_backend", BACKENDS)
@pytest.mark.parametrize(
    "step_date, at_initial", [(DATE_FIRST, True), (DATE_MID, False)], ids=["first", "mid-run"]
)
def test_full_timestep_multi_substep_parity(
    symcon_backend: str,
    step_date: str,
    at_initial: bool,
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """One public ``__call__`` = ndyn_substeps=2 substeps vs the substep-2 exit
    savepoints — upstream ``test_run_solve_nonhydro_multi_step`` through the
    component boundary (tolerances cited per field below; upstream runs this test
    for MCH_CH_R04B09 — the tolerances are reused on EXCLAIM_APE, see STATUS)."""
    if symcon_backend == "gtfn_gpu":
        pytest.importorskip("cupy")
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=1, date=step_date, substep=1)
    sp_exit = data_provider.from_savepoint_nonhydro_exit(istep=2, date=step_date, substep=2)
    sp_final = data_provider.from_savepoint_nonhydro_step_final(date=step_date, substep=2)
    assert bool(sp_init.get_metadata("linit").get("linit")) == at_initial
    dt_substep = float(sp_init.get_metadata("dtime").get("dtime"))

    solver = _make_solver(
        experiment=experiment,
        grid_savepoint=grid_savepoint,
        metrics_savepoint=metrics_savepoint,
        interpolation_savepoint=interpolation_savepoint,
        icon_grid=icon_grid,
        sp_init=sp_init,
        symcon_backend=symcon_backend,
    )
    _load_carry(solver, sp_init, at_initial=at_initial, swap_w_pair=not at_initial)
    velocity_advection_calls = _record_velocity_advection(solver)

    state = _state_from_savepoint(sp_init, solver.ctx)
    _, new_state = solver(state, timedelta(seconds=dt_substep * 2))

    # acceptance 2, data-verified half: velocity-advection reuse per icon4py's flags —
    # the predictor advection runs only at the first substep (vertical advection
    # skipped unless this is the very first substep of the run), the corrector's every
    # substep (solve_nonhydro.py run_predictor_step/run_corrector_step at v0.2.0).
    assert velocity_advection_calls == [
        ("predictor", not at_initial),
        ("corrector",),
        ("corrector",),
    ]

    # test_run_solve_nonhydro_multi_step, savepoint_nonhydro_exit(istep=2, substep=2):
    checks = (
        # vn: atol=5e-13 (upstream l.943-946)
        ("icon:normal_wind", sp_exit.vn_new(), dict(atol=5e-13)),
        # w: atol=1e-13 (l.936-940)
        ("upward_air_velocity_on_interface_levels", sp_exit.w_new(), dict(atol=1e-13)),
        # rho: dallclose defaults (l.926-929)
        ("air_density", sp_exit.rho_new(), dict()),
        # exner, theta_v: vs savepoint_nonhydro_step_final, dallclose defaults
        # (l.921-924, l.931-934)
        ("icon:exner_function", sp_final.exner_new(), dict()),
        ("icon:virtual_potential_temperature", sp_final.theta_v_new(), dict()),
    )
    for name, reference, tols in checks:
        assert_allclose(
            _host(new_state[name].data),
            reference.asnumpy(),
            rtol=tols.get("rtol", 1e-12),
            atol=tols.get("atol", 0.0),
            names=(f"symcon {name}", "icon4py solve-nonhydro exit"),
            equal_nan=False,
        )

    restart = solver.restart_state()
    carry_checks = (
        # rho_ic, theta_v_ic: dallclose defaults (l.893-901)
        ("carry/rho_ic", sp_exit.rho_ic(), dict()),
        ("carry/theta_v_ic", sp_exit.theta_v_ic(), dict()),
        # mass_fl_e: atol=5e-7 (l.903-907)
        ("carry/mass_fl_e", sp_exit.mass_fl_e(), dict(atol=5e-7)),
        # mass_flx_me: atol=5e-7, vn_traj: atol=1e-12 (l.909-919)
        ("prep_adv/mass_flx_me", sp_exit.mass_flx_me(), dict(atol=5e-7)),
        ("prep_adv/vn_traj", sp_exit.vn_traj(), dict(atol=1e-12)),
        # exner_dyn_incr: atol=1e-14 (l.947-951)
        ("carry/exner_dyn_incr", sp_exit.exner_dyn_incr(), dict(atol=1e-14)),
    )
    for key, reference, tols in carry_checks:
        assert_allclose(
            np.asarray(restart[key].data),
            reference.asnumpy(),
            rtol=tols.get("rtol", 1e-12),
            atol=tols.get("atol", 0.0),
            names=(f"symcon {key}", "icon4py solve-nonhydro exit"),
            equal_nan=False,
        )


@pytest.mark.parametrize("symcon_backend", BACKENDS)
def test_single_substep_parity(
    symcon_backend: str,
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """One substep (predictor+corrector) vs the substep-1 exit savepoints — upstream
    ``test_run_solve_nonhydro_single_step`` (EXCLAIM_APE leg: istep 1→2, substep 1,
    at_initial) driven through the frozen substep hooks with ndyn_substeps_var=2."""
    if symcon_backend == "gtfn_gpu":
        pytest.importorskip("cupy")
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=1, date=DATE_FIRST, substep=1)
    sp_exit = data_provider.from_savepoint_nonhydro_exit(istep=2, date=DATE_FIRST, substep=1)
    sp_final = data_provider.from_savepoint_nonhydro_step_final(date=DATE_FIRST, substep=1)
    dt_substep = float(sp_init.get_metadata("dtime").get("dtime"))

    solver = _make_solver(
        experiment=experiment,
        grid_savepoint=grid_savepoint,
        metrics_savepoint=metrics_savepoint,
        interpolation_savepoint=interpolation_savepoint,
        icon_grid=icon_grid,
        sp_init=sp_init,
        symcon_backend=symcon_backend,
    )
    _load_carry(solver, sp_init, at_initial=True, swap_w_pair=False)
    solver._load_bus(
        {
            "icon:ddt_vn_phy": sp_init.ddt_vn_phy().asnumpy(),
            "icon:ddt_exner_phy": sp_init.ddt_exner_phy().asnumpy(),
        }
    )
    # upstream passes ndyn_substeps_var=2 and drives the first substep only
    # (at_first_substep=True, at_last_substep = 1 == 2 -> False):
    solver._current_call_substeps = 2
    dt = timedelta(seconds=dt_substep)
    solver.substep_array_call(0, 0, {}, {}, dt)
    solver.substep_array_call(1, 0, {}, {}, dt)

    restart = solver.restart_state()
    checks = (
        # test_run_solve_nonhydro_single_step: vn rtol=1e-12, atol=1e-13 (l.760-765)
        ("nnew/vn", sp_exit.vn_new(), dict(rtol=1e-12, atol=1e-13)),
        # w: atol=8e-14 (l.771-775)
        ("nnew/w", sp_exit.w_new(), dict(atol=8e-14)),
        # rho: dallclose defaults (l.767-769)
        ("nnew/rho", sp_exit.rho_new(), dict()),
        # theta_v, exner vs step_final: dallclose defaults (l.751-758)
        ("nnew/theta_v", sp_final.theta_v_new(), dict()),
        ("nnew/exner", sp_final.exner_new(), dict()),
        # exner_dyn_incr: atol=1e-14 (l.777-781)
        ("carry/exner_dyn_incr", sp_exit.exner_dyn_incr(), dict(atol=1e-14)),
    )
    for key, reference, tols in checks:
        assert_allclose(
            np.asarray(restart[key].data),
            reference.asnumpy(),
            rtol=tols.get("rtol", 1e-12),
            atol=tols.get("atol", 0.0),
            names=(f"symcon {key}", "icon4py solve-nonhydro exit"),
            equal_nan=False,
        )


def test_predictor_stage_parity(
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """The predictor stage hook vs the istep=1 exit savepoint — upstream
    ``test_nonhydro_predictor_step`` (EXCLAIM_APE leg), on the fields the component
    exposes at its boundary/restart surface (gtfn_cpu; internal z_* locals of the
    granule that symcon does not persist are covered upstream)."""
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=1, date=DATE_FIRST, substep=1)
    sp_exit = data_provider.from_savepoint_nonhydro_exit(istep=1, date=DATE_FIRST, substep=1)

    solver = _make_solver(
        experiment=experiment,
        grid_savepoint=grid_savepoint,
        metrics_savepoint=metrics_savepoint,
        interpolation_savepoint=interpolation_savepoint,
        icon_grid=icon_grid,
        sp_init=sp_init,
        symcon_backend="gtfn_cpu",
    )
    _load_carry(solver, sp_init, at_initial=True, swap_w_pair=False)
    solver._load_bus(
        {
            "icon:ddt_vn_phy": sp_init.ddt_vn_phy().asnumpy(),
            "icon:ddt_exner_phy": sp_init.ddt_exner_phy().asnumpy(),
        }
    )
    solver._current_call_substeps = 2
    solver.substep_array_call(
        0, 0, {}, {}, timedelta(seconds=float(sp_init.get_metadata("dtime").get("dtime")))
    )

    restart = solver.restart_state()
    checks = (
        # test_nonhydro_predictor_step (EXCLAIM_APE leg), per-field:
        ("carry/exner_pr", sp_exit.exner_pr(), dict()),  # stencils 2,3 (l.246-251)
        ("carry/rho_ic", sp_exit.rho_ic(), dict()),  # stencils 7-9 (l.284-289)
        ("carry/theta_v_ic", sp_exit.theta_v_ic(), dict()),  # stencil 11 (l.305-310)
        ("z/rho_e", sp_exit.z_rho_e(), dict()),  # rho/theta advection (l.336-341)
        ("z/theta_v_e", sp_exit.z_theta_v_e(), dict()),  # (l.342-347)
        ("z/gradh_exner", sp_exit.z_gradh_exner(), dict(atol=1e-20)),  # 18-22 (l.350)
        ("nnew/vn", sp_exit.vn_new(), dict(atol=6e-15)),  # stencil 24 (l.361-365)
        ("z/graddiv_vn", sp_exit.z_graddiv_vn(), dict(atol=5e-20)),  # stencil 30
        ("carry/vt", sp_exit.vt(), dict(atol=5e-14)),  # stencil 30 (l.387-391)
        ("carry/mass_fl_e", sp_exit.mass_fl_e(), dict(atol=4e-12)),  # stencil 32
        ("carry/vn_ie", sp_exit.vn_ie(), dict(atol=2e-14)),  # stencils 35-38 (l.409)
        ("z/vt_ie", sp_exit.z_vt_ie(), dict(atol=2e-14)),  # (l.416-422)
        ("z/kin_hor_e", sp_exit.z_kin_hor_e(), dict(atol=1e-20)),  # (l.424-430)
        ("carry/w_concorr_c", sp_exit.w_concorr_c(), dict(atol=1e-15)),  # 39,40 (l.441)
        ("nnew/rho", sp_exit.rho_new(), dict()),  # (l.448)
        ("nnew/w", sp_exit.w_new(), dict(atol=7e-14)),  # (l.449-451)
        ("nnew/exner", sp_exit.exner_new(), dict()),  # (l.453-455)
        ("nnew/theta_v", sp_exit.theta_v_new(), dict()),  # (l.456-458)
    )
    for key, reference, tols in checks:
        assert_allclose(
            np.asarray(restart[key].data),
            reference.asnumpy(),
            rtol=tols.get("rtol", 1e-12),
            atol=tols.get("atol", 0.0),
            names=(f"symcon {key}", "icon4py predictor exit"),
            equal_nan=False,
        )


def test_corrector_stage_parity(
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """The corrector stage hook vs the istep=2 exit savepoint — upstream
    ``test_nonhydro_corrector_step`` (EXCLAIM_APE leg: istep_init=2, substep 1),
    with the predictor's intermediates loaded from the istep=2 init savepoint."""
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=2, date=DATE_FIRST, substep=1)
    sp_exit = data_provider.from_savepoint_nonhydro_exit(istep=2, date=DATE_FIRST, substep=1)

    solver = _make_solver(
        experiment=experiment,
        grid_savepoint=grid_savepoint,
        metrics_savepoint=metrics_savepoint,
        interpolation_savepoint=interpolation_savepoint,
        icon_grid=icon_grid,
        sp_init=sp_init,
        symcon_backend="gtfn_cpu",
    )
    _load_carry(solver, sp_init, at_initial=True, swap_w_pair=False)
    solver._load_bus(
        {
            "icon:ddt_vn_phy": sp_init.ddt_vn_phy().asnumpy(),
            "icon:ddt_exner_phy": sp_init.ddt_exner_phy().asnumpy(),
        }
    )
    solver._current_call_substeps = 2
    solver.substep_array_call(
        1, 0, {}, {}, timedelta(seconds=float(sp_init.get_metadata("dtime").get("dtime")))
    )

    restart = solver.restart_state()
    checks = (
        # test_nonhydro_corrector_step (EXCLAIM_APE leg), per-field:
        ("carry/rho_ic", sp_exit.rho_ic(), dict()),  # stencil 10 (l.577-580)
        ("carry/theta_v_ic", sp_exit.theta_v_ic(), dict(atol=1e-12)),  # (l.582-586)
        # vn: rtol=1e-9 (l.589-593; upstream note "was 1e-10 for local experiment only")
        ("nnew/vn", sp_exit.vn_new(), dict(rtol=1e-9)),
        ("nnew/exner", sp_exit.exner_new(), dict()),  # (l.595-598)
        ("nnew/rho", sp_exit.rho_new(), dict()),  # (l.600-603)
        ("nnew/w", sp_exit.w_new(), dict(atol=8e-14)),  # (l.605-609)
        ("nnew/theta_v", sp_exit.theta_v_new(), dict()),  # (l.611-614)
        ("carry/mass_fl_e", sp_exit.mass_fl_e(), dict(rtol=5e-7)),  # stencil 32 (l.625)
        ("prep_adv/mass_flx_me", sp_exit.mass_flx_me(), dict(rtol=5e-7)),  # 33,34
        ("prep_adv/vn_traj", sp_exit.vn_traj(), dict(rtol=5e-7)),  # 33,34 (l.638-642)
        ("carry/exner_dyn_incr", sp_exit.exner_dyn_incr(), dict(atol=1e-14)),  # 60
    )
    for key, reference, tols in checks:
        assert_allclose(
            np.asarray(restart[key].data),
            reference.asnumpy(),
            rtol=tols.get("rtol", 1e-12),
            atol=tols.get("atol", 0.0),
            names=(f"symcon {key}", "icon4py corrector exit"),
            equal_nan=False,
        )


# -- acceptance 3: restart bitwise reproducibility --------------------------------------------


def test_restart_bitwise_reproducibility(
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """Run 5 steps → serialize → restore into a fresh component → 5 more ≡ 10
    straight, bitwise fp64 (SPEC S12 acceptance 3)."""
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=1, date=DATE_FIRST, substep=1)
    dt = timedelta(seconds=float(sp_init.get_metadata("dtime").get("dtime")) * 2)

    def build() -> NonhydroSolver:
        solver = _make_solver(
            experiment=experiment,
            grid_savepoint=grid_savepoint,
            metrics_savepoint=metrics_savepoint,
            interpolation_savepoint=interpolation_savepoint,
            icon_grid=icon_grid,
            sp_init=sp_init,
            symcon_backend="gtfn_cpu",
        )
        _load_carry(solver, sp_init, at_initial=True, swap_w_pair=False)
        return solver

    def advance(solver: NonhydroSolver, state: dict[str, Any], n: int) -> dict[str, Any]:
        for _ in range(n):
            _, new_state = solver(state, dt)
            state = {**state, **new_state}
        return state

    solver_straight = build()
    state = _state_from_savepoint(sp_init, solver_straight.ctx)
    straight = advance(solver_straight, dict(state), 10)

    solver_a = build()
    half = advance(solver_a, dict(state), 5)
    blob = solver_a.restart_state()

    solver_b = build()
    solver_b.load_restart_state(blob)
    resumed = advance(solver_b, half, 5)

    for name, _accessor, _dims in _PROGNOSTICS:
        np.testing.assert_array_equal(
            _host(resumed[name].data), _host(straight[name].data), err_msg=name
        )


# -- acceptance 4: bus consumption (linear-response smoke) ------------------------------------


def test_bus_constant_vn_tendency_linear_response(
    data_provider: Any,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    icon_grid: Any,
) -> None:
    """A constant synthetic ``icon:ddt_vn_phy`` shifts vn by ≈ Δt·c over one Δt.

    ICON applies the slow vn tendency additively inside every substep
    (``mo_solve_nonhydro.f90`` l.1365/l.1410: ``vn_new = vn_now + Δτ(... + ddt_vn_phy)``),
    so over N substeps the leading-order response is exactly Δt·c; the residual is
    the dynamical feedback of the perturbation (advection/divergence damping of the
    Δτ·c increment), which is O(Δτ²) — the 2% bound is a smoke-test contract, not an
    upstream tolerance.
    """
    sp_init = data_provider.from_savepoint_nonhydro_init(istep=1, date=DATE_FIRST, substep=1)
    dt_seconds = float(sp_init.get_metadata("dtime").get("dtime")) * 2
    constant = 1.0e-6  # m s-2

    def run(with_bus: bool) -> np.ndarray:
        solver = _make_solver(
            experiment=experiment,
            grid_savepoint=grid_savepoint,
            metrics_savepoint=metrics_savepoint,
            interpolation_savepoint=interpolation_savepoint,
            icon_grid=icon_grid,
            sp_init=sp_init,
            symcon_backend="gtfn_cpu",
        )
        _load_carry(solver, sp_init, at_initial=True, swap_w_pair=False)
        state = _state_from_savepoint(sp_init, solver.ctx, bus=False)
        if with_bus:
            n_edges, n_levels = state["icon:normal_wind"].data.shape
            state["icon:ddt_vn_phy"] = _upload(
                solver.ctx,
                "icon:ddt_vn_phy",
                np.full((n_edges, n_levels), constant, dtype=np.float64),
                ("edge", "height"),
            )
        _, new_state = solver(state, timedelta(seconds=dt_seconds))
        return _host(new_state["icon:normal_wind"].data)

    baseline = run(with_bus=False)
    shifted = run(with_bus=True)
    increment = shifted - baseline
    expected = dt_seconds * constant
    assert_allclose(
        increment,
        np.full_like(increment, expected),
        rtol=0.0,
        atol=0.02 * expected,
        names=("vn response to constant ddt_vn_phy", "analytic Δt·c"),
        equal_nan=False,
    )
