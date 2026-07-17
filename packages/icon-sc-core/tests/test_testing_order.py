"""measure_order harness unit tests (SPEC S04, PLAN item 5)."""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.testing import measure_order


def test_exact_power_law_recovers_the_order() -> None:
    exact = np.array([1.0, 2.0])

    def build(dt: float) -> np.ndarray:
        return exact + 3.0 * dt**2

    fit = measure_order(build, [0.1, 0.05, 0.025, 0.0125], exact)
    assert fit.slope == pytest.approx(2.0, abs=1e-10)
    assert fit.errors[0] == pytest.approx(3.0 * 0.1**2)
    assert fit.dts == (0.1, 0.05, 0.025, 0.0125)


def test_ladder_is_sorted_coarse_to_fine() -> None:
    def build(dt: float) -> np.ndarray:
        return np.array([dt])  # first-order "error" against 0

    fit = measure_order(build, [0.025, 0.1, 0.05], np.array([0.0]))
    assert fit.dts == (0.1, 0.05, 0.025)
    assert fit.slope == pytest.approx(1.0, abs=1e-10)


def test_self_convergence_pairs() -> None:
    def build(dt: float) -> np.ndarray:
        return np.array([7.0 + 5.0 * dt**3])

    fit = measure_order(build, [0.2, 0.1, 0.05, 0.025], None)
    # err(dt) = 5 (dt^3 - (dt/2)^3) = 5 (7/8) dt^3: slope 3 exactly.
    assert fit.slope == pytest.approx(3.0, abs=1e-10)
    assert len(fit.errors) == 3
    assert fit.dts == (0.2, 0.1, 0.05)


def test_short_ladders_reject() -> None:
    with pytest.raises(ValueError, match="too short"):
        measure_order(lambda dt: np.array([dt]), [0.1], np.array([0.0]))
    with pytest.raises(ValueError, match="too short"):
        measure_order(lambda dt: np.array([dt]), [0.1, 0.05], None)


def test_repeated_entries_reject() -> None:
    with pytest.raises(ValueError, match="repeated"):
        measure_order(lambda dt: np.array([dt]), [0.1, 0.1, 0.05], np.array([0.0]))


def test_vanishing_errors_reject() -> None:
    exact = np.array([1.0])
    with pytest.raises(ValueError, match="finite and positive"):
        measure_order(lambda dt: exact, [0.1, 0.05], exact)


def test_custom_norm() -> None:
    exact = np.zeros(4)

    def build(dt: float) -> np.ndarray:
        return np.full(4, dt)

    fit = measure_order(
        build,
        [0.1, 0.05],
        exact,
        norm=lambda diff: float(np.sqrt(np.mean(diff**2))),
    )
    assert fit.errors[0] == pytest.approx(0.1)
