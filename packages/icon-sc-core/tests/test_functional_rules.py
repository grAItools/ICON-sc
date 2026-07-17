"""S10: IFT fixed-point rules — rules.py unit tests (both AD modes, L8 shape)."""

from __future__ import annotations

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from symcon.core.functional.rules import implicit_fixed_point, masked_newton_solve  # noqa: E402
from symcon.core.testing import assert_allclose  # noqa: E402


def _sqrt_via_ift(a: jax.Array) -> jax.Array:
    """x with x**2 - a == 0, solved by the masked Newton, differentiated by IFT."""

    def residual(x: jax.Array) -> jax.Array:
        return x * x - a

    def solve(f: object, x0: jax.Array) -> jax.Array:
        return masked_newton_solve(
            residual,
            lambda x: 2.0 * x,
            x0,
            active0=jnp.ones_like(x0, dtype=bool),
            tolerance=1e-14,
            max_iter=60,
        )

    return implicit_fixed_point(residual, jnp.ones_like(a), solve)


def test_primal_and_both_ad_modes_match_analytic() -> None:
    a = jnp.asarray([2.0, 3.0, 9.0, 0.25])
    x = _sqrt_via_ift(a)
    assert_allclose(np.asarray(x), np.sqrt(np.asarray(a)), rtol=1e-12, names="sqrt")

    tangent = jnp.ones_like(a)
    _, jvp = jax.jvp(_sqrt_via_ift, (a,), (tangent,))
    assert_allclose(np.asarray(jvp), 0.5 / np.sqrt(np.asarray(a)), rtol=1e-12, names="jvp")

    grad = jax.grad(lambda a_: jnp.sum(_sqrt_via_ift(a_)))(a)
    assert_allclose(np.asarray(grad), 0.5 / np.sqrt(np.asarray(a)), rtol=1e-12, names="vjp")


def test_adjoint_consistency_through_the_rule() -> None:
    from symcon.core.testing.gradients import dot_product_test

    a = jnp.asarray([1.7, 4.2, 0.9])
    v = jnp.asarray([0.3, -1.1, 0.7])
    w = jnp.asarray([-0.2, 0.5, 1.3])
    assert dot_product_test(_sqrt_via_ift, a, v, w) <= 1e-10


def test_masked_newton_freezes_converged_points() -> None:
    # One point starts inactive: it must come back unchanged.
    a = jnp.asarray([2.0, 3.0])

    def residual(x: jax.Array) -> jax.Array:
        return x * x - a

    x0 = jnp.asarray([1.0, 100.0])
    out = masked_newton_solve(
        residual,
        lambda x: 2.0 * x,
        x0,
        active0=jnp.asarray([True, False]),
        tolerance=1e-14,
        max_iter=60,
    )
    assert_allclose(np.asarray(out[0]), np.sqrt(2.0), rtol=1e-12, names="active point")
    assert float(out[1]) == 100.0  # frozen


def test_masked_newton_is_bounded() -> None:
    # max_iter bounds the loop even when the tolerance is unreachable.
    a = jnp.asarray([2.0])

    def residual(x: jax.Array) -> jax.Array:
        return x * x - a

    out = masked_newton_solve(
        residual,
        lambda x: 2.0 * x,
        jnp.asarray([1.0]),
        active0=jnp.asarray([True]),
        tolerance=0.0,  # never converges
        max_iter=7,
    )
    assert np.isfinite(float(out[0]))
