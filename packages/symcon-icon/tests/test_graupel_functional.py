"""S10: graupel functional core — granule parity battery + L8 component gradients.

The always-on guard of the §8.6 native pairing: the JAX core against the
embedded granule on synthetic hydrometeor columns walking the warm/cold/melting
branches (the acceptance-1 gate against the **gtfn kernel on the S08 reference
data** lives in ``test_graupel_functional_datatest.py``, marker ``data``), plus
acceptance 2/3 per component: Taylor slope 2.0±0.1 and dot-product ≤ 1e-10.
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from symcon.core import ComputeContext  # noqa: E402
from symcon.core.testing import assert_allclose  # noqa: E402
from symcon.core.testing.gradients import dot_product_test, taylor_test  # noqa: E402
from symcon.icon.components.fast.graupel_constants import GRAUPEL_QMIN  # noqa: E402
from symcon.icon.components.fast.microphysics import Graupel, Microphysics  # noqa: E402
from symcon.icon.grid.vertical import SleveConfig, VerticalGrid  # noqa: E402

from _functional_columns import PROGNOSTICS, RATES, hydrometeor_column  # noqa: E402

_DT = timedelta(seconds=30)
_NLEV = 65

#: Parity of the two implementations of one scheme (§11.8): the SPEC-1 relative
#: tolerance, with an absolute floor at the scheme's own lowest detectable
#: mixing ratio (QMIN = 1e-15; differences below it are sub-detectability noise
#: on physically-zero points — justification in STATUS S10).
PARITY_RTOL = 1.0e-10
PARITY_ATOL = GRAUPEL_QMIN

DOT_PRODUCT_TOL = 1.0e-10
TAYLOR_SLOPE = 2.0
TAYLOR_TOL = 0.1


@pytest.fixture(scope="module")
def graupel() -> Graupel:
    grid = VerticalGrid.from_config(SleveConfig(num_levels=_NLEV))
    component = Microphysics(
        grid, None, ComputeContext(backend="embedded"), scheme="graupel", name="mphys"
    )
    assert isinstance(component, Graupel)
    return component


def _inputs(graupel: Graupel, state: dict[str, Any]) -> dict[str, Any]:
    return {name: np.asarray(state[name].data) for name in graupel.input_properties}


@pytest.mark.parametrize(
    ("qv_scale", "seed"),
    [
        pytest.param(1.5, 42, id="moist-hydrometeors"),
        pytest.param(0.5, 3, id="subsaturated-hydrometeors"),
        pytest.param(2.0, 9, id="supersaturated-hydrometeors"),
    ],
)
def test_functional_core_matches_the_granule(graupel: Graupel, qv_scale: float, seed: int) -> None:
    state = hydrometeor_column(_NLEV, 2, qv_scale=qv_scale, seed=seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # icon4py embedded-execution warnings
        diagnostics, new_state = graupel(state, _DT)
    reference = {name: np.asarray(array.data) for name, array in new_state.items()}
    reference.update({name: np.asarray(array.data) for name, array in diagnostics.items()})

    out = graupel.functional_call(
        _inputs(graupel, state), dict(graupel.functional_params()), dt=_DT.total_seconds()
    )
    for name in (*PROGNOSTICS, *RATES):
        assert_allclose(
            np.asarray(out[name]),
            reference[name],
            rtol=PARITY_RTOL,
            atol=PARITY_ATOL,
            names=(f"functional {name}", f"granule {name}"),
        )


def test_no_hydrometeors_is_a_fixed_point_with_zero_rates(graupel: Graupel) -> None:
    state = hydrometeor_column(_NLEV, 2, qv_scale=0.0, seed=1)
    for name in PROGNOSTICS[1:]:
        state[name].data[:] = 0.0
    inputs = _inputs(graupel, state)
    out = graupel.functional_call(
        inputs, dict(graupel.functional_params()), dt=_DT.total_seconds()
    )
    for name in PROGNOSTICS:
        np.testing.assert_array_equal(np.asarray(out[name]), inputs[name])
    for name in RATES:
        np.testing.assert_array_equal(np.asarray(out[name]), 0.0)


def test_moist_domain_masking(graupel: Graupel) -> None:
    k0 = int(graupel._i4_vertical.kstart_moist)
    assert k0 > 0
    inputs = _inputs(graupel, hydrometeor_column(_NLEV, 2))
    out = graupel.functional_call(
        inputs, dict(graupel.functional_params()), dt=_DT.total_seconds()
    )
    for name in PROGNOSTICS:
        np.testing.assert_array_equal(np.asarray(out[name])[:, :k0], inputs[name][:, :k0])


def test_declared_spec_params_are_provided(graupel: Graupel) -> None:
    declared = {
        param
        for dict_name in graupel.output_dict_names
        for spec in graupel.parsed_properties.get(dict_name, {}).values()
        for param in spec.params
    }
    assert declared == {"kcau", "kcac"}
    assert declared <= set(graupel.functional_params())


def _f(graupel: Graupel, inputs: dict[str, Any]) -> Any:
    fixed = {name: jnp.asarray(value) for name, value in inputs.items()}
    params = {name: jnp.asarray(value) for name, value in graupel.functional_params().items()}

    def f(x: tuple[Any, Any]) -> tuple[Any, ...]:
        temperature, qv = x
        out = graupel.functional_call(
            {**fixed, "air_temperature": temperature, "specific_humidity": qv},
            params,
            dt=_DT.total_seconds(),
        )
        return tuple(out[name] for name in (*PROGNOSTICS, *RATES))

    return f


def test_taylor_jvp_decay(graupel: Graupel) -> None:
    inputs = _inputs(graupel, hydrometeor_column(_NLEV, 2))
    f = _f(graupel, inputs)
    rng = np.random.default_rng(7)
    x = (jnp.asarray(inputs["air_temperature"]), jnp.asarray(inputs["specific_humidity"]))
    v = (
        jnp.asarray(rng.normal(size=x[0].shape)) * 1e-1,
        jnp.asarray(rng.normal(size=x[1].shape)) * 1e-5,
    )
    result = taylor_test(f, x, v, h0=1e-2, n_halvings=6)
    assert result.slope == pytest.approx(TAYLOR_SLOPE, abs=TAYLOR_TOL), result


def test_dot_product_adjoint_consistency(graupel: Graupel) -> None:
    inputs = _inputs(graupel, hydrometeor_column(_NLEV, 2))
    f = _f(graupel, inputs)
    rng = np.random.default_rng(11)
    x = (jnp.asarray(inputs["air_temperature"]), jnp.asarray(inputs["specific_humidity"]))
    v = (
        jnp.asarray(rng.normal(size=x[0].shape)) * 1e-1,
        jnp.asarray(rng.normal(size=x[1].shape)) * 1e-5,
    )
    w = tuple(jnp.asarray(rng.normal(size=np.shape(out))) for out in f(x))
    assert dot_product_test(f, x, v, w) <= DOT_PRODUCT_TOL


def test_param_gradients_are_finite_and_autoconversion_reacts(graupel: Graupel) -> None:
    inputs = {
        name: jnp.asarray(value)
        for name, value in _inputs(graupel, hydrometeor_column(_NLEV, 2)).items()
    }

    def rain(params: dict[str, Any]) -> Any:
        out = graupel.functional_call(inputs, params, dt=_DT.total_seconds())
        return jnp.sum(out["specific_rain_content"])

    params0 = {name: jnp.asarray(value) for name, value in graupel.functional_params().items()}
    grads = jax.grad(rain)(params0)
    assert all(bool(jnp.isfinite(value)) for value in grads.values())
    # More autoconversion kernel -> more rain (the sign every textbook expects).
    assert float(grads["kcau"]) > 0.0
