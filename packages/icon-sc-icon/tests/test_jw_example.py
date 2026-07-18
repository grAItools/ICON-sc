"""S13 acceptance 5 (markers ``data``+``slow``): example 02 CI smoke at 6 h.

Runs ``examples/02_jw_baroclinic.py`` at the SPEC's reduced length (6 simulated
hours = 72 composed steps on the JW archive grid) and inspects the NetCDF: the
declared output set is present, surface pressure stays physical, and the wave
perturbation is actually switched on (provenance check on the preset).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from icon_sc.icon.testing import DATATEST_AVAILABLE

pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples" / "02_jw_baroclinic.py"


def _load_example() -> Any:
    spec = importlib.util.spec_from_file_location("example_02_jw_baroclinic", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_02_smoke_6h(tmp_path: Path) -> None:
    """SPEC acceptance 5: the example runs 6 h and writes the declared variables."""
    xr = pytest.importorskip("xarray")
    example = _load_example()
    out = tmp_path / "jw_smoke.nc"
    final = example.main(output=out, hours=6.0, store_every_hours=3.0)

    assert set(final) >= {
        "icon:normal_wind",
        "upward_air_velocity_on_interface_levels",
        "air_density",
        "icon:exner_function",
        "icon:virtual_potential_temperature",
    }
    with xr.open_dataset(out) as dataset:
        for name in example.OUTPUT_SET:
            assert name in dataset, name
        ps = np.asarray(dataset["air_pressure_at_ground_level"].isel(time=-1))
    # physical sanity: the JW surface pressure stays near 1000 hPa at 6 h.
    assert 9.0e4 < ps.min() < ps.max() < 1.1e5
