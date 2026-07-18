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

from icon_sc.core import ComputeContext, MemoryMonitor, PlanCompileError


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
    from icon_sc.core.testing.toys import WindSpeed

    ctx = ComputeContext("embedded", tier="plan")
    with pytest.raises(PlanCompileError, match="Stepper-shaped"):
        ctx.timeloop(toy_state(), WindSpeed(), timestep=COLUMN_DT, n_steps=1)


def test_unknown_wrapper_refuses_plan_compilation() -> None:
    """ComponentWrapper.visit must never silently delegate to the inner component."""
    from icon_sc.core import ComponentWrapper
    from icon_sc.core.testing.toys import Damping

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


def test_run_step_yields_to_the_host_callback_at_segment_markers() -> None:
    """S14 host-step seam: ``run_step(..., on_segment=...)`` fires at every
    SegmentMarker — the point where T2 will stop graph replay and return
    control to Python; ``ctx.timeloop`` hangs monitors and time advancement
    off exactly this callback."""
    from icon_sc.core import ExecutionPlan, StateSchema, StateVault

    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    state = toy_state()
    vault = StateVault.from_state(state)
    plan = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(state), ctx)

    markers: list[tuple[str, str]] = []
    for index in range(3):
        plan.run_step(vault, index, on_segment=lambda m: markers.append((m.kind, m.tag)))
    assert markers == [("step_end", "root")] * 3

    # The callback is optional: the default path stays marker-silent.
    plan_quiet = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(state), ctx)
    vault_quiet = StateVault.from_state(toy_state())
    plan_quiet.run_step(vault_quiet, 0)


def test_plan_and_interpret_monitor_series_agree_bitwise() -> None:
    """Monitors run in the step_end host step at T1; the stored series equals
    T0's snapshot-for-snapshot (values and time stamps)."""
    import numpy as np

    series = {}
    for tier in ("interpret", "plan"):
        monitor = MemoryMonitor(variables=("air_temperature", "upward_air_velocity"))
        ctx = ComputeContext("embedded", tier=tier)
        ctx.timeloop(
            toy_state(), make_toy_loop(), timestep=COLUMN_DT, n_steps=4, monitors=(monitor,)
        )
        series[tier] = monitor.snapshots
    assert len(series["interpret"]) == len(series["plan"]) == 4
    for t0_snap, t1_snap in zip(series["interpret"], series["plan"], strict=True):
        assert t0_snap["time"] == t1_snap["time"]
        for name in ("air_temperature", "upward_air_velocity"):
            np.testing.assert_array_equal(
                np.asarray(t1_snap[name].data), np.asarray(t0_snap[name].data), strict=True
            )
