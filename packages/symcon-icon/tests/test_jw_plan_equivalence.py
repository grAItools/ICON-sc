"""SPEC S14 acceptance 1 (markers ``data``+``slow``): T0 ≡ T1 on JW, 24 h, bitwise.

Two independently built JW models (the dycore is stateful: each leg owns its
private time levels and carry) advance 24 simulated hours = 288 composed steps
in lockstep — T0 through the composition's interpret semantics, T1 through the
frozen plan — and every prognostic is compared **bitwise** after every step
(same kernels, same order ⇒ bitwise is required, as in S05; AGENTS.md: exact
equality, never allclose). A first-steps closure-vs-composition check ties the
S14 composition to the ``model.step`` closure the S13 L4 cache legs ran.

**Chunked execution** (the S13 ``make_reference.py`` pattern): schedulers with
wall-time caps can split the 24 h across invocations —
``SYMCON_S14_EQUIV_HOURS`` (simulated hours per invocation) +
``SYMCON_S14_EQUIV_STATE`` (resume directory). Resume goes through the S12/S13
component restart protocols (bitwise, SPEC S12 acceptance 3) plus the boundary
prognostics, per leg; every chunk re-asserts lockstep bitwise equality at each
step, and the final chunk closes with the checkpoint-diagnostics comparison.
Without the env vars (CI default) the full 24 h run in one invocation.

The gtfn_gpu leg is gpu-marked and skips without a device; embedded is not a
leg (upstream xfails solve_nonhydro on embedded — S12 STATUS deviation 3).
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
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
HOURS_ENV = "SYMCON_S14_EQUIV_HOURS"
STATE_ENV = "SYMCON_S14_EQUIV_STATE"


def _build(backend: str) -> Any:
    from symcon.icon.presets import JWConfig, build_jw

    return build_jw(JWConfig(backend=backend))


def _host(value: Any) -> np.ndarray:
    return np.asarray(value.get()) if hasattr(value, "get") else np.asarray(value)


def _restore_leg(model: Any, state: dict[str, Any], data: Any, prefix: str) -> None:
    """One leg's resume: boundary prognostics + both components' private state."""
    for name in PROGNOSTICS:
        state[name].data[...] = data[f"{prefix}::st::{name}"]
    for tag, component in (("dyc", model.dycore), ("dif", model.diffusion)):
        blob = component.restart_state()
        for key in blob:
            blob[key].data[...] = data[f"{prefix}::{tag}::{key}"]
        component.load_restart_state(blob)


def _save_leg(model: Any, state: dict[str, Any], prefix: str) -> dict[str, np.ndarray]:
    payload: dict[str, np.ndarray] = {}
    for name in PROGNOSTICS:
        payload[f"{prefix}::st::{name}"] = _host(state[name].data)
    for tag, component in (("dyc", model.dycore), ("dif", model.diffusion)):
        for key, array in component.restart_state().items():
            payload[f"{prefix}::{tag}::{key}"] = np.asarray(array.data)
    return payload


@pytest.mark.parametrize("backend", BACKENDS)
def test_jw_t0_t1_bitwise_24h(backend: str) -> None:
    """SPEC S14 acceptance 1: 24 simulated hours, bitwise fp64, per backend."""
    t0_model = _build(backend)
    t1_model = _build(backend)
    dt = t0_model.dtime
    n_total = int(SIMULATED_HOURS * 3600 / dt.total_seconds())
    assert n_total * dt.total_seconds() == SIMULATED_HOURS * 3600

    hours_this = float(os.environ.get(HOURS_ENV, str(SIMULATED_HOURS)))
    n_this = int(hours_this * 3600 / dt.total_seconds())
    assert n_this * dt.total_seconds() == hours_this * 3600, "chunk hours must divide by Δt"
    state_dir = os.environ.get(STATE_ENV)
    resume_path = (
        pathlib.Path(state_dir) / f"s14_equiv_{backend}.npz" if state_dir is not None else None
    )

    t0_state = dict(t0_model.state)
    t1_state = dict(t1_model.state)
    done_steps = 0
    if resume_path is not None and resume_path.exists():
        with np.load(resume_path) as data:
            done_steps = int(data["done_steps"])
            _restore_leg(t0_model, t0_state, data, "t0")
            _restore_leg(t1_model, t1_state, data, "t1")

    # T1 leg: bind against the (possibly resumed) state; a fresh vault holds
    # every live value in its canonical cell, so the plan starts at phase 0
    # regardless of the resumed trajectory position.
    from symcon.core import ExecutionPlan, StateSchema, StateVault

    bind_ctx = dataclasses.replace(t1_model.dycore.ctx, tier="plan", timestep=dt)
    vault = StateVault.from_state(t1_state)
    plan = ExecutionPlan.bind(t1_model.composition, StateSchema.from_state(t1_state), bind_ctx)
    facade = vault.facade()

    n_steps = min(n_this, n_total - done_steps)
    assert n_steps > 0, "the 24 h trajectory is already complete; remove the resume file"
    for index in range(n_steps):
        diagnostics, new_state = t0_model.composition(t0_state, dt)
        t0_state.update(diagnostics)
        t0_state.update(new_state)
        plan.run_step(vault, index)
        for name in PROGNOSTICS:
            np.testing.assert_array_equal(
                _host(facade[name].data),
                _host(t0_state[name].data),
                err_msg=f"T1 diverges from T0 on {name!r} at step {done_steps + index + 1}",
                strict=True,
            )

    done_steps += n_steps
    if done_steps < n_total:
        assert resume_path is not None  # only the chunked mode can stop early
        payload = {"done_steps": np.asarray(done_steps)}
        payload.update(_save_leg(t0_model, t0_state, "t0"))
        t1_full = dict(t1_state)
        t1_full.update({name: facade[name] for name in PROGNOSTICS})
        payload.update(_save_leg(t1_model, t1_full, "t1"))
        np.savez(resume_path, **payload)
        return

    # 24 h of identical trajectories ⇒ identical checkpoint diagnostics too.
    t0_check = t0_model.checkpoint(t0_state)
    t1_check = t1_model.checkpoint({name: facade[name] for name in PROGNOSTICS})
    for key in t0_check:
        np.testing.assert_array_equal(t1_check[key], t0_check[key], err_msg=key, strict=True)
    if resume_path is not None:
        resume_path.unlink(missing_ok=True)


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
