"""Shared synthetic column states for the S10 functional-core suites.

The reference_moist S06 column carries no hydrometeors, so a bare state
exercises almost none of the graupel scheme's process branches; these builders
inject Gaussian hydrometeor layers across the temperature range (warm rain,
mixed phase, cold ice/snow/graupel) so the JAX-vs-granule parity checks walk the
warm/cold/melting branches without reference data (the data-marked WK-torus
parity test is the acceptance-1 gate; this battery is the always-on guard).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from symcon.core.state import canonical_units, make_dataarray
from symcon.icon.testing import moist_test_column

TRACERS = (
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
)

PROGNOSTICS = ("air_temperature", *TRACERS)

RATES = (
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
)

#: Hydrometeor injection profiles: (field, peak mixing ratio, center height [m]).
_LAYERS = (
    ("specific_cloud_content", 2.0e-3, 3000.0),
    ("specific_rain_content", 1.0e-3, 2000.0),
    ("specific_ice_content", 5.0e-4, 7000.0),
    ("specific_snow_content", 8.0e-4, 6000.0),
    ("specific_graupel_content", 6.0e-4, 5000.0),
)


def hydrometeor_column(
    nlev: int = 65, n_cell: int = 2, *, qv_scale: float = 1.5, seed: int = 42
) -> dict[str, Any]:
    """A moist column with hydrometeors in warm, mixed-phase and cold layers."""
    state = moist_test_column("reference_moist", nlev=nlev, n_cell=n_cell)
    rng = np.random.default_rng(seed)
    z = np.asarray(state["altitude"].data)
    for name, peak, center in _LAYERS:
        profile = peak * np.exp(-((z - center) ** 2) / (2.0 * 3000.0**2))
        state[name].data[:] = profile * rng.uniform(0.3, 1.0, size=z.shape)
    state["specific_humidity"].data[:] *= qv_scale
    state["icon:qnc"] = make_dataarray(
        np.full((n_cell,), 200.0e6),
        name="icon:qnc",
        dims=("cell",),
        units=canonical_units("icon:qnc"),
        location="cell",
    )
    return state
