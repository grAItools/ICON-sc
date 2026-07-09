"""SPEC S05 acceptance 2: even/odd correctness — an odd step count (101) matches T0.

The toy-loop composition ping-pongs ``upward_air_velocity`` (Damping is a bare
Stepper: kernel-written output, §8.2 slot swap), so the plan has two variants
and 101 steps end on the *alternate* buffer; the façade must still expose the
current data.
"""

from __future__ import annotations

from _plan_toys import (
    COLUMN_DT,
    assert_states_bitwise_equal,
    make_cf_subcycle_composite,
    make_toy_loop,
    run_tier,
    toy_state,
)

from symcon.core import ComputeContext, ExecutionPlan, StateSchema, StateVault


def test_odd_step_count_matches_t0_bitwise() -> None:
    t0 = run_tier("interpret", make_toy_loop, toy_state(), timestep=COLUMN_DT, n_steps=101)
    t1 = run_tier("plan", make_toy_loop, toy_state(), timestep=COLUMN_DT, n_steps=101)
    assert_states_bitwise_equal(t0, t1)


def test_odd_step_count_with_cadence_matches_t0_bitwise() -> None:
    t0 = run_tier(
        "interpret", make_cf_subcycle_composite, toy_state(), timestep=COLUMN_DT, n_steps=101
    )
    t1 = run_tier("plan", make_cf_subcycle_composite, toy_state(), timestep=COLUMN_DT, n_steps=101)
    assert_states_bitwise_equal(t0, t1)


def test_plan_emits_two_variants_and_swap_keeps_facade_coherent() -> None:
    """The swap variant machinery: 2 signatures; façade tracks the live buffer."""
    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    state = toy_state()
    vault = StateVault.from_state(state)
    plan = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(state), ctx)
    assert len(plan.signatures) == 2
    assert "swap" in plan.describe()

    facade = vault.facade()
    plan.run_step(vault, 0)
    after_one = facade["upward_air_velocity"].data.copy()
    plan.run_step(vault, 1)
    after_two = facade["upward_air_velocity"].data
    # Damping is a strict contraction: consecutive façade reads must differ
    # (a stale ping-pong view would repeat the previous step's values).
    assert (after_two < after_one).all()
