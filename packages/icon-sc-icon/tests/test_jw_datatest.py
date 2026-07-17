"""S13 acceptance 2 + composed-model parity (marker ``data``): the JW experiment.

Verification targets are icon4py's own JW tests on the ``exclaim_nh35_tri_jws``
archive (REFERENCES.lock ``icon4py-driver-jw-tests``):

- ``test_jabw_initial_condition`` — the initial state vs the ``jabw_exit`` savepoint
  at dallclose defaults (rtol=1e-12) for rho/exner/theta_v/vn/pressure/temperature,
  perturbed exner vs ``diagnostics_initial.exner_pr`` at atol=1e-14; w deliberately
  not verified (forced zero upstream and here);
- delegation parity (SPEC acceptance 2): the symcon initializer with
  ``perturbation_amplitude=0`` vs the *donor* ``model_initialization_jabw`` output
  at 1e-12 (the donor hard-wires ``jw_up=0``);
- ``test_run_timeloop_single_step`` (JW row) — one composed Δt (5 dynamics substeps
  then diffusion, driver order) through the symcon ``build_jw`` preset vs the
  diffusion/nonhydro exit savepoints at the upstream tolerances: vn atol=6e-12,
  w atol=1e-13, theta_v atol=4e-12, exner and rho at defaults.

The archive (~14 GB unpacked) downloads once into the shared datatest cache; the
composed leg reuses the persistent gtfn program cache (the dycore programs were
compiled by the S12 parity runs — grid sizes are runtime parameters).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from symcon.core.testing import assert_allclose
from symcon.icon.ingest.idealized import JablonowskiWilliamsonConfig, jablonowski_williamson
from symcon.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    from icon4py.model.testing import datatest_utils as dtu
    from icon4py.model.testing import definitions as icon4py_definitions
    from icon4py.model.testing.fixtures import icon_grid  # noqa: F401
    from icon4py.model.testing.fixtures.datatest import (  # noqa: F401
        interpolation_savepoint,
        metrics_savepoint,
    )

    from symcon.icon.testing import (  # noqa: F401  (re-exported icon4py fixtures)
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        process_props,
    )

    @pytest.fixture(params=[icon4py_definitions.Experiments.JW], ids=lambda e: e.name)
    def experiment_description(request: Any) -> Any:
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
]

#: Upstream JW savepoint dates (test_icon4py.py l.86-98): the single archived step.
STEP_DATE_INIT = "2008-09-01T00:05:00.000"
STEP_DATE_EXIT = "2008-09-01T00:05:00.000"


def _initializer_static(metrics_savepoint: Any, interpolation_savepoint: Any) -> dict[str, Any]:
    return {
        "icon:wgtfac_c": metrics_savepoint.wgtfac_c(),
        "icon:ddqz_z_half": metrics_savepoint.ddqz_z_half(),
        "icon:theta_ref_mc": metrics_savepoint.theta_ref_mc(),
        "icon:theta_ref_ic": metrics_savepoint.theta_ref_ic(),
        "icon:exner_ref_mc": metrics_savepoint.exner_ref_mc(),
        "icon:d_exner_dz_ref_ic": metrics_savepoint.d_exner_dz_ref_ic(),
        "icon:geopot": metrics_savepoint.geopot(),
        "icon:c_lin_e": interpolation_savepoint.c_lin_e(),
    }


def _build_state(
    experiment: Any,
    grid_savepoint: Any,
    icon_grid: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
    *,
    perturbation: float = 0.0,
) -> dict[str, Any]:
    from icon4py.model.common.grid import vertical as v_grid

    vertical_params = v_grid.VerticalGrid(
        config=experiment.config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )
    return jablonowski_williamson(
        icon_grid,
        vertical_params,
        JablonowskiWilliamsonConfig(perturbation_amplitude=perturbation),
        static=_initializer_static(metrics_savepoint, interpolation_savepoint),
        edge_geometry=grid_savepoint.construct_edge_geometry(),
        cell_geometry=grid_savepoint.construct_cell_geometry(),
    )


# -- acceptance 2a: the upstream initial-condition criterion ---------------------------------


def test_jw_initial_state_matches_jabw_exit_savepoint(
    experiment: Any,
    data_provider: Any,
    grid_savepoint: Any,
    icon_grid: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
) -> None:
    """Upstream ``test_jabw_initial_condition`` tolerances, verbatim: dallclose
    defaults (rtol=1e-12) for rho/exner/theta_v/vn/pressure/temperature vs the
    ``jabw_exit`` savepoint; perturbed exner atol=1e-14; w not verified (zero)."""
    state = _build_state(
        experiment, grid_savepoint, icon_grid, metrics_savepoint, interpolation_savepoint
    )
    sp_exit = data_provider.from_savepoint_jabw_exit()

    checks = (
        ("air_density", sp_exit.rho()),
        ("icon:exner_function", sp_exit.exner()),
        ("icon:virtual_potential_temperature", sp_exit.theta_v()),
        ("icon:normal_wind", sp_exit.vn()),
        ("air_pressure", sp_exit.pressure()),
        ("air_temperature", sp_exit.temperature()),
    )
    for name, reference in checks:
        assert_allclose(
            np.asarray(state[name].data),
            reference.asnumpy(),
            rtol=1e-12,
            atol=0.0,
            names=(f"symcon JW {name}", "icon4py jabw_exit savepoint"),
            equal_nan=False,
        )
    np.testing.assert_array_equal(
        np.asarray(state["upward_air_velocity_on_interface_levels"].data), 0.0
    )
    # perturbed exner (the dycore's cold-start exner_pr) vs diagnostics_initial
    # (upstream l.102-106, atol=1e-14):
    exner_pr = (
        np.asarray(state["icon:exner_function"].data) - metrics_savepoint.exner_ref_mc().asnumpy()
    )
    assert_allclose(
        exner_pr,
        data_provider.from_savepoint_diagnostics_initial().exner_pr().asnumpy(),
        rtol=1e-12,
        atol=1e-14,
        names=("symcon JW exner - exner_ref", "icon4py diagnostics_initial exner_pr"),
        equal_nan=False,
    )


# -- acceptance 2b: delegation parity against the donor initializer ---------------------------


def test_jw_initializer_delegation_parity(
    experiment: Any,
    data_provider: Any,
    process_props: Any,
    grid_savepoint: Any,
    icon_grid: Any,
    metrics_savepoint: Any,
    interpolation_savepoint: Any,
) -> None:
    """symcon initializer (perturbation 0) == donor ``model_initialization_jabw``
    to 1e-12 (SPEC acceptance 2: delegation is possible — the donor is importable)."""
    del data_provider  # gates on the downloaded archive
    from icon4py.model.driver.testcases import jablonowski_williamson as donor

    state = _build_state(
        experiment, grid_savepoint, icon_grid, metrics_savepoint, interpolation_savepoint
    )
    (
        _diffusion_diag,
        _nh_diag,
        _prep_adv,
        second_order_divdamp_factor,
        donor_diagnostics,
        donor_now,
        _donor_next,
    ) = donor.model_initialization_jabw(
        grid=icon_grid,
        cell_param=grid_savepoint.construct_cell_geometry(),
        edge_param=grid_savepoint.construct_edge_geometry(),
        path=dtu.get_datapath_for_experiment(experiment.description, process_props),
        backend=None,  # donor helpers run on numpy; gt4py steps on embedded
        rank=0,
    )
    assert second_order_divdamp_factor == 0.0

    checks = (
        ("icon:normal_wind", donor_now.vn),
        ("upward_air_velocity_on_interface_levels", donor_now.w),
        ("air_density", donor_now.rho),
        ("icon:exner_function", donor_now.exner),
        ("icon:virtual_potential_temperature", donor_now.theta_v),
        ("air_temperature", donor_diagnostics.temperature),
        ("air_pressure", donor_diagnostics.pressure),
    )
    for name, reference in checks:
        assert_allclose(
            np.asarray(state[name].data),
            reference.asnumpy(),
            rtol=1e-12,
            atol=0.0,
            names=(f"symcon JW {name}", "icon4py model_initialization_jabw"),
            equal_nan=False,
        )


# -- composed single-step parity (upstream timeloop tolerances) --------------------------------


def test_jw_composed_single_step_parity(data_provider: Any, experiment: Any) -> None:
    """Upstream ``test_run_timeloop_single_step`` (JW row) through the symcon
    ``build_jw`` preset: one Δt = 5 solve_nonhydro substeps then diffusion.

    State/carry staged from the archived savepoints exactly as upstream stages its
    TimeLoop (nonhydro-init + velocity-init at istep=1/substep=1, diffusion-init
    diagnostics; z-intermediates cold like upstream's freshly allocated granule).
    Tolerances verbatim from test_icon4py.py l.335-367: vn atol=6e-12, w atol=1e-13,
    theta_v atol=4e-12, exner defaults (vs diffusion exit); rho defaults (vs
    nonhydro exit, istep=2 substep=5).
    """
    from datetime import timedelta

    from symcon.core.state import canonical_units, make_dataarray
    from symcon.icon.presets import JWConfig, build_jw

    model = build_jw(JWConfig(perturbation_amplitude=0.0, backend="gtfn_cpu"))
    n_substeps = int(model.provenance["ndyn_substeps"])
    assert n_substeps == 5  # the archive's namelist (config congruence)
    assert model.dtime == timedelta(seconds=300.0)

    sp = data_provider.from_savepoint_nonhydro_init(istep=1, date=STEP_DATE_INIT, substep=1)
    sp_v = data_provider.from_savepoint_velocity_init(istep=1, date=STEP_DATE_INIT, substep=1)
    sp_diffusion_init = data_provider.from_savepoint_diffusion_init(
        linit=False, date=STEP_DATE_INIT
    )
    sp_diffusion_exit = data_provider.from_savepoint_diffusion_exit(
        linit=False, date=STEP_DATE_EXIT
    )
    sp_nonhydro_exit = data_provider.from_savepoint_nonhydro_exit(
        istep=2, date=STEP_DATE_EXIT, substep=n_substeps
    )
    linit = bool(sp.get_metadata("linit").get("linit"))

    # -- dycore carry through the S12 restart protocol ---------------------------------
    carry = model.dycore.restart_state()

    def put(key: str, value: Any) -> None:
        carry[key].data[...] = np.asarray(value.asnumpy() if hasattr(value, "asnumpy") else value)

    put("nnow/vn", sp.vn_now())
    put("nnow/w", sp.w_now())
    put("nnow/rho", sp.rho_now())
    put("nnow/exner", sp.exner_now())
    put("nnow/theta_v", sp.theta_v_now())
    put("nnew/vn", sp.vn_new())
    put("nnew/w", sp.w_new())
    put("nnew/rho", sp.rho_new())
    put("nnew/exner", sp.exner_new())
    put("nnew/theta_v", sp.theta_v_new())
    put("carry/ddt_vn_apc_predictor", sp_v.ddt_vn_apc_pc(0))
    put("carry/ddt_vn_apc_corrector", sp_v.ddt_vn_apc_pc(1))
    # upstream: PredictorCorrectorPair(ddt_w_adv_pc(current), ddt_w_adv_pc(next))
    # with (0, 1) if linit else (1, 0) — test_icon4py.py l.272-283.
    w_pred, w_corr = (0, 1) if linit else (1, 0)
    put("carry/ddt_w_adv_predictor", sp_v.ddt_w_adv_pc(w_pred))
    put("carry/ddt_w_adv_corrector", sp_v.ddt_w_adv_pc(w_corr))
    put("carry/vt", sp_v.vt())
    put("carry/vn_ie", sp_v.vn_ie())
    put("carry/w_concorr_c", sp_v.w_concorr_c())
    put("carry/theta_v_ic", sp.theta_v_ic())
    put("carry/rho_ic", sp.rho_ic())
    put("carry/exner_pr", sp.exner_pr())
    put("carry/mass_fl_e", sp.mass_fl_e())
    put("carry/exner_dyn_incr", sp.exner_dyn_incr())
    put("prep_adv/vn_traj", sp.vn_traj())
    put("prep_adv/mass_flx_me", sp.mass_flx_me())
    put("prep_adv/mass_flx_ic", sp.mass_flx_ic())
    # z intermediates + vol_flx stay zero (upstream's TimeLoop granule starts them
    # freshly allocated); bookkeeping mirrors restart_mode=False:
    carry["meta/at_initial_timestep"].data[...] = 1.0
    carry["meta/steps_done"].data[...] = 0.0
    model.dycore.load_restart_state(carry)

    # -- diffusion diagnostics from the diffusion-init savepoint ------------------------
    diffusion_carry = model.diffusion.restart_state()
    for key, accessor in (
        ("carry/hdef_ic", "hdef_ic"),
        ("carry/div_ic", "div_ic"),
        ("carry/dwdx", "dwdx"),
        ("carry/dwdy", "dwdy"),
    ):
        diffusion_carry[key].data[...] = getattr(sp_diffusion_init, accessor)().asnumpy()
    model.diffusion.load_restart_state(diffusion_carry)

    # -- boundary state (prognostics + bus slots) from the savepoints -------------------
    def upload(name: str, host: np.ndarray, dims: tuple[str, ...]) -> Any:
        return make_dataarray(
            np.ascontiguousarray(host, dtype=np.float64),
            name=name,
            dims=dims,
            units=canonical_units(name),
            location="edge" if dims[0] == "edge" else "cell",
        )

    state: dict[str, Any] = {
        "icon:normal_wind": upload("icon:normal_wind", sp.vn_now().asnumpy(), ("edge", "height")),
        "upward_air_velocity_on_interface_levels": upload(
            "upward_air_velocity_on_interface_levels",
            sp.w_now().asnumpy(),
            ("cell", "height_interface"),
        ),
        "air_density": upload("air_density", sp.rho_now().asnumpy(), ("cell", "height")),
        "icon:exner_function": upload(
            "icon:exner_function", sp.exner_now().asnumpy(), ("cell", "height")
        ),
        "icon:virtual_potential_temperature": upload(
            "icon:virtual_potential_temperature", sp.theta_v_now().asnumpy(), ("cell", "height")
        ),
        "icon:ddt_vn_phy": upload("icon:ddt_vn_phy", sp.ddt_vn_phy().asnumpy(), ("edge", "height")),
        "icon:ddt_exner_phy": upload(
            "icon:ddt_exner_phy", sp.ddt_exner_phy().asnumpy(), ("cell", "height")
        ),
    }

    new_state = model.step(state, model.dtime)

    # test_icon4py.py l.341-345: vn atol=6e-12
    assert_allclose(
        np.asarray(new_state["icon:normal_wind"].data),
        sp_diffusion_exit.vn().asnumpy(),
        rtol=1e-12,
        atol=6e-12,
        names=("symcon composed vn", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # l.347-351: w atol=1e-13
    assert_allclose(
        np.asarray(new_state["upward_air_velocity_on_interface_levels"].data),
        sp_diffusion_exit.w().asnumpy(),
        rtol=1e-12,
        atol=1e-13,
        names=("symcon composed w", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # l.353-356: exner at defaults
    assert_allclose(
        np.asarray(new_state["icon:exner_function"].data),
        sp_diffusion_exit.exner().asnumpy(),
        rtol=1e-12,
        atol=0.0,
        names=("symcon composed exner", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # l.358-362: theta_v atol=4e-12
    assert_allclose(
        np.asarray(new_state["icon:virtual_potential_temperature"].data),
        sp_diffusion_exit.theta_v().asnumpy(),
        rtol=1e-12,
        atol=4e-12,
        names=("symcon composed theta_v", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # l.364-367: rho vs nonhydro exit at defaults
    assert_allclose(
        np.asarray(new_state["air_density"].data),
        sp_nonhydro_exit.rho_new().asnumpy(),
        rtol=1e-12,
        atol=0.0,
        names=("symcon composed rho", "icon4py nonhydro exit"),
        equal_nan=False,
    )
