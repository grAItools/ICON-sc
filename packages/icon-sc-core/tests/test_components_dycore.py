"""DynamicalCore tier orchestration (SPEC S04 acceptance 4, Fig. 3.9/3.10).

A recording toy core (2-stage, ``substep_fraction = 1/3``, ``substeps = 6``)
asserts the exact hook-invocation order, that slow-port tendencies are held
constant across stages, and that the per-stage fast coupling fires once per
stage. A 3-stage variant reproduces the Fig. 3.10 substep counts (2, 3, 6).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest

from icon_sc.core.components.base import TendencyComponent
from icon_sc.core.components.dycore import DynamicalCore
from icon_sc.core.coupling import ConcurrentCoupling
from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.testing import assert_allclose
from icon_sc.core.time import datetime

_DIMS = ["cell", "height"]
DT = timedelta(seconds=6)
SLOT = "tendency_of_eastward_wind"
FAST_RATE = 0.25  # constant fast tendency [m s-2]


def core_state(u0: float = 10.0, slow: float = 2.0) -> dict[str, Any]:
    def field(name: str, value: float, units: str) -> Any:
        return make_dataarray(
            np.full((1, 1), value, dtype=np.float64),
            name=name,
            dims=_DIMS,
            units=units,
            location="cell",
        )

    return {
        "time": datetime(2000, 1, 1),
        "eastward_wind": field("eastward_wind", u0, "m s-1"),
        SLOT: field(SLOT, slow, "m s-2"),
    }


class RecordingFast(TendencyComponent):
    """Constant fast tendency; records each invocation and the state it saw."""

    input_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    tendency_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-2"},
    }

    def __init__(self, events: list[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._events = events

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        self._events.append(("fast", float(np.asarray(inputs["eastward_wind"])[0, 0])))
        outputs["eastward_wind"][...] = FAST_RATE


class RecordingCore(DynamicalCore):
    """2-stage toy: stage = identity, substep = +1; records every hook call."""

    n_stages: ClassVar[int] = 2
    substep_fraction: ClassVar[float | tuple[float, ...]] = 1.0 / 3.0
    input_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        SLOT: {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    tendency_port: ClassVar[dict[str, str]] = {"eastward_wind": SLOT}

    def __init__(self, events: list[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._events = events

    def stage_array_call(
        self,
        stage: int,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        dt: timedelta,
    ) -> None:
        self._events.append(
            (
                "stage",
                stage,
                float(np.asarray(inputs[SLOT])[0, 0]),  # combined slow+fast value
                dt.total_seconds(),
            )
        )
        outputs["eastward_wind"][...] = inputs["eastward_wind"]

    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        dt: timedelta,
    ) -> None:
        assert "stage/eastward_wind" in inputs  # the enclosing stage's output
        self._events.append(("substep", stage, substep, dt.total_seconds()))
        outputs["eastward_wind"][...] = np.asarray(inputs["eastward_wind"]) + 1.0


def test_fig_3_10_call_sequence_with_fast_coupling() -> None:
    """Acceptance 4: exact hook order; fast once per stage; slow port constant."""
    events: list[Any] = []
    core = RecordingCore(
        events,
        fast_tendency_component=ConcurrentCoupling([RecordingFast(events)]),
        substeps=6,
    )
    state = core_state(u0=10.0, slow=2.0)
    diagnostics, new_state = core(state, DT)
    assert diagnostics == {}

    kinds = [event[0] for event in events]
    assert kinds == [
        "fast",
        "stage",
        "substep",
        "substep",  # stage 0: round(6/3) = 2 substeps
        "fast",
        "stage",
        "substep",
        "substep",  # stage 1
    ]
    stage_events = [event for event in events if event[0] == "stage"]
    # Slow-port tendencies held constant across stages: both stages saw
    # slow + fast = 2.0 + 0.25, and the state's slot buffer is untouched.
    assert stage_events[0][2] == pytest.approx(2.0 + FAST_RATE)
    assert stage_events[1][2] == pytest.approx(2.0 + FAST_RATE)
    assert float(state[SLOT].data[0, 0]) == 2.0
    # Stage hooks receive the full Δt; substep hooks Δt/N.
    assert all(event[3] == 6.0 for event in stage_events)
    assert all(event[3] == 1.0 for event in events if event[0] == "substep")
    # Substeps chain: identity stages + two "+1" substeps per stage -> ψⁿ + 4.
    assert_allclose(new_state["eastward_wind"].data, 10.0 + 4.0, rtol=0.0, names="substep chaining")
    # The fast coupling saw the latest provisional state: ψⁿ, then ψⁿ + 2.
    fast_events = [event for event in events if event[0] == "fast"]
    assert fast_events[0][1] == pytest.approx(10.0)
    assert fast_events[1][1] == pytest.approx(12.0)


def test_slow_port_passthrough_without_fast_coupling() -> None:
    events: list[Any] = []
    core = RecordingCore(events)
    state = core_state(u0=1.0, slow=3.5)
    _, new_state = core(state, DT)
    kinds = [event[0] for event in events]
    assert kinds == ["stage", "stage"]  # substep tier disabled (substeps=0)
    assert all(event[2] == pytest.approx(3.5) for event in events)
    assert float(state[SLOT].data[0, 0]) == 3.5
    assert_allclose(new_state["eastward_wind"].data, 1.0, rtol=0.0, names="identity core")


def test_fig_3_10_substep_counts_on_three_stage_core() -> None:
    """The Fig. 3.10 example: fractions (1/3, 1/2, 1), N=6 -> 2, 3, 6 substeps."""
    events: list[Any] = []

    class WS3Core(RecordingCore):
        n_stages: ClassVar[int] = 3
        substep_fraction: ClassVar[float | tuple[float, ...]] = (1.0 / 3.0, 0.5, 1.0)

    core = WS3Core(events, substeps=6)
    core(core_state(), DT)
    counts = [
        sum(1 for event in events if event[0] == "substep" and event[1] == stage)
        for stage in range(3)
    ]
    assert counts == [2, 3, 6]
    assert all(event[3] == 1.0 for event in events if event[0] == "substep")


def test_ratio_provider_is_called_once_per_step() -> None:
    events: list[Any] = []
    calls: list[Any] = []

    def provider(state: Any) -> int:
        calls.append(state["time"])
        return 3

    core = RecordingCore(events, ratio_provider=provider)
    state = core_state()
    core(state, DT)
    assert len(calls) == 1
    # N=3, fraction 1/3 -> one substep per stage.
    kinds = [event[0] for event in events]
    assert kinds == ["stage", "substep", "stage", "substep"]
    with pytest.raises(ValueError, match="need >= 1"):
        RecordingCore(events, ratio_provider=lambda _state: 0)(state, DT)


def test_constructor_validation() -> None:
    events: list[Any] = []
    with pytest.raises(ValueError, match="at most one of substeps and ratio_provider"):
        RecordingCore(events, substeps=2, ratio_provider=lambda _state: 2)
    with pytest.raises(ValueError, match="substeps must be >= 0"):
        RecordingCore(events, substeps=-1)

    class BadFractions(RecordingCore):
        substep_fraction: ClassVar[float | tuple[float, ...]] = (0.5,)

    with pytest.raises(ValueError, match="substep_fraction has 1 entries for 2 stages"):
        BadFractions(events)

    class NotAnInput(RecordingCore):
        input_properties: ClassVar[dict[str, Any]] = {
            SLOT: {"dims": _DIMS, "units": "m s-2"},
        }

    with pytest.raises(ValueError, match="reads what it steps"):
        NotAnInput(events)

    class SlotNotAnInput(RecordingCore):
        input_properties: ClassVar[dict[str, Any]] = {
            "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        }

    with pytest.raises(ValueError, match="the slow port is an input port"):
        SlotNotAnInput(events)


def test_fast_tendency_without_port_slot_rejects() -> None:
    events: list[Any] = []

    class NorthFast(RecordingFast):
        input_properties: ClassVar[dict[str, Any]] = {
            "northward_wind": {"dims": _DIMS, "units": "m s-1"},
        }
        tendency_properties: ClassVar[dict[str, Any]] = {
            "northward_wind": {"dims": _DIMS, "units": "m s-2"},
        }

    with pytest.raises(ValueError, match="tendency_port declares no slot"):
        RecordingCore(events, fast_tendency_component=ConcurrentCoupling([NorthFast(events)]))
