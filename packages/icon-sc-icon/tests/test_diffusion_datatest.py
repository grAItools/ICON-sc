"""S13 acceptance 1 (marker ``data``): ``HorizontalDiffusion`` savepoint parity.

icon4py's diffusion integration tests rerun through the ICON-sc component boundary
(REFERENCES.lock ``icon4py-diffusion-tests``):

- ``test_run_diffusion_single_step`` — EXCLAIM_APE (global R02B04, the archive S11/S12
  already cache) at 2000-01-01T00:00:02.000, ``linit=False``;
- ``test_run_diffusion_initial_step`` — MCH_CH_R04B09 (regional) at
  2021-06-20T12:00:10.000, ``linit=True`` → the component's explicit
  :meth:`initial_stabilization` entry.

Grid construction mirrors upstream *exactly*: upstream builds the grid from the grid
**file** with ``keep_skip_values=True`` and derives Cell/EdgeParams from
``GridGeometry`` (test_diffusion.py ``_get_or_initialize``) — which is precisely the
ICON-sc production path (``from_file`` + geometry derived inside the component), so
these tests double as the S13 production-path leg. Note the contrast with the S12
pentagon dossier: upstream diffusion parity **passes deterministically on the
file-built global grid with the 12 pentagon ``-1``s retained** — the granule's only
pentagon-adjacent access is a guarded ``neighbor_sum`` V2E reduction.

Tolerances are icon4py's own ``verify_diffusion_fields`` (utils.py:16-53 at v0.2.0),
cited per field below; dallclose defaults are ``rtol=1e-12, atol=0``. No ``embedded``
leg: upstream marks every diffusion datatest ``embedded_remap_error``/
``uses_concat_where`` (xfail on embedded), so parity runs on gtfn_cpu (+ gpu-marked
gtfn_gpu, which skips cleanly without a CUDA device).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from icon_sc.core import ComputeContext
from icon_sc.core.ingress.gt4py import make_backend
from icon_sc.core.state import canonical_units, make_dataarray
from icon_sc.core.testing import assert_allclose
from icon_sc.icon.components import DiffusionConfig, HorizontalDiffusion
from icon_sc.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    from icon4py.model.testing import definitions as icon4py_definitions

    from icon_sc.icon.testing import (  # noqa: F401  (re-exported icon4py fixtures)
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        process_props,
    )

    @pytest.fixture(
        params=[
            icon4py_definitions.Experiments.EXCLAIM_APE,
            pytest.param(icon4py_definitions.Experiments.MCH_CH_R04B09, marks=pytest.mark.slow),
        ],
        ids=lambda e: e.name,
    )
    def experiment_description(request: Any) -> Any:
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

#: Upstream per-experiment savepoint dates (test_diffusion.py l.313-327).
_SINGLE_STEP_DATE = {
    "exclaim_ape_R02B04": "2000-01-01T00:00:02.000",
    "exclaim_ch_r04b09_dsl": "2021-06-20T12:00:10.000",
}
_INITIAL_STEP_DATE = "2021-06-20T12:00:10.000"

#: Parity backends (no embedded leg — see module docstring).
BACKENDS = ["gtfn_cpu", pytest.param("gtfn_gpu", marks=pytest.mark.gpu)]

_PROGNOSTICS = (
    ("icon:normal_wind", "vn", ("edge", "height")),
    ("upward_air_velocity_on_interface_levels", "w", ("cell", "height_interface")),
    ("icon:exner_function", "exner", ("cell", "height")),
    ("icon:virtual_potential_temperature", "theta_v", ("cell", "height")),
)


def _host(buffer: Any) -> np.ndarray:
    return buffer.get() if hasattr(buffer, "get") else np.asarray(buffer)


def _static_from_savepoints(metrics_savepoint: Any, interpolation_savepoint: Any) -> dict[str, Any]:
    """The static state as ready icon4py fields — exactly how icon4py's own fixtures
    build ``DiffusionMetricState``/``DiffusionInterpolationState`` (fixtures.py:39-65)."""
    m, i = metrics_savepoint, interpolation_savepoint
    grg = i.geofac_grg()
    return {
        "icon:theta_ref_mc": m.theta_ref_mc(),
        "icon:wgtfac_c": m.wgtfac_c(),
        "icon:zd_intcoef": m.zd_intcoef(),
        "icon:zd_vertoffset": m.zd_vertoffset(),
        "icon:zd_diffcoef": m.zd_diffcoef(),
        "icon:e_bln_c_s": i.e_bln_c_s(),
        "icon:rbf_vec_coeff_v1": i.rbf_vec_coeff_v1(),
        "icon:rbf_vec_coeff_v2": i.rbf_vec_coeff_v2(),
        "icon:geofac_div": i.geofac_div(),
        "icon:geofac_n2s": i.geofac_n2s(),
        "icon:geofac_grg_x": grg[0],
        "icon:geofac_grg_y": grg[1],
        "icon:nudgecoeff_e": i.nudgecoeff_e(),
    }


def _file_grid(experiment: Any, ctx: ComputeContext) -> Any:
    """The upstream grid construction: grid file, ``keep_skip_values=True`` (S11 path)."""
    from icon_sc.icon.grid import from_file
    from icon_sc.icon.testing import download_grid_file

    return from_file(
        download_grid_file(experiment.grid),
        ctx,
        num_levels=experiment.config.vertical_grid.num_levels,
        keep_skip_values=True,
    )


def _make_component(
    *,
    experiment: Any,
    data_provider: Any,
    icon_sc_backend: str,
) -> tuple[HorizontalDiffusion, DiffusionConfig, ComputeContext]:
    """Component construction mirroring upstream ``test_run_diffusion_single_step``."""
    from icon4py.model.common.grid import vertical as v_grid

    ctx = ComputeContext(backend=make_backend(icon_sc_backend))
    grid = _file_grid(experiment, ctx)
    config = DiffusionConfig.from_icon4py(experiment.config.diffusion)
    vertical_config = experiment.config.vertical_grid
    vct_a, vct_b = v_grid.get_vct_a_and_vct_b(vertical_config, ctx.backend.gt4py_backend)
    vertical_params = v_grid.VerticalGrid(config=vertical_config, vct_a=vct_a, vct_b=vct_b)
    metrics_savepoint = data_provider.from_metrics_savepoint()
    interpolation_savepoint = data_provider.from_interpolation_savepoint()
    component = HorizontalDiffusion(
        grid,
        vertical_params,
        _static_from_savepoints(metrics_savepoint, interpolation_savepoint),
        config,
        ctx,
    )
    return component, config, ctx


def _load_diagnostics(component: HorizontalDiffusion, sp_init: Any) -> None:
    """The private turbulence diagnostics from the init savepoint, through the
    restart protocol (upstream builds DiffusionDiagnosticState from these fields)."""
    carry = component.restart_state()
    for key, accessor in (
        ("carry/hdef_ic", "hdef_ic"),
        ("carry/div_ic", "div_ic"),
        ("carry/dwdx", "dwdx"),
        ("carry/dwdy", "dwdy"),
    ):
        carry[key].data[...] = getattr(sp_init, accessor)().asnumpy()
    component.load_restart_state(carry)


def _state_from_savepoint(sp_init: Any, ctx: ComputeContext) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name, accessor, dims in _PROGNOSTICS:
        host = np.ascontiguousarray(getattr(sp_init, accessor)().asnumpy(), np.float64)
        buffer: Any = ctx.require_allocator.empty(host.shape, host.dtype)
        buffer[...] = host
        state[name] = make_dataarray(
            buffer,
            name=name,
            dims=dims,
            units=canonical_units(name),
            location="edge" if dims[0] == "edge" else "cell",
        )
    return state


def _verify(
    component: HorizontalDiffusion,
    config: DiffusionConfig,
    new_state: dict[str, Any],
    sp_exit: Any,
) -> None:
    """icon4py ``verify_diffusion_fields`` through the component boundary
    (utils.py:16-53; tolerances cited per line)."""
    # vn: atol=1.0e-8, rtol=1.0e-9 (l.48)
    assert_allclose(
        _host(new_state["icon:normal_wind"].data),
        sp_exit.vn().asnumpy(),
        rtol=1.0e-9,
        atol=1.0e-8,
        names=("ICON-sc vn", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # w: atol=1e-14 (l.49)
    assert_allclose(
        _host(new_state["upward_air_velocity_on_interface_levels"].data),
        sp_exit.w().asnumpy(),
        rtol=1e-12,
        atol=1e-14,
        names=("ICON-sc w", "icon4py diffusion exit"),
        equal_nan=False,
    )
    # theta_v, exner: dallclose defaults rtol=1e-12 (l.50-51)
    for name, accessor in (
        ("icon:virtual_potential_temperature", "theta_v"),
        ("icon:exner_function", "exner"),
    ):
        assert_allclose(
            _host(new_state[name].data),
            getattr(sp_exit, accessor)().asnumpy(),
            rtol=1e-12,
            atol=0.0,
            names=(f"ICON-sc {accessor}", "icon4py diffusion exit"),
            equal_nan=False,
        )
    # diagnostics only when shear_type >= VERTICAL_HORIZONTAL_OF_HORIZONTAL_WIND
    # (l.31-46): div_ic atol=1e-16, hdef_ic atol=1e-13, dwdx/dwdy atol=1e-18.
    if config.shear_type >= 1:
        restart = component.restart_state()
        for key, accessor, atol in (
            ("carry/div_ic", "div_ic", 1e-16),
            ("carry/hdef_ic", "hdef_ic", 1e-13),
            ("carry/dwdx", "dwdx", 1e-18),
            ("carry/dwdy", "dwdy", 1e-18),
        ):
            assert_allclose(
                np.asarray(restart[key].data),
                getattr(sp_exit, accessor)().asnumpy(),
                rtol=1e-12,
                atol=atol,
                names=(f"ICON-sc {accessor}", "icon4py diffusion exit"),
                equal_nan=False,
            )


# -- acceptance 1: savepoint parity -----------------------------------------------------------


@pytest.mark.parametrize("icon_sc_backend", BACKENDS)
def test_run_diffusion_single_step_parity(
    icon_sc_backend: str,
    data_provider: Any,
    experiment: Any,
) -> None:
    """Upstream ``test_run_diffusion_single_step`` through the component boundary."""
    if icon_sc_backend == "gtfn_gpu":
        pytest.importorskip("cupy")
    date = _SINGLE_STEP_DATE[experiment.name]
    sp_init = data_provider.from_savepoint_diffusion_init(linit=False, date=date)
    sp_exit = data_provider.from_savepoint_diffusion_exit(linit=False, date=date)
    dtime = float(sp_init.get_metadata("dtime").get("dtime"))

    component, config, ctx = _make_component(
        experiment=experiment, data_provider=data_provider, icon_sc_backend=icon_sc_backend
    )
    _load_diagnostics(component, sp_init)

    # upstream asserts the derived boundary-diffusion coefficient before running
    # (test_diffusion.py l.377): the archive's fac_bdydiff_v equals the granule's.
    assert float(sp_init.fac_bdydiff_v()) == component._diffusion.fac_bdydiff_v

    state = _state_from_savepoint(sp_init, ctx)
    _, new_state = component(state, timedelta(seconds=dtime))
    _verify(component, config, new_state, sp_exit)


@pytest.mark.slow
def test_run_diffusion_initial_step_parity(
    data_provider: Any,
    experiment: Any,
) -> None:
    """Upstream ``test_run_diffusion_initial_step`` (MCH_CH_R04B09, linit=True)
    through the component's explicit :meth:`initial_stabilization` entry."""
    if experiment.name != "exclaim_ch_r04b09_dsl":
        pytest.skip("upstream runs the initial step for MCH_CH_R04B09 only")
    sp_init = data_provider.from_savepoint_diffusion_init(linit=True, date=_INITIAL_STEP_DATE)
    sp_exit = data_provider.from_savepoint_diffusion_exit(linit=True, date=_INITIAL_STEP_DATE)
    dtime = float(sp_init.get_metadata("dtime").get("dtime"))

    component, config, ctx = _make_component(
        experiment=experiment, data_provider=data_provider, icon_sc_backend="gtfn_cpu"
    )
    _load_diagnostics(component, sp_init)
    assert float(sp_init.fac_bdydiff_v()) == component._diffusion.fac_bdydiff_v

    state = _state_from_savepoint(sp_init, ctx)
    _, new_state = component.initial_stabilization(state, timedelta(seconds=dtime))
    _verify(component, config, new_state, sp_exit)


def test_config_provenance_roundtrip(experiment: Any, data_provider: Any) -> None:
    """The archive's namelist-derived DiffusionConfig mirrors losslessly through the
    ICON-sc config (the PLAN 'config congruence' pitfall — asserted, not assumed)."""
    del data_provider  # only here to gate on the downloaded archive
    theirs = experiment.config.diffusion
    ours = DiffusionConfig.from_icon4py(theirs).to_icon4py()
    for attr in (
        "diffusion_type",
        "apply_to_vertical_wind",
        "apply_to_horizontal_wind",
        "apply_to_temperature",
        "type_vn_diffu",
        "type_t_diffu",
        "hdiff_efdt_ratio",
        "hdiff_w_efdt_ratio",
        "smagorinski_scaling_factor",
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
