"""Tendency-bus checker (SPEC S04 acceptance 3): single-consumer enforcement."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import pytest

from icon_sc.core.components.base import DiagnosticComponent, Stepper
from icon_sc.core.coupling import BusError, SlowTendencyBus, TendencySlot

_DIMS = ["cell", "height"]
SLOT = TendencySlot(name="icon:ddt_air_temperature", units="K s-1", dims=("cell", "height"))


class SlowProcess(DiagnosticComponent):
    """Publishes a piecewise-constant temperature tendency into the bus slot."""

    input_properties: ClassVar[dict[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
    }
    diagnostic_properties: ClassVar[dict[str, Any]] = {
        "icon:ddt_air_temperature": {"dims": _DIMS, "units": "K s-1"},
    }

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        outputs["icon:ddt_air_temperature"][...] = -inputs["air_temperature"] * 1e-5


class CoreConsumer(Stepper):
    """Consumes the slot through its input port (the DynamicalCore pattern)."""

    input_properties: ClassVar[dict[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
        "icon:ddt_air_temperature": {"dims": _DIMS, "units": "K s-1"},
    }
    output_properties: ClassVar[dict[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
    }

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        outputs["air_temperature"][...] = (
            inputs["air_temperature"]
            + timestep.total_seconds() * inputs["icon:ddt_air_temperature"]
        )


def test_declare_rejects_conflicting_redeclaration() -> None:
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    bus.declare(SLOT)  # identical redeclaration is idempotent
    with pytest.raises(BusError, match="already declared"):
        bus.declare(TendencySlot(name=SLOT.name, units="K min-1"))


def test_publish_requires_declared_slot_and_matching_output() -> None:
    bus = SlowTendencyBus()
    with pytest.raises(BusError, match="undeclared slot"):
        bus.publish(SlowProcess(), SLOT.name)
    bus.declare(SLOT)
    with pytest.raises(BusError, match="cannot publish"):
        bus.publish(CoreConsumer(), SLOT.name)  # slot is not among its outputs
    bus.publish(SlowProcess(), SLOT.name)


def test_units_mismatch_rejects() -> None:
    bus = SlowTendencyBus()
    bus.declare(TendencySlot(name=SLOT.name, units="K min-1"))
    with pytest.raises(BusError, match="units"):
        bus.publish(SlowProcess(), SLOT.name)


def test_zero_consumers_rejected() -> None:
    """Acceptance 3: a published slot with 0 consumers rejects."""
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    bus.publish(SlowProcess(), SLOT.name)
    with pytest.raises(BusError, match="0 consumers"):
        bus.check()


def test_two_consumers_rejected() -> None:
    """Acceptance 3: a published slot with 2 consumers rejects, naming them."""
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    bus.publish(SlowProcess(), SLOT.name)
    bus.consume(CoreConsumer(name="core"), SLOT.name)
    bus.consume(CoreConsumer(name="transport"), SLOT.name)
    with pytest.raises(BusError, match="2 consumers") as excinfo:
        bus.check()
    assert "core" in str(excinfo.value)
    assert "transport" in str(excinfo.value)


def test_exactly_one_consumer_passes() -> None:
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    bus.publish(SlowProcess(), SLOT.name)
    bus.consume(CoreConsumer(), SLOT.name)
    bus.check()


def test_consumed_but_unpublished_rejects() -> None:
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    bus.consume(CoreConsumer(), SLOT.name)
    with pytest.raises(BusError, match=r"never\s+published"):
        bus.check()


def test_consume_requires_input_declaration() -> None:
    bus = SlowTendencyBus()
    bus.declare(SLOT)
    with pytest.raises(BusError, match="cannot consume"):
        bus.consume(SlowProcess(), SLOT.name)  # slot not among its inputs
