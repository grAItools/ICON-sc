"""SPEC S04 acceptance 1: measured convergence orders on the 2-process linear ODE.

D = rotation, P1 = relaxation, P2 = damping (closed form in ``_coupling_toys``),
fp64, RK2 (Heun) as every Eₗ, Δt ∈ {T/64 … T/1024}. Expected slopes per thesis
§2.4 (Table 2.1): FC ≈ 2, LFC ≈ 1, PS ≈ 1, STS ≈ 1, SUS ≈ 1, SSUS(λ=½) ≈ 2,
SSUS(λ=0.3) ≈ 1; slope tolerance ±0.15 (contract).

The module also emits the convergence plot artifact (PLAN item 5) into
``development/records/S04_coupling_algebra/artifacts/`` for the human gate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from _coupling_toys import (
    ODE_DTS,
    ODE_T,
    ZETA_0,
    PlaneDamping,
    PlaneRelaxation,
    Rotation,
    RotationCore,
    integrate,
    make_scheme_steps,
    ode_exact,
    plane_state,
)

from symcon.core.testing import OrderFit, measure_order

pytestmark = pytest.mark.slow

#: Expected slopes (thesis §2.4) and the SPEC's contract tolerance.
EXPECTED_ORDER = {
    "fc": 2.0,
    "lfc": 1.0,
    "ps": 1.0,
    "sts": 1.0,
    "sus": 1.0,
    "ssus_half": 2.0,
    "ssus_03": 1.0,
}
SLOPE_TOLERANCE = 0.15

_SLOTS = {
    "eastward_wind": "tendency_of_eastward_wind",
    "northward_wind": "tendency_of_northward_wind",
}


def _final_state(scheme: str, dt_seconds: float) -> npt.NDArray[np.float64]:
    steps = make_scheme_steps(
        Rotation(),
        [PlaneRelaxation(), PlaneDamping()],
        RotationCore(),
        _SLOTS,
    )
    state = integrate(steps[scheme], plane_state(ZETA_0.real, ZETA_0.imag), dt_seconds, ODE_T)
    return np.array(
        [state["eastward_wind"].data[0, 0], state["northward_wind"].data[0, 0]],
        dtype=np.float64,
    )


@pytest.fixture(scope="module")
def fits() -> dict[str, OrderFit]:
    exact = ode_exact(ODE_T)
    return {
        scheme: measure_order(lambda dt, s=scheme: _final_state(s, dt), ODE_DTS, exact)
        for scheme in EXPECTED_ORDER
    }


@pytest.mark.parametrize("scheme", sorted(EXPECTED_ORDER))
def test_measured_order_matches_thesis(fits: dict[str, OrderFit], scheme: str) -> None:
    fit = fits[scheme]
    expected = EXPECTED_ORDER[scheme]
    assert abs(fit.slope - expected) <= SLOPE_TOLERANCE, (
        f"{scheme}: measured order {fit.slope:.3f} outside {expected} ± {SLOPE_TOLERANCE} — {fit}"
    )


def test_fc_and_strang_beat_first_order_schemes(fits: dict[str, OrderFit]) -> None:
    """Sanity cross-check: at the finest Δt the second-order schemes are more accurate."""
    finest_error = {scheme: fit.errors[-1] for scheme, fit in fits.items()}
    for second_order in ("fc", "ssus_half"):
        for first_order in ("lfc", "ps", "sts", "sus", "ssus_03"):
            assert finest_error[second_order] < finest_error[first_order]


def test_convergence_plot_artifact(fits: dict[str, OrderFit]) -> None:
    """PLAN item 5: convergence lines for the human gate (skips without matplotlib)."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    artifacts = (
        Path(__file__).resolve().parents[3] / "development/records/S04_coupling_algebra/artifacts"
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    for scheme, fit in sorted(fits.items()):
        ax.loglog(fit.dts, fit.errors, "o-", label=f"{scheme} (p={fit.slope:.2f})")
    anchor = np.asarray(fits["sus"].dts)
    ax.loglog(anchor, 0.5 * fits["sus"].errors[0] * (anchor / anchor[0]), "k:", label="slope 1")
    ax.loglog(
        anchor, 0.5 * fits["fc"].errors[0] * (anchor / anchor[0]) ** 2, "k--", label="slope 2"
    )
    ax.set_xlabel("Δt [s]")
    ax.set_ylabel("L∞ error vs closed form at T")
    ax.set_title("S04 acceptance 1 — linear ODE (D=rotation, P1=relaxation, P2=damping)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(artifacts / "convergence_ode.png", dpi=150)
    plt.close(fig)
