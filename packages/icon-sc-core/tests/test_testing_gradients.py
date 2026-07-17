"""S10: the L8 harness itself — taylor_test / dot_product_test sanity."""

from __future__ import annotations

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from symcon.core.testing.gradients import (  # noqa: E402
    dot_product_test,
    taylor_test,
    tree_axpy,
    tree_dot,
)


def _f(x: jax.Array) -> jax.Array:
    return jnp.sin(x) * jnp.exp(-0.3 * x**2)


def test_taylor_slope_two_for_correct_jvp() -> None:
    x = jnp.asarray([0.3, -0.7, 1.2])
    v = jnp.asarray([1.0, 0.5, -0.25])
    result = taylor_test(_f, x, v, h0=1e-2, n_halvings=6)
    assert result.slope == pytest.approx(2.0, abs=0.1)
    # slope-1 control: the perturbation registers at all.
    assert all(r > 0 for r in result.increments)


def test_taylor_detects_a_wrong_tangent() -> None:
    # A deliberately wrong custom JVP must break the slope-2 decay.
    @jax.custom_jvp
    def broken(x: jax.Array) -> jax.Array:
        return _f(x)

    @broken.defjvp
    def _broken_jvp(
        primals: tuple[jax.Array], tangents: tuple[jax.Array]
    ) -> tuple[jax.Array, jax.Array]:
        (x,), (dx,) = primals, tangents
        return _f(x), 1.1 * (jnp.cos(x) * jnp.exp(-0.3 * x**2) - 0.6 * x * _f(x)) * dx

    x = jnp.asarray([0.3, -0.7, 1.2])
    v = jnp.asarray([1.0, 0.5, -0.25])
    result = taylor_test(broken, x, v, h0=1e-2, n_halvings=6)
    assert result.slope == pytest.approx(1.0, abs=0.2)  # first-order remainder survives


def test_dot_product_consistency() -> None:
    x = jnp.asarray([[0.3, -0.7], [1.2, 0.1]])
    v = jnp.asarray([[1.0, 0.5], [-0.25, 2.0]])
    w = jnp.asarray([[0.2, -1.5], [0.75, -0.1]])
    assert dot_product_test(_f, x, v, w) <= 1e-12


def test_tree_helpers_over_pytrees() -> None:
    a = {"x": jnp.asarray([1.0, 2.0]), "y": jnp.asarray(3.0)}
    b = {"x": jnp.asarray([4.0, -1.0]), "y": jnp.asarray(2.0)}
    assert float(tree_dot(a, b)) == pytest.approx(1.0 * 4 - 2 + 6)
    summed = tree_axpy(2.0, a, b)
    np.testing.assert_allclose(np.asarray(summed["x"]), [6.0, 3.0])
