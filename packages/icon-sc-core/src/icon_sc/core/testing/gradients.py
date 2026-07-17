"""L8 gradient-verification harness: Taylor and dot-product tests (SPEC S10, §9-L8).

Generic over PyTrees and reused beyond S10 (P6): ``taylor_test`` measures the
first-order Taylor-remainder decay of ``jax.jvp`` (correct tangents ⇒ slope 2 in
``h``), ``dot_product_test`` measures adjoint consistency
``|⟨Jv,w⟩-⟨v,Jᵀw⟩| / (|⟨Jv,w⟩|+ε)`` between ``jax.jvp`` and ``jax.vjp``.

Lives outside :mod:`icon_sc.core.testing`'s ``__init__`` on purpose: importing
the package stays numpy-only; this module imports jax (fp64 expected — enable
``jax_enable_x64`` before use, PLAN item 6).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import jax
import jax.numpy as jnp
import numpy as np

__all__ = ["TaylorResult", "dot_product_test", "taylor_test", "tree_axpy", "tree_dot"]


def tree_dot(a: Any, b: Any) -> Any:
    """The inner product ⟨a, b⟩ over two same-structure PyTrees (fp64 accumulate)."""
    leaves_a = jax.tree_util.tree_leaves(a)
    leaves_b = jax.tree_util.tree_leaves(b)
    total = jnp.asarray(0.0)
    for la, lb in zip(leaves_a, leaves_b, strict=True):
        total = total + jnp.vdot(jnp.ravel(la), jnp.ravel(lb))
    return total


def tree_axpy(alpha: float, x: Any, y: Any) -> Any:
    """``alpha * x + y`` over two same-structure PyTrees."""
    return jax.tree_util.tree_map(lambda lx, ly: alpha * lx + ly, x, y)


def _tree_norm(x: Any) -> float:
    return float(jnp.sqrt(tree_dot(x, x)))


@dataclasses.dataclass(frozen=True)
class TaylorResult:
    """Outcome of one Taylor-remainder decay measurement."""

    #: Least-squares slope of log2(remainder) vs log2(h) — 2.0 for a correct jvp.
    slope: float
    #: The step sizes tried, largest first.
    steps: tuple[float, ...]
    #: ‖f(x+hv) - f(x) - h·Jv‖ per step.
    remainders: tuple[float, ...]
    #: ‖f(x+hv) - f(x)‖ per step (the slope-1 control: perturbations register).
    increments: tuple[float, ...]


def taylor_test(
    f: Callable[[Any], Any],
    x: Any,
    v: Any,
    *,
    h0: float = 1e-3,
    n_halvings: int = 6,
) -> TaylorResult:
    """First-order Taylor-remainder test of ``jax.jvp`` at ``x`` along ``v`` (L8).

    ``r(h) = ‖f(x + h·v) - f(x) - h·Jv‖`` decays with slope 2 in ``h`` iff the
    tangent ``Jv`` is exact (the slope-1 term cancels). The SPEC contract is
    slope ``2.0 ± 0.1`` over 6 halvings; choose ``h0`` so the smallest remainder
    stays above the fp64 noise floor.
    """
    fx, jv = jax.jvp(f, (x,), (v,))
    steps: list[float] = []
    remainders: list[float] = []
    increments: list[float] = []
    for k in range(n_halvings):
        h = h0 / (2.0**k)
        fxh = f(tree_axpy(h, v, x))
        increment = tree_axpy(-1.0, fx, fxh)  # f(x+hv) - f(x)
        remainder = tree_axpy(-h, jv, increment)
        steps.append(h)
        remainders.append(_tree_norm(remainder))
        increments.append(_tree_norm(increment))
    log_h = np.log2(np.asarray(steps))
    log_r = np.log2(np.maximum(np.asarray(remainders), np.finfo(np.float64).tiny))
    slope = float(np.polyfit(log_h, log_r, 1)[0])
    return TaylorResult(
        slope=slope,
        steps=tuple(steps),
        remainders=tuple(remainders),
        increments=tuple(increments),
    )


def dot_product_test(
    f: Callable[[Any], Any],
    x: Any,
    v: Any,
    w: Any,
    *,
    eps: float = 1e-300,
) -> float:
    """Adjoint-consistency (dot-product) test: ``|⟨Jv,w⟩-⟨v,Jᵀw⟩|/(|⟨Jv,w⟩|+ε)`` (L8).

    ``v`` has the structure of ``x`` (input tangent), ``w`` the structure of
    ``f(x)`` (output cotangent). fp64 contract: ≤ 1e-10 per SPEC S10.
    """
    _, jv = jax.jvp(f, (x,), (v,))
    _, vjp_fn = jax.vjp(f, x)
    (jtw,) = vjp_fn(w)
    forward = tree_dot(jv, w)
    reverse = tree_dot(v, jtw)
    return float(jnp.abs(forward - reverse) / (jnp.abs(forward) + eps))
