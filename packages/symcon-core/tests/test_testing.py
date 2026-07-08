"""Unit tests for the frozen symcon.core.testing interface (SPEC S01)."""

from __future__ import annotations

import numpy as np
import pytest

from symcon.core.testing import MARKERS, assert_allclose


def test_passes_on_close_arrays() -> None:
    a = np.linspace(0.0, 1.0, 101)
    assert_allclose(a, a * (1.0 + 1e-12), rtol=1e-9, atol=0.0, names="phi")


def test_failure_reports_worst_offender_index_values_and_name() -> None:
    desired = np.ones((3, 4))
    actual = desired.copy()
    actual[1, 2] = 1.5  # the single worst offender
    actual[2, 0] = 1.0001

    with pytest.raises(AssertionError) as excinfo:
        assert_allclose(actual, desired, rtol=1e-6, atol=0.0, names="theta_v")

    message = str(excinfo.value)
    assert "theta_v" in message
    assert "(1, 2)" in message
    assert "1.5" in message
    assert "rel err=5.0" in message  # |1.5-1.0|/1.0 = 5e-1
    assert "Not equal to tolerance" in message  # numpy's original report is preserved


def test_failure_reports_name_pair() -> None:
    with pytest.raises(AssertionError) as excinfo:
        assert_allclose(
            np.array([1.0]), np.array([2.0]), rtol=1e-6, atol=0.0, names=("t0", "t1")
        )
    assert "'t0' vs 't1'" in str(excinfo.value)


def test_nan_positions_must_match_by_default() -> None:
    a = np.array([np.nan, 1.0])
    assert_allclose(a, a, rtol=0.0, atol=0.0, names="w")
    with pytest.raises(AssertionError):
        assert_allclose(np.array([np.nan, 1.0]), np.array([1.0, 1.0]), rtol=1e-6, atol=0.0)


def test_atol_only_comparison() -> None:
    assert_allclose(np.zeros(4), np.full(4, 1e-9), rtol=0.0, atol=1e-8, names="rho")


def test_canonical_marker_names_are_frozen() -> None:
    assert set(MARKERS) == {"gpu", "mpi", "slow", "data"}


def test_markers_registered_with_pytest(pytestconfig: pytest.Config) -> None:
    registered = "\n".join(pytestconfig.getini("markers"))
    for name in MARKERS:
        assert f"{name}:" in registered
