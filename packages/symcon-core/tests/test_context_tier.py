"""ComputeContext tier surface + ctx.timeloop (SPEC S05: context gains tier/timeloop)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from _plan_toys import (
    COLUMN_DT,
    assert_states_bitwise_equal,
    make_toy_loop,
    toy_state,
)

from symcon.core import ComputeContext, MemoryMonitor, PlanCompileError


def test_tier_is_validated() -> None:
    assert ComputeContext("embedded").tier == "interpret"
    assert ComputeContext("embedded", tier="plan").tier == "plan"
    with pytest.raises(ValueError, match="tier"):
        ComputeContext("embedded", tier="warp")


def test_timeloop_requires_time_and_exactly_one_extent() -> None:
    ctx = ComputeContext("embedded")
    state = toy_state()
    with pytest.raises(ValueError, match="exactly one"):
        ctx.timeloop(state, make_toy_loop(), timestep=COLUMN_DT)
    with pytest.raises(ValueError, match="exactly one"):
        ctx.timeloop(state, make_toy_loop(), timestep=COLUMN_DT, n_steps=1, until=COLUMN_DT)
    with pytest.raises(ValueError, match="multiple"):
        ctx.timeloop(state, make_toy_loop(), timestep=COLUMN_DT, until=timedelta(seconds=90))
    del state["time"]
    with pytest.raises(KeyError, match="time"):
        ctx.timeloop(state, make_toy_loop(), timestep=COLUMN_DT, n_steps=1)


@pytest.mark.parametrize("tier", ["interpret", "plan"])
def test_timeloop_advances_time_and_feeds_monitors(tier: str) -> None:
    monitor = MemoryMonitor(variables=("air_temperature",))
    ctx = ComputeContext("embedded", tier=tier)
    state = toy_state()
    start = state["time"]
    final = ctx.timeloop(state, make_toy_loop(), timestep=COLUMN_DT, n_steps=3, monitors=(monitor,))
    assert final["time"] == start + 3 * COLUMN_DT
    assert len(monitor.snapshots) == 3
    assert monitor.snapshots[0]["time"] == start + COLUMN_DT


def test_timeloop_until_equals_n_steps() -> None:
    ctx = ComputeContext("embedded", tier="plan")
    by_steps = ctx.timeloop(toy_state(), make_toy_loop(), timestep=COLUMN_DT, n_steps=5)
    by_until = ctx.timeloop(toy_state(), make_toy_loop(), timestep=COLUMN_DT, until=5 * COLUMN_DT)
    assert_states_bitwise_equal(by_steps, by_until)


def test_plan_tier_requires_stepper_shaped_composition() -> None:
    from symcon.core.testing.toys import WindSpeed

    ctx = ComputeContext("embedded", tier="plan")
    with pytest.raises(PlanCompileError, match="Stepper-shaped"):
        ctx.timeloop(toy_state(), WindSpeed(), timestep=COLUMN_DT, n_steps=1)


def test_unknown_wrapper_refuses_plan_compilation() -> None:
    """ComponentWrapper.visit must never silently delegate to the inner component."""
    from symcon.core import ComponentWrapper
    from symcon.core.testing.toys import Damping

    class Mystery(ComponentWrapper):
        def __call__(self, state, timestep, *, out=None):  # type: ignore[no-untyped-def]
            return self._call_component(state, timestep, out)

    ctx = ComputeContext("embedded", tier="plan")
    with pytest.raises(PlanCompileError, match="Mystery"):
        ctx.timeloop(
            toy_state(),
            Mystery(Damping(tau=timedelta(minutes=10))),
            timestep=COLUMN_DT,
            n_steps=1,
        )
