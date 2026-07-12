"""SPEC S14 acceptance 1 (markers ``data``+``slow``): T0 ≡ T1 on JW, 24 h, bitwise.

Two independently built JW models (the dycore is stateful: each leg owns its
private time levels and carry) advance 24 simulated hours = 288 composed steps
in lockstep — T0 through the composition's interpret semantics, T1 through the
frozen plan — and every prognostic is compared **bitwise** after every step
(same kernels, same order ⇒ bitwise is required, as in S05; AGENTS.md: exact
equality, never allclose). A first-steps closure-vs-composition check ties the
S14 composition to the ``model.step`` closure the S13 L4 cache legs ran.

The gtfn_gpu leg is gpu-marked and skips without a device; embedded is not a
leg (upstream xfails solve_nonhydro on embedded — S12 STATUS deviation 3).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import pytest

from symcon.icon.testing import DATATEST_AVAILABLE

pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
]

PROGNOSTICS = (
    "icon:normal_wind",
    "upward_air_velocity_on_interface_levels",
    "air_density",
    "icon:exner_function",
    "icon:virtual_potential_temperature",
)

BACKENDS = [
    "gtfn_cpu",
    pytest.param("gtfn_gpu", marks=pytest.mark.gpu),
]

SIMULATED_HOURS = 24


def _build(backend: str) -> Any:
    from symcon.icon.presets import JWConfig, build_jw

    return build_jw(JWConfig(backend=backend))


def _host(value: Any) -> np.ndarray:
    array = np.asarray(value.get()) if hasattr(value, "get") else np.asarray(value)
    return array


@pytest.mark.parametrize("backend", BACKENDS)
def test_jw_t0_t1_bitwise_24h(backend: str) -> None:
    """SPEC S14 acceptance 1: 24 simulated hours, bitwise fp64, per backend."""
    t0_model = _build(backend)
    t1_model = _build(backend)
    dt = t0_model.dtime
    n_steps = int(SIMULATED_HOURS * 3600 / dt.total_seconds())
    assert n_steps * dt.total_seconds() == SIMULATED_HOURS * 3600

    # T0 leg: the composition under interpret semantics (what ctx.timeloop
    # tier="interpret" does per step), driven in lockstep with the plan.
    t0_state = dict(t0_model.state)

    # T1 leg: bind once, then run_step on the frozen plan.
    from symcon.core import ExecutionPlan, StateSchema, StateVault

    bind_ctx = dataclasses.replace(t1_model.dycore.ctx, tier="plan", timestep=dt)
    vault = StateVault.from_state(dict(t1_model.state))
    plan = ExecutionPlan.bind(
        t1_model.composition, StateSchema.from_state(t1_model.state), bind_ctx
    )
    facade = vault.facade()

    for index in range(n_steps):
        diagnostics, new_state = t0_model.composition(t0_state, dt)
        t0_state.update(diagnostics)
        t0_state.update(new_state)
        plan.run_step(vault, index)
        for name in PROGNOSTICS:
            np.testing.assert_array_equal(
                _host(facade[name].data),
                _host(t0_state[name].data),
                err_msg=f"T1 diverges from T0 on {name!r} at step {index + 1}",
                strict=True,
            )

    # 24 h of identical trajectories ⇒ identical checkpoint diagnostics too.
    t0_check = t0_model.checkpoint(t0_state)
    t1_check = t1_model.checkpoint({name: facade[name] for name in PROGNOSTICS})
    for key in t0_check:
        np.testing.assert_array_equal(t1_check[key], t0_check[key], err_msg=key, strict=True)


def test_jw_composition_matches_step_closure_first_steps() -> None:
    """The S14 composition and the S13 ``model.step`` closure are the same
    model, bitwise (ties the plan work to the 9-day L4 cache's symcon leg)."""
    closure_model = _build("gtfn_cpu")
    composed_model = _build("gtfn_cpu")
    dt = closure_model.dtime

    closure_state = dict(closure_model.state)
    composed_state = dict(composed_model.state)
    for step in range(2):
        closure_state = closure_model.step(closure_state, dt)
        diagnostics, new_state = composed_model.composition(composed_state, dt)
        composed_state.update(diagnostics)
        composed_state.update(new_state)
        for name in PROGNOSTICS:
            np.testing.assert_array_equal(
                np.asarray(composed_state[name].data),
                np.asarray(closure_state[name].data),
                err_msg=f"composition diverges from closure on {name!r} at step {step + 1}",
                strict=True,
            )
