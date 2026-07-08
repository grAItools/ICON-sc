"""Test support shared by all symcon packages (frozen interface, SPEC S01).

Exports:
- :func:`assert_allclose` — numpy.testing wrapper with worst-offender reporting.
- :data:`MARKERS` — canonical pytest marker names/descriptions (``gpu``, ``mpi``,
  ``slow``, ``data``).
- :func:`register_markers` — hook helper used by the pytest plugin.

The pytest-dependent pieces (fixtures, hooks) live in :mod:`symcon.core.testing.plugin`
so that importing this module needs numpy only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    import pytest

__all__ = ["MARKERS", "assert_allclose", "register_markers"]

#: Canonical marker names; registered via the plugin, referenced by CI job filters.
MARKERS: dict[str, str] = {
    "gpu": "needs a CUDA device; must skip (not fail) when none is available",
    "mpi": "needs an MPI launch (pytest-mpi, np<=4)",
    "slow": "long-running; excluded from the default fast tier",
    "data": "downloads or reads reference data (pooch manifests); never data in git",
}


def register_markers(config: pytest.Config) -> None:
    """Register the canonical symcon markers on a pytest config."""
    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def assert_allclose(
    actual: npt.ArrayLike,
    desired: npt.ArrayLike,
    rtol: float = 1e-7,
    atol: float = 0.0,
    names: str | tuple[str, str] | None = None,
    equal_nan: bool = True,
) -> None:
    """``numpy.testing.assert_allclose`` with worst-offender reporting.

    On failure the raised ``AssertionError`` additionally names the field(s) being
    compared and pinpoints the single worst-offending element: its (multi-)index, the
    actual and desired values there, and the absolute/relative errors.

    ``names`` is either one label for the compared field or an
    ``(actual_name, desired_name)`` pair.
    """
    actual_arr = np.asarray(actual)
    desired_arr = np.asarray(desired)

    if isinstance(names, tuple):
        actual_name, desired_name = names
    elif names is not None:
        actual_name = desired_name = names
    else:
        actual_name = "actual"
        desired_name = "desired"

    try:
        np.testing.assert_allclose(
            actual_arr,
            desired_arr,
            rtol=rtol,
            atol=atol,
            equal_nan=equal_nan,
        )
    except AssertionError as exc:
        raise AssertionError(
            _worst_offender_report(actual_arr, desired_arr, rtol, atol, actual_name, desired_name)
            + "\n\n"
            + str(exc)
        ) from None


def _worst_offender_report(
    actual: npt.NDArray[np.generic],
    desired: npt.NDArray[np.generic],
    rtol: float,
    atol: float,
    actual_name: str,
    desired_name: str,
) -> str:
    label = (
        f"{actual_name!r} vs {desired_name!r}"
        if actual_name != desired_name
        else f"{actual_name!r}"
    )
    header = f"assert_allclose failed for {label} (rtol={rtol:g}, atol={atol:g})"

    try:
        a = np.broadcast_to(
            np.asarray(actual, dtype=np.float64), desired.shape if desired.shape else actual.shape
        )
        d = np.broadcast_to(np.asarray(desired, dtype=np.float64), a.shape)
    except (TypeError, ValueError):
        return header  # non-numeric or non-broadcastable; numpy's message has the rest

    abs_err = np.abs(a - d)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_err = np.where(d != 0, abs_err / np.abs(d), np.inf)
    rel_err = np.where(np.isnan(abs_err), np.nan, rel_err)

    # Violation of the assert_allclose criterion |a-d| <= atol + rtol*|d|; the worst
    # offender is the element violating it by the largest margin.
    violation = abs_err - (atol + rtol * np.abs(d))
    violation = np.where(np.isnan(violation), -np.inf, violation)
    if violation.size == 0:
        return header
    flat_idx = int(np.argmax(violation))
    idx = np.unravel_index(flat_idx, violation.shape)

    return (
        f"{header}\n"
        f"worst offender at index {tuple(int(i) for i in idx)}: "
        f"{actual_name}={a[idx]!r}, {desired_name}={d[idx]!r}, "
        f"abs err={abs_err[idx]:.6e}, rel err={rel_err[idx]:.6e}"
    )
