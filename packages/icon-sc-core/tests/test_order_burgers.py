"""SPEC S04 acceptance 2: the order pattern on a PDE (thesis §2.5.2 spirit).

1-D viscous Burgers (D = advection + diffusion, periodic central differences,
N = 512, numpy) with a relaxation "physics" term P = (u_eq(x) - u)/τ. No closed
form, so orders are measured by self-convergence between consecutive ladder
solutions. Same expected pattern and ±0.15 tolerance as acceptance 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from _coupling_toys import (
    BURGERS_DTS,
    BURGERS_T,
    BurgersCore,
    BurgersDynamics,
    BurgersRelaxation,
    burgers_state,
    integrate,
    make_scheme_steps,
)

from icon_sc.core.testing import OrderFit, measure_order

pytestmark = pytest.mark.slow

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

_SLOTS = {"eastward_wind": "tendency_of_eastward_wind"}


def _final_field(scheme: str, dt_seconds: float) -> npt.NDArray[np.float64]:
    steps = make_scheme_steps(
        BurgersDynamics(),
        [BurgersRelaxation()],
        BurgersCore(),
        _SLOTS,
    )
    state = integrate(steps[scheme], burgers_state(), dt_seconds, BURGERS_T)
    return np.asarray(state["eastward_wind"].data[0], dtype=np.float64)


@pytest.fixture(scope="module")
def fits() -> dict[str, OrderFit]:
    return {
        scheme: measure_order(lambda dt, s=scheme: _final_field(s, dt), BURGERS_DTS, None)
        for scheme in EXPECTED_ORDER
    }


@pytest.mark.parametrize("scheme", sorted(EXPECTED_ORDER))
def test_pde_order_pattern(fits: dict[str, OrderFit], scheme: str) -> None:
    fit = fits[scheme]
    expected = EXPECTED_ORDER[scheme]
    assert abs(fit.slope - expected) <= SLOPE_TOLERANCE, (
        f"{scheme}: measured order {fit.slope:.3f} outside {expected} ± {SLOPE_TOLERANCE} — {fit}"
    )


def test_solution_stays_bounded(fits: dict[str, OrderFit]) -> None:
    """Stability guard: the coarsest run of every scheme stays within physical bounds."""
    for scheme in EXPECTED_ORDER:
        field = _final_field(scheme, BURGERS_DTS[0])
        assert np.all(np.isfinite(field))
        assert float(np.max(np.abs(field))) < 1.0


def test_convergence_plot_artifact(fits: dict[str, OrderFit]) -> None:
    """PLAN item 5: the PDE convergence lines for the human gate."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    artifacts = (
        Path(__file__).resolve().parents[3]
        / "development/work/reports/report-0004-coupling-algebra"
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
    ax.set_ylabel("L∞ self-convergence error at T")
    ax.set_title("S04 acceptance 2 — 1-D viscous Burgers + relaxation (N=512)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(artifacts / "convergence_burgers.png", dpi=150)
    plt.close(fig)
