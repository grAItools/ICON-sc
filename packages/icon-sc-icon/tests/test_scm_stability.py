"""S09 acceptance 2 — L3-lite stability of the SCM preset (``slow``-marked).

48 simulated hours at dt = 30 s on the preset's moist unstable column: no
NaN/Inf, tracers >= 0, total water conserved to graupel-scheme tolerance once
the accumulated surface precipitation is added back, and precipitation actually
accumulated. Runs on ``gtfn_cpu`` (the embedded backend executes the graupel
K-scan per column in Python — a 48 h run would take ~12 min; the compiled
n_cell=1 program variant is shared with ``test_scm_preset.py`` through the
persistent gt4py build cache).
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from symcon.core import ComputeContext, make_backend, timeloop
from symcon.core.testing import assert_allclose
from symcon.icon.components.fast.graupel_constants import GRAUPEL_QMIN
from symcon.icon.presets import build_scm

pytestmark = pytest.mark.slow

TRACERS = (
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
)
RATES = (
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
)

SIMULATED = timedelta(hours=48)

#: Water-budget closure of the 48 h run: |Δ(Σ q·rho·dz) + Σ precip·Δt| ≤ rtol ·
#: initial path. Characterized bound (STATUS S09): the measured defect grows to
#: ≈ -2e-13 relative after 5760 steps (the S08 per-step round-off contract of
#: 1e-13 accumulates far sub-linearly here; the documented cold-glaciation leak
#: corner is never entered by this trajectory) — the bound is that measurement
#: with ~50x margin, still round-off territory, far below any physics signal.
CONSERVATION_RTOL = 1e-11

#: Negativity contract, S08 precedent for the same tendency-application
#: arithmetic (x + dx/dt·Δt reconstructs a zeroed tracer with one rounding step,
#: so exact zero can land at -ε): no tracer below -QMIN, the graupel scheme's own
#: "lowest detectable mixing ratio". SPEC S09 says "tracers >= 0" — the measured
#: worst transient over the whole 48 h run is qc = -5.3e-23 (STATUS S09, HUMAN
#: SIGN-OFF flag), eight orders below this bound.
NEGATIVITY_EPS = GRAUPEL_QMIN


def test_l3_lite_stability_48h() -> None:
    ctx = ComputeContext(backend=make_backend("gtfn_cpu"))
    composition, state, cfg = build_scm(ctx=ctx)
    assert SIMULATED // cfg.dtime == 5760  # dt = 30 s (SPEC acceptance 2)

    rho = np.asarray(state["air_density"].data)
    dz = np.asarray(state["icon:ddqz_z_full"].data)
    path_initial = float((sum(np.asarray(state[n].data) for n in TRACERS) * rho * dz).sum())
    dt_seconds = cfg.dtime.total_seconds()

    accumulated = {"precip": 0.0}

    def step(current: dict[str, Any], timestep: timedelta) -> dict[str, Any]:
        advanced = composition.step(current, timestep)
        accumulated["precip"] += (
            float(sum(np.asarray(advanced[name].data).sum() for name in RATES)) * dt_seconds
        )
        # Per-step invariants (cheap on a single column): finite fields, no
        # tracer below the scheme's clipping epsilon (see NEGATIVITY_EPS note).
        for name in ("air_temperature", *TRACERS):
            values = np.asarray(advanced[name].data)
            assert np.isfinite(values).all(), name
        for name in TRACERS:
            assert float(np.asarray(advanced[name].data).min()) >= -NEGATIVITY_EPS, name
        return advanced

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        final = timeloop(state, step, timestep=cfg.dtime, until=SIMULATED)

    # Physically sane temperatures after 48 h of forcing (no runaway state).
    temperature = np.asarray(final["air_temperature"].data)
    assert temperature.min() > 150.0 and temperature.max() < 350.0

    # It rained: the unstable column precipitated (SPEC: "+ accumulated
    # precipitation" — the budget below is only meaningful if precip is nonzero).
    assert accumulated["precip"] > 1.0  # kg/m2 over 48 h; measured ≈ 19.4

    path_final = float((sum(np.asarray(final[n].data) for n in TRACERS) * rho * dz).sum())
    assert_allclose(
        path_final + accumulated["precip"],
        path_initial,
        rtol=CONSERVATION_RTOL,
        atol=0.0,
        names=("final water path + accumulated precip", "initial water path"),
    )
