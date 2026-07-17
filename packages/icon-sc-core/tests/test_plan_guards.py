"""SPEC S05 acceptance 5: staleness guards and debug renegotiation.

Mutating the façade between steps raises ``StalePlanError`` on the next
``run_step``; debug renegotiate-and-diff passes on the toys and detects a
composition that drifted from the bound plan.
"""

from __future__ import annotations

import numpy as np
import pytest
from _plan_toys import (
    COLUMN_DT,
    TAU_DAMP,
    assert_states_bitwise_equal,
    make_toy_loop,
    run_tier,
    toy_state,
)

from icon_sc.core import (
    ComputeContext,
    ExecutionPlan,
    PlanCompileError,
    PlanDriftError,
    StateSchema,
    StateVault,
    renegotiate_and_diff,
)
from icon_sc.core.plan.guards import StalePlanError
from icon_sc.core.state.dataarray import make_dataarray


def _bound_plan() -> tuple[ExecutionPlan, StateVault]:
    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    state = toy_state()
    vault = StateVault.from_state(state)
    plan = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(state), ctx)
    plan.run_step(vault, 0)
    return plan, vault


def test_facade_rebind_raises_stale_plan_error() -> None:
    plan, vault = _bound_plan()
    facade = vault.facade()
    replacement = make_dataarray(
        np.zeros_like(np.asarray(facade["air_temperature"].data)),
        name="air_temperature",
        dims=["cell", "height"],
        units="K",
        location="cell",
    )
    facade["air_temperature"] = replacement  # out-of-band mutation: epoch bump
    with pytest.raises(StalePlanError):
        plan.run_step(vault, 1)


def test_facade_new_field_raises_stale_plan_error() -> None:
    plan, vault = _bound_plan()
    facade = vault.facade()
    facade["surprise"] = make_dataarray(
        np.zeros((1, 10)), name="surprise", dims=["cell", "height"], units="1", location="cell"
    )
    with pytest.raises(StalePlanError):
        plan.run_step(vault, 1)


def test_facade_delete_raises_stale_plan_error() -> None:
    plan, vault = _bound_plan()
    facade = vault.facade()
    del facade["wind_speed"]
    with pytest.raises(StalePlanError):
        plan.run_step(vault, 1)


def test_in_place_buffer_writes_do_not_stale_the_plan() -> None:
    """Value mutation preserves buffer identity: legal, plan stays valid (§8.2)."""
    plan, vault = _bound_plan()
    facade = vault.facade()
    facade["air_temperature"].data[...] += 1.0
    plan.run_step(vault, 1)  # no raise


def test_non_sequential_step_index_is_rejected() -> None:
    plan, vault = _bound_plan()  # ran step 0; expects step_index % 2 == 1 next
    with pytest.raises(StalePlanError, match="sequential"):
        plan.run_step(vault, 2)


def test_debug_renegotiation_passes_on_the_toys() -> None:
    t0 = run_tier("interpret", make_toy_loop, toy_state(), timestep=COLUMN_DT, n_steps=20)
    ctx = ComputeContext("embedded", tier="plan")
    t1 = ctx.timeloop(
        toy_state(),
        make_toy_loop(),
        timestep=COLUMN_DT,
        n_steps=20,
        debug_renegotiate_every=5,
    )
    assert_states_bitwise_equal(t0, t1)


def test_debug_renegotiation_detects_drift() -> None:
    from icon_sc.core import Subcycle
    from icon_sc.core.testing.toys import Damping

    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    schema = StateSchema.from_state(toy_state())
    plan = ExecutionPlan.bind(make_toy_loop(), schema, ctx)
    drifted = Subcycle(Damping(tau=TAU_DAMP), n=2)  # a different composition
    with pytest.raises(PlanDriftError):
        renegotiate_and_diff(plan, drifted, ctx)


def test_bind_requires_a_timestep() -> None:
    ctx = ComputeContext("embedded", tier="plan")  # no timestep stamped
    with pytest.raises(PlanCompileError, match="timestep"):
        ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(toy_state()), ctx)


def test_vault_mismatch_is_rejected() -> None:
    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    plan = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(toy_state()), ctx)
    smaller = toy_state()
    del smaller["northward_wind"]
    vault = StateVault.from_state(smaller)
    with pytest.raises(StalePlanError, match="northward_wind"):
        plan.run_step(vault, 0)
