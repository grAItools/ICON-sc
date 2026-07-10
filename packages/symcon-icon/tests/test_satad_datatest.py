"""S07 acceptance 1 (marker ``data``): ladder-L2 parity of ``SaturationAdjustment``
against icon4py's own satad verification data.

This is icon4py's integration test (REFERENCES.lock ``icon4py-satad-test``)
rerun through the symcon component: experiment WEISMAN_KLEMP_TORUS — the only
serialized archive carrying satad-init/satad-exit savepoints (GAUSS3D, the S06
default, has none; the ~1.6 GB archive downloads once into the shared cache) —
savepoints at two fast-physics call sites per step ("nwp-gscp-interface" before
graupel, "interface-nwp" — the tutorial-§3.7.2 double appearance), three dates.
The symcon state is built from the init savepoint, the component hosts the
granule on the savepoint's icon grid, and the adjusted state is compared to the
exit savepoint at **icon4py's own tolerances**.

Backends: embedded + gtfn_cpu (the CPU pair of the component suite); gtfn_gpu
under the ``gpu`` marker.
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from symcon.core import ComputeContext, make_backend
from symcon.core.state import canonical_units, make_dataarray
from symcon.core.testing import assert_allclose
from symcon.core.time import datetime
from symcon.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    # Re-exported icon4py fixtures (fixture *names* are what pytest resolves; the
    # bridge sets the cache path before icon4py.model.testing reads the env).
    from icon4py.model.testing import definitions as icon4py_definitions
    from icon4py.model.testing.fixtures import icon_grid  # noqa: F401

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
        """Override the S06 GAUSS3D default: only WK torus has satad savepoints."""
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
]

#: icon4py's own satad verification tolerances (test_saturation_adjustment.py,
#: v0.2.0: ``test_utils.dallclose(..., atol=1.0e-13)`` with the dallclose default
#: ``rtol=1.0e-12``) — the SPEC acceptance-1 tolerance contract.
ICON4PY_RTOL = 1.0e-12
ICON4PY_ATOL = 1.0e-13

#: icon4py's parametrization, verbatim.
DATES = ["2008-09-01T01:59:48.000", "2008-09-01T01:59:52.000", "2008-09-01T01:59:56.000"]
LOCATIONS = ["nwp-gscp-interface", "interface-nwp"]

#: Cell-column dims of the symcon state built from the savepoints.
_DIMS = ("cell", "height")


def _state_from_savepoint(satad_init: Any) -> dict[str, Any]:
    """A symcon state (canonical names/units, S06 registry) from satad-init."""
    fields = {
        "air_temperature": satad_init.temperature(),
        "specific_humidity": satad_init.qv(),
        "specific_cloud_content": satad_init.qc(),
        "air_density": satad_init.rho(),
    }
    state: dict[str, Any] = {"time": datetime(2008, 9, 1)}
    for name, field in fields.items():
        buffer = np.ascontiguousarray(field.asnumpy(), dtype=np.float64)
        state[name] = make_dataarray(
            buffer, name=name, dims=_DIMS, units=canonical_units(name), location="cell"
        )
    return state


@pytest.mark.parametrize("date", DATES)
@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize("symcon_backend", ["embedded", "gtfn_cpu"])
def test_satad_l2_parity_against_icon4py_savepoints(
    symcon_backend: str,
    location: str,
    date: str,
    *,
    data_provider: Any,
    grid_savepoint: Any,
    icon_grid: Any,
    experiment: Any,
) -> None:
    from icon4py.model.common.grid import vertical as v_grid

    from symcon.icon.components import SaturationAdjustment, SaturationAdjustmentConfig

    satad_init = data_provider.from_savepoint_satad_init(location=location, date=date)
    satad_exit = data_provider.from_savepoint_satad_exit(location=location, date=date)
    entry_savepoint = data_provider.from_savepoint_weisman_klemp_graupel_entry(date=date)
    dtime = float(entry_savepoint.dtime())

    # Vertical params exactly as icon4py's own test builds them.
    vertical_params = v_grid.VerticalGrid(
        config=experiment.config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )

    satad = SaturationAdjustment(
        (icon_grid, vertical_params),
        SaturationAdjustmentConfig(),
        ComputeContext(backend=make_backend(symcon_backend)),
    )
    state = _state_from_savepoint(satad_init)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # icon4py embedded-execution warnings
        _, new_state = satad(state, timedelta(seconds=dtime))

    assert_allclose(
        np.asarray(new_state["specific_humidity"].data),
        satad_exit.qv().asnumpy(),
        rtol=ICON4PY_RTOL,
        atol=ICON4PY_ATOL,
        names=("symcon qv", "icon4py satad-exit qv"),
    )
    assert_allclose(
        np.asarray(new_state["specific_cloud_content"].data),
        satad_exit.qc().asnumpy(),
        rtol=ICON4PY_RTOL,
        atol=ICON4PY_ATOL,
        names=("symcon qc", "icon4py satad-exit qc"),
    )
    assert_allclose(
        np.asarray(new_state["air_temperature"].data),
        satad_exit.temperature().asnumpy(),
        rtol=ICON4PY_RTOL,
        atol=ICON4PY_ATOL,
        names=("symcon temperature", "icon4py satad-exit temperature"),
    )
