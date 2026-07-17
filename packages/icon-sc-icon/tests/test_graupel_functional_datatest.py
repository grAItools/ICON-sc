"""S10 acceptance 1 (marker ``data``): functional-core parity — the graupel JAX
core against the **gtfn kernel** on the S08 reference data (L2 restated).

Same state construction as the S08 datatest (WEISMAN_KLEMP_TORUS entry
savepoints + metrics dz, the archive's own namelist configuration); the
reference here is the granule run through the symcon component on the
``gtfn_cpu`` backend, the candidate the JAX core on the identical inputs.
Contract: fp64, rtol ≤ 1e-10 (identical constants module makes this
achievable); mixing-ratio-valued fields carry an absolute floor at the
scheme's lowest detectable mixing ratio QMIN = 1e-15 (STATUS S10).
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from symcon.core import ComputeContext, make_backend
from symcon.core.testing import assert_allclose
from symcon.icon.components.fast.graupel_constants import GRAUPEL_QMIN
from symcon.icon.testing import DATATEST_AVAILABLE

try:  # jax + datatest stack must both be present
    import jax
except ImportError:  # pragma: no cover - jax is a dev dependency
    jax = None  # type: ignore[assignment]

if DATATEST_AVAILABLE:
    from icon4py.model.testing import definitions as icon4py_definitions
    from icon4py.model.testing.fixtures import icon_grid, metrics_savepoint  # noqa: F401

    from symcon.icon.testing import (  # noqa: F401
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
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
    pytest.mark.skipif(jax is None, reason="jax not installed (symcon-core[jax])"),
]

#: SPEC S10 acceptance-1 tolerance contract.
PARITY_RTOL = 1.0e-10
PARITY_ATOL = GRAUPEL_QMIN
#: Temperature is O(250 K): the relative contract carries it alone.
TEMPERATURE_ATOL = 0.0

DATES = ["2008-09-01T01:59:48.000", "2008-09-01T01:59:52.000", "2008-09-01T01:59:56.000"]

_FIELDS = (
    "air_temperature",
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
)
_RATES = (
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
)


@pytest.mark.parametrize("date", DATES)
def test_graupel_jax_core_vs_gtfn_kernel_on_wk_savepoints(
    date: str,
    *,
    data_provider: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    icon_grid: Any,
    experiment: Any,
) -> None:
    from icon4py.model.common.grid import vertical as v_grid
    from test_graupel_datatest import _state_from_savepoint  # S08 builder, reused

    from symcon.icon.components import GraupelConfig, Microphysics

    jax.config.update("jax_enable_x64", True)

    entry_savepoint = data_provider.from_savepoint_weisman_klemp_graupel_entry(date=date)
    dtime = float(entry_savepoint.dtime())
    vertical_params = v_grid.VerticalGrid(
        config=experiment.config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )

    ctx = ComputeContext(backend=make_backend("gtfn_cpu"))
    graupel = Microphysics(
        (icon_grid, vertical_params),
        GraupelConfig.from_icon4py(experiment.config.graupel),
        ctx,
        scheme="graupel",
    )
    state = _state_from_savepoint(entry_savepoint, metrics_savepoint, ctx)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        diagnostics, new_state = graupel(state, timedelta(seconds=dtime))
    reference = {name: np.asarray(array.data) for name, array in new_state.items()}
    reference.update({name: np.asarray(array.data) for name, array in diagnostics.items()})

    inputs = {name: np.asarray(state[name].data) for name in graupel.input_properties}
    out = graupel.functional_call(inputs, dict(graupel.functional_params()), dt=dtime)

    for name in (*_FIELDS, *_RATES):
        assert_allclose(
            np.asarray(out[name]),
            reference[name],
            rtol=PARITY_RTOL,
            atol=TEMPERATURE_ATOL if name == "air_temperature" else PARITY_ATOL,
            names=(f"JAX core {name}", f"gtfn kernel {name}"),
        )
