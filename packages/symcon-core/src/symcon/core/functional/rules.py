"""Implicit-function-theorem rules for fixed points (§8.6 ``custom`` route, SPEC S10).

Implicit structure gets IFT treatment rather than unrolling: the fixed point
differentiates through a ``lax.custom_root``-style rule, not through recorded
Newton iterations — which also sidesteps ``while_loop``'s reverse-mode
prohibition (the solver runs inside ``custom_root``'s non-differentiated primal).

Verified on the pinned jax (REFERENCES.lock ``jax``): ``lax.custom_root`` with a
linear elementwise ``tangent_solve`` supports **both** ``jvp`` and ``vjp``
(reverse mode derives from the JVP by transposition), with a bounded
``lax.while_loop`` inside ``solve``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import jax
import jax.numpy as jnp

__all__ = ["implicit_fixed_point", "masked_newton_solve"]

#: An elementwise array function (residual, solver, ...): arrays in, arrays out.
ArrayFn = Callable[..., Any]


def implicit_fixed_point(residual: ArrayFn, x0: Any, solve: Callable[[ArrayFn, Any], Any]) -> Any:
    """Solve ``residual(x) == 0`` elementwise; differentiate via the IFT (§8.6).

    ``residual`` must be **elementwise** in ``x`` (its Jacobian at the solution
    is diagonal): the linearized-residual solve is then ``y / g(1)``, which is
    linear — exactly what ``lax.custom_root`` needs to derive both the JVP and,
    by transposition, the VJP. Everything ``residual`` closes over is
    differentiated through the implicit function; ``solve`` is primal-only and
    may use ``lax.while_loop``.
    """

    def tangent_solve(g: ArrayFn, y: Any) -> Any:
        return y / g(jnp.ones_like(y))

    return jax.lax.custom_root(residual, x0, solve, tangent_solve)


def masked_newton_solve(
    residual: ArrayFn,
    residual_prime: ArrayFn,
    x0: Any,
    *,
    active0: Any,
    tolerance: float,
    max_iter: int,
) -> Any:
    """Elementwise Newton with per-point convergence freeze (primal-only solver).

    Mirrors the granule-style masked iteration (icon4py satad, REFERENCES.lock
    ``icon4py-satad-stencils``): points update only while their mask is active;
    the mask deactivates when ``|Δx| <= tolerance``; the global loop runs while
    any point is active, bounded by ``max_iter`` (a data-dependent raise is not
    expressible under ``jit`` — the T0 granule raises ``ConvergenceError``
    instead; deviation recorded in STATUS S10). Meant to be passed as the
    ``solve`` of :func:`implicit_fixed_point`, so its iterations are never
    differentiated.
    """

    def cond(carry: tuple[Any, Any, Any]) -> Any:
        _, active, count = carry
        return jnp.logical_and(jnp.any(active), count < max_iter)

    def body(carry: tuple[Any, Any, Any]) -> tuple[Any, Any, Any]:
        x, active, count = carry
        x_new = jnp.where(active, x - residual(x) / residual_prime(x), x)
        active_new = jnp.abs(x_new - x) > tolerance
        return x_new, active_new, count + 1

    x_final, _, _ = jax.lax.while_loop(cond, body, (x0, active0, jnp.asarray(0)))
    return x_final
