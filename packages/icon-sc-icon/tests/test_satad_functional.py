"""S10: satad functional core — granule parity + L8 gradients through the IFT rule.

SPEC S10 acceptance 2 (Taylor slope 2.0±0.1 per component) and 3 (dot-product
adjoint consistency ≤ 1e-10 fp64, *including through the satad IFT rule*), plus
the always-on parity guard of the §8.6 pairing (the L2 restatement for satad is
the S07 datatest; here the functional core is held to the embedded granule).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from icon_sc.core import ComputeContext  # noqa: E402
from icon_sc.core.testing import assert_allclose  # noqa: E402
from icon_sc.core.testing.gradients import dot_product_test, taylor_test  # noqa: E402
from icon_sc.icon.components.fast.satad import SaturationAdjustment  # noqa: E402
from icon_sc.icon.grid.vertical import SleveConfig, VerticalGrid  # noqa: E402
from icon_sc.icon.testing import moist_test_column  # noqa: E402

_DT = timedelta(seconds=30)
_NLEV = 65

#: acceptance-3 contract: |⟨Jv,w⟩-⟨v,Jᵀw⟩| / (|⟨Jv,w⟩|+ε) ≤ 1e-10 fp64.
DOT_PRODUCT_TOL = 1.0e-10
#: acceptance-2 contract: Taylor slope 2.0 ± 0.1 over 6 halvings.
TAYLOR_SLOPE = 2.0
TAYLOR_TOL = 0.1


@pytest.fixture(scope="module")
def satad() -> SaturationAdjustment:
    grid = VerticalGrid.from_config(SleveConfig(num_levels=_NLEV))
    return SaturationAdjustment(grid, None, ComputeContext(backend="embedded"), name="satad")


def _column(qv_scale: float, qc: float) -> dict[str, Any]:
    state = moist_test_column("reference_moist", nlev=_NLEV, n_cell=2)
    state["specific_humidity"].data[:] *= qv_scale
    state["specific_cloud_content"].data[:] = qc
    return state


def _inputs(satad: SaturationAdjustment, state: dict[str, Any]) -> dict[str, Any]:
    return {name: np.asarray(state[name].data) for name in satad.input_properties}


@pytest.mark.parametrize(
    ("qv_scale", "qc"),
    [
        pytest.param(2.0, 1.0e-4, id="supersaturated"),
        pytest.param(0.2, 5.0e-5, id="subsaturated-shortcut"),
        pytest.param(1.0, 0.0, id="near-saturation-dry-cloud"),
    ],
)
def test_functional_core_matches_the_granule(
    satad: SaturationAdjustment, qv_scale: float, qc: float
) -> None:
    state = _column(qv_scale, qc)
    _, new_state = satad(state, _DT)
    inputs = _inputs(satad, state)
    out = satad.functional_call(inputs, {}, dt=_DT.total_seconds())
    for name, reference in new_state.items():
        assert_allclose(
            np.asarray(out[name]),
            np.asarray(reference.data),
            rtol=1e-12,
            atol=1e-18,
            names=(f"functional {name}", f"granule {name}"),
        )


def test_moist_domain_masking(satad: SaturationAdjustment) -> None:
    # Above kstart_moist the outputs equal the inputs bitwise (granule domain).
    k0 = int(satad._i4_vertical.kstart_moist)
    assert k0 > 0, "the default S06 grid has a non-trivial moist-domain start"
    inputs = _inputs(satad, _column(2.0, 1.0e-4))
    out = satad.functional_call(inputs, {}, dt=_DT.total_seconds())
    for name in ("air_temperature", "specific_humidity", "specific_cloud_content"):
        np.testing.assert_array_equal(np.asarray(out[name])[:, :k0], inputs[name][:, :k0])


def _f(satad: SaturationAdjustment, inputs: dict[str, Any]) -> Any:
    fixed = {name: jnp.asarray(value) for name, value in inputs.items()}

    def f(x: tuple[Any, Any]) -> tuple[Any, Any, Any]:
        temperature, qv = x
        out = satad.functional_call(
            {**fixed, "air_temperature": temperature, "specific_humidity": qv},
            {},
            dt=_DT.total_seconds(),
        )
        return (
            out["air_temperature"],
            out["specific_humidity"],
            out["specific_cloud_content"],
        )

    return f


def test_taylor_jvp_decay_through_the_ift(satad: SaturationAdjustment) -> None:
    inputs = _inputs(satad, _column(2.0, 1.0e-4))
    f = _f(satad, inputs)
    rng = np.random.default_rng(7)
    x = (jnp.asarray(inputs["air_temperature"]), jnp.asarray(inputs["specific_humidity"]))
    v = (
        jnp.asarray(rng.normal(size=x[0].shape)) * 1e-1,
        jnp.asarray(rng.normal(size=x[1].shape)) * 1e-5,
    )
    result = taylor_test(f, x, v, h0=1e-2, n_halvings=6)
    assert result.slope == pytest.approx(TAYLOR_SLOPE, abs=TAYLOR_TOL), result


def test_dot_product_adjoint_consistency_through_the_ift(satad: SaturationAdjustment) -> None:
    inputs = _inputs(satad, _column(2.0, 1.0e-4))
    f = _f(satad, inputs)
    rng = np.random.default_rng(11)
    x = (jnp.asarray(inputs["air_temperature"]), jnp.asarray(inputs["specific_humidity"]))
    v = (
        jnp.asarray(rng.normal(size=x[0].shape)) * 1e-1,
        jnp.asarray(rng.normal(size=x[1].shape)) * 1e-5,
    )
    w = tuple(jnp.asarray(rng.normal(size=np.shape(out))) for out in f(x))
    assert dot_product_test(f, x, v, w) <= DOT_PRODUCT_TOL


def test_reverse_mode_matches_forward_mode_columnwise(satad: SaturationAdjustment) -> None:
    # grad of a scalar functional == jvp-assembled directional derivatives:
    # both AD modes cross the fixed point through the same implicit rule.
    inputs = _inputs(satad, _column(2.0, 1.0e-4))
    fixed = {name: jnp.asarray(value) for name, value in inputs.items()}

    def scalar(temperature: Any) -> Any:
        out = satad.functional_call(
            {**fixed, "air_temperature": temperature}, {}, dt=_DT.total_seconds()
        )
        return jnp.sum(out["specific_cloud_content"])

    t0 = jnp.asarray(inputs["air_temperature"])
    grad = jax.grad(scalar)(t0)
    _, jvp = jax.jvp(scalar, (t0,), (jnp.ones_like(t0),))
    assert float(jnp.sum(grad)) == pytest.approx(float(jvp), rel=1e-12)
