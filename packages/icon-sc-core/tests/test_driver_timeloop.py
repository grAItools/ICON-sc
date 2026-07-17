"""T0 timeloop helper tests (SPEC S03)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import pytest

from icon_sc.core import Monitor, timeloop
from icon_sc.core.testing.toys import column_state
from icon_sc.core.time import datetime

DT = timedelta(minutes=5)


class RecordingMonitor(Monitor):
    def __init__(self) -> None:
        super().__init__()
        self.times: list[Any] = []

    def store(self, state: Mapping[str, Any]) -> None:
        self.times.append(state["time"])


def _identity(state: dict[str, Any], timestep: timedelta) -> dict[str, Any]:
    return state


def test_advances_time_and_calls_monitors_each_step() -> None:
    monitor = RecordingMonitor()
    state = column_state()
    final = timeloop(state, _identity, timestep=DT, n_steps=3, monitors=(monitor,))
    t0 = datetime(2000, 1, 1)
    assert monitor.times == [t0 + DT, t0 + 2 * DT, t0 + 3 * DT]
    assert final["time"] == t0 + 3 * DT
    # the input state mapping is not mutated
    assert state["time"] == t0


def test_step_function_sees_the_pre_advance_time() -> None:
    seen: list[Any] = []

    def step(state: dict[str, Any], timestep: timedelta) -> dict[str, Any]:
        seen.append(state["time"])
        return state

    timeloop(column_state(), step, timestep=DT, n_steps=2)
    t0 = datetime(2000, 1, 1)
    assert seen == [t0, t0 + DT]


def test_until_must_be_exact_multiple() -> None:
    state = column_state()
    final = timeloop(state, _identity, timestep=DT, until=timedelta(minutes=15))
    assert final["time"] == datetime(2000, 1, 1) + timedelta(minutes=15)
    with pytest.raises(ValueError, match="integer multiple"):
        timeloop(state, _identity, timestep=DT, until=timedelta(minutes=7))


def test_argument_validation() -> None:
    state = column_state()
    with pytest.raises(ValueError, match="exactly one"):
        timeloop(state, _identity, timestep=DT)
    with pytest.raises(ValueError, match="exactly one"):
        timeloop(state, _identity, timestep=DT, n_steps=1, until=DT)
    with pytest.raises(ValueError, match="positive"):
        timeloop(state, _identity, timestep=timedelta(0), n_steps=1)
    with pytest.raises(ValueError, match="non-negative"):
        timeloop(state, _identity, timestep=DT, n_steps=-1)
    with pytest.raises(KeyError, match="time"):
        timeloop({}, _identity, timestep=DT, n_steps=1)
