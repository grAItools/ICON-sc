"""S08 acceptance 1 (marker ``data``): ladder-L2 parity of ``Microphysics``
(graupel scheme) against icon4py's own graupel verification data.

This is icon4py's integration test (REFERENCES.lock ``icon4py-graupel-test``)
rerun through the ICON-sc component: experiment WEISMAN_KLEMP_TORUS — the only
serialized archive carrying microphysics-init/microphysics-exit savepoints
(GAUSS3D, the S06 default, has none; the ~1.6 GB archive downloads once into
the shared cache) — three dates, one call site per step. The ICON-sc state is
built from the entry savepoint (dz from the metrics savepoint — the SPEC's
static-state input), the component hosts the granule on the savepoint's icon
grid with the *archive's own namelist configuration*
(``experiment.config.graupel``, the PLAN-pitfall pin), and the stepped state
plus the precipitation-rate diagnostics are compared to the exit savepoint at
**icon4py's own tolerances**.

Matrix: 3 dates x {embedded, gtfn_cpu, gtfn_gpu (``gpu``-marked, skips cleanly
without a CUDA device)}.
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from icon_sc.core import ComputeContext, make_backend
from icon_sc.core.state import canonical_units, make_dataarray
from icon_sc.core.testing import assert_allclose
from icon_sc.core.time import datetime
from icon_sc.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    # Re-exported icon4py fixtures (fixture *names* are what pytest resolves; the
    # bridge sets the cache path before icon4py.model.testing reads the env).
    from icon4py.model.testing import definitions as icon4py_definitions
    from icon4py.model.testing.fixtures import icon_grid, metrics_savepoint  # noqa: F401

    from icon_sc.icon.testing import (  # noqa: F401
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        process_props,
    )

    @pytest.fixture(
        params=[icon4py_definitions.Experiments.WEISMAN_KLEMP_TORUS], ids=lambda e: e.name
    )
    def experiment_description(request: Any) -> Any:
        """Override the S06 GAUSS3D default: only WK torus has graupel savepoints."""
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

#: icon4py's own graupel verification tolerances
#: (test_single_moment_six_class_gscp_graupel.py, v0.2.0: temperature via
#: ``test_utils.dallclose(...)`` at the dallclose defaults ``rtol=1.0e-12``/
#: ``atol=0.0``; the six tracers with explicit ``atol=1.0e-12``; the surface
#: precipitation fluxes with explicit ``atol=9.0e-11``) — the SPEC acceptance-1
#: tolerance contracts.
ICON4PY_RTOL = 1.0e-12
ICON4PY_TEMPERATURE_ATOL = 0.0
ICON4PY_TRACER_ATOL = 1.0e-12
ICON4PY_FLUX_ATOL = 9.0e-11

#: icon4py's parametrization, verbatim.
DATES = ["2008-09-01T01:59:48.000", "2008-09-01T01:59:52.000", "2008-09-01T01:59:56.000"]

#: Cell-column dims of the ICON-sc state built from the savepoints.
_DIMS = ("cell", "height")

#: (canonical name, savepoint accessor) for every stepped output field.
_FIELDS = (
    ("air_temperature", "temperature"),
    ("specific_humidity", "qv"),
    ("specific_cloud_content", "qc"),
    ("specific_ice_content", "qi"),
    ("specific_rain_content", "qr"),
    ("specific_snow_content", "qs"),
    ("specific_graupel_content", "qg"),
)

#: (canonical diagnostic name, exit-savepoint accessor) for the surface rates.
_RATES = (
    ("icon:rain_gsp_rate", "rain_flux"),
    ("icon:snow_gsp_rate", "snow_flux"),
    ("icon:ice_gsp_rate", "ice_flux"),
    ("icon:graupel_gsp_rate", "graupel_flux"),
)


def _upload(ctx: ComputeContext, name: str, host: np.ndarray, dims: tuple[str, ...]) -> Any:
    buffer: Any = ctx.require_allocator.empty(host.shape, host.dtype)
    buffer[...] = host  # numpy: aliasing-free copy; cupy: host->device upload
    return make_dataarray(
        buffer, name=name, dims=dims, units=canonical_units(name), location="cell"
    )


def _state_from_savepoint(
    graupel_entry: Any, metrics_savepoint: Any, ctx: ComputeContext
) -> dict[str, Any]:
    """A ICON-sc state (canonical names/units, S06/S08 registry) from the entry
    savepoint + the metrics savepoint (``icon:ddqz_z_full`` — dz).

    Buffers are allocated through the context so the state lives on the
    backend's device (strict mode rejects host buffers under a cupy context);
    this is *state construction* (the S06-builder role), not component ingress.
    """
    state: dict[str, Any] = {"time": datetime(2008, 9, 1)}
    for name, accessor in (
        *_FIELDS,
        ("air_pressure", "pressure"),
        ("air_density", "rho"),
    ):
        host = np.ascontiguousarray(getattr(graupel_entry, accessor)().asnumpy(), np.float64)
        state[name] = _upload(ctx, name, host, _DIMS)
    qnc = np.ascontiguousarray(graupel_entry.qnc().asnumpy(), dtype=np.float64)
    state["icon:qnc"] = _upload(ctx, "icon:qnc", qnc, ("cell",))
    dz = np.ascontiguousarray(metrics_savepoint.ddqz_z_full().asnumpy(), dtype=np.float64)
    state["icon:ddqz_z_full"] = _upload(ctx, "icon:ddqz_z_full", dz, _DIMS)
    return state


def _host(buffer: Any) -> np.ndarray:
    """Bring a state buffer back to the host for comparison (cupy ``.get()``)."""
    return buffer.get() if hasattr(buffer, "get") else np.asarray(buffer)


@pytest.mark.parametrize("date", DATES)
@pytest.mark.parametrize(
    "icon_sc_backend",
    ["embedded", "gtfn_cpu", pytest.param("gtfn_gpu", marks=pytest.mark.gpu)],
)
def test_graupel_l2_parity_against_icon4py_savepoints(
    icon_sc_backend: str,
    date: str,
    *,
    data_provider: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    icon_grid: Any,
    experiment: Any,
) -> None:
    from icon4py.model.common.grid import vertical as v_grid

    from icon_sc.icon.components import GraupelConfig, Microphysics

    entry_savepoint = data_provider.from_savepoint_weisman_klemp_graupel_entry(date=date)
    exit_savepoint = data_provider.from_savepoint_weisman_klemp_graupel_exit(date=date)
    dtime = float(entry_savepoint.dtime())

    # Vertical params exactly as icon4py's own test builds them.
    vertical_params = v_grid.VerticalGrid(
        config=experiment.config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )

    ctx = ComputeContext(backend=make_backend(icon_sc_backend))
    graupel = Microphysics(
        (icon_grid, vertical_params),
        GraupelConfig.from_icon4py(experiment.config.graupel),
        ctx,
        scheme="graupel",
    )
    state = _state_from_savepoint(entry_savepoint, metrics_savepoint, ctx)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # icon4py embedded-execution warnings
        diagnostics, new_state = graupel(state, timedelta(seconds=dtime))

    for name, accessor in _FIELDS:
        assert_allclose(
            _host(new_state[name].data),
            getattr(exit_savepoint, accessor)().asnumpy(),
            rtol=ICON4PY_RTOL,
            atol=ICON4PY_TEMPERATURE_ATOL if name == "air_temperature" else ICON4PY_TRACER_ATOL,
            names=(f"ICON-sc {name}", f"icon4py microphysics-exit {accessor}"),
        )
    for name, accessor in _RATES:
        assert_allclose(
            _host(diagnostics[name].data),
            getattr(exit_savepoint, accessor)().asnumpy(),
            rtol=ICON4PY_RTOL,
            atol=ICON4PY_FLUX_ATOL,
            names=(f"ICON-sc {name}", f"icon4py microphysics-exit {accessor}"),
        )
