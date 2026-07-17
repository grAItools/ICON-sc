"""Convergence-order measurement harness (SPEC S04, PLAN item 5).

``measure_order(builder, dts, exact)`` runs one integration per Δt and fits the
slope of ``log(error)`` against ``log(Δt)`` — the measured order of accuracy the
S04 acceptance criteria (and, later, the L7 validation ladder) assert against
thesis §2.4 expectations. With ``exact=None`` the errors are self-convergence
differences between consecutive ladder solutions (for problems without a closed
form, thesis §2.5.2 spirit); the fit then uses the coarser Δt of each pair.

numpy-only by design (importable wherever :mod:`icon_sc.core.testing` is).
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = ["OrderFit", "measure_order"]

#: One ladder run: Δt in seconds -> the solution at the final time (array-like).
Builder = Callable[[float], npt.ArrayLike]
#: Error norm on the difference array; default is the max-abs (L∞) norm.
Norm = Callable[[npt.NDArray[np.floating[Any]]], float]


@dataclasses.dataclass(frozen=True, slots=True)
class OrderFit:
    """Result of one order measurement (the fitted slope is the measured order)."""

    dts: tuple[float, ...]
    errors: tuple[float, ...]
    slope: float
    intercept: float

    def __str__(self) -> str:
        points = ", ".join(
            f"(dt={dt:.3e}, err={err:.3e})" for dt, err in zip(self.dts, self.errors, strict=True)
        )
        return f"OrderFit(slope={self.slope:.3f}; {points})"


def _linf(difference: npt.NDArray[np.floating[Any]]) -> float:
    return float(np.max(np.abs(difference)))


def measure_order(
    builder: Builder,
    dts: Sequence[float],
    exact: npt.ArrayLike | None,
    *,
    norm: Norm | None = None,
) -> OrderFit:
    """Measure the convergence order of ``builder`` over the Δt ladder (SPEC S04).

    ``builder(dt)`` integrates to the common final time and returns the solution;
    ``dts`` is the ladder in seconds (need not be sorted; at least two entries,
    three for self-convergence). ``exact`` is the reference solution at the final
    time, or ``None`` for self-convergence (errors between consecutive ladder
    solutions, sorted from coarse to fine). Returns an :class:`OrderFit`; its
    ``slope`` is the least-squares order estimate.
    """
    ladder = sorted((float(dt) for dt in dts), reverse=True)
    if len(ladder) < (2 if exact is not None else 3):
        raise ValueError(f"measure_order: ladder {ladder!r} is too short to fit a slope.")
    if len(set(ladder)) != len(ladder):
        raise ValueError(f"measure_order: ladder {ladder!r} has repeated entries.")
    solutions = [np.asarray(builder(dt), dtype=np.float64) for dt in ladder]

    error_norm = norm if norm is not None else _linf
    if exact is not None:
        reference = np.asarray(exact, dtype=np.float64)
        errors = [error_norm(solution - reference) for solution in solutions]
        fit_dts = ladder
    else:
        errors = [error_norm(coarse - fine) for coarse, fine in itertools.pairwise(solutions)]
        fit_dts = ladder[:-1]
    if any(not math.isfinite(err) or err <= 0.0 for err in errors):
        raise ValueError(
            f"measure_order: errors {errors!r} are not all finite and positive; "
            f"cannot fit a log-log slope."
        )
    slope, intercept = np.polyfit(np.log(fit_dts), np.log(errors), 1)
    return OrderFit(
        dts=tuple(fit_dts),
        errors=tuple(errors),
        slope=float(slope),
        intercept=float(intercept),
    )
