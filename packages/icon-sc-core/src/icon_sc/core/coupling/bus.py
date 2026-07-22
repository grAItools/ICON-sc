"""The slow-tendency bus: slot declaration + single-consumer check (SPEC S04).

Architecture §4.2 ("the bus, reframed"): slow processes publish piecewise-constant
tendencies into named state slots (``icon:ddt_*`` convention) under
``CallingFrequency``; the dynamical core and transport declare those slots as
inputs (the :class:`~icon_sc.core.components.dycore.DynamicalCore` slow-tendency
port). The bus is the *naming-and-checking convention* for that port — pure
composition-time bookkeeping, never on the step path:

- :meth:`SlowTendencyBus.declare` registers a slot (name + canonical units);
- :meth:`SlowTendencyBus.publish` / :meth:`SlowTendencyBus.consume` record which
  component writes/reads a slot, validated against the component's property dicts;
- :meth:`SlowTendencyBus.check` enforces that **every published slot has exactly
  one consumer** (0 or ≥2 both reject: a dangling tendency silently loses physics,
  a double consumer double-applies it) and that every consumed slot is published.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from icon_sc.core.contracts.properties import PropertySpec
from icon_sc.core.coupling.concurrent import (
    name_of,
    output_dict_names_of,
    parsed_properties_of,
)

__all__ = ["BusError", "SlowTendencyBus", "TendencySlot"]


class BusError(ValueError):
    """A tendency-bus declaration or wiring rule is violated (composition time)."""


@dataclasses.dataclass(frozen=True, slots=True)
class TendencySlot:
    """One bus slot: a named state field carrying a piecewise-constant tendency.

    ``name`` is the state key (``icon:ddt_*`` convention downstream); ``units``
    are the canonical tendency units; ``dims``, when given, are checked against
    publisher/consumer declarations.
    """

    name: str
    units: str
    dims: tuple[str, ...] | None = None


class SlowTendencyBus:
    """Composition-time registry of tendency slots and their wiring (SPEC S04)."""

    def __init__(self) -> None:
        self._slots: dict[str, TendencySlot] = {}
        self._publishers: dict[str, list[str]] = {}
        self._consumers: dict[str, list[str]] = {}

    @property
    def slots(self) -> dict[str, TendencySlot]:
        """The declared slots, keyed by slot (state-field) name."""
        return dict(self._slots)

    def declare(self, slot: TendencySlot) -> TendencySlot:
        """Register a slot; re-declaring a name with a different contract rejects."""
        held = self._slots.get(slot.name)
        if held is not None and held != slot:
            raise BusError(
                f"slot {slot.name!r} already declared as {held!r}; cannot redeclare as {slot!r}."
            )
        self._slots[slot.name] = slot
        return slot

    def _slot_spec(
        self, component: Any, slot_name: str, *, dict_names: tuple[str, ...], role: str
    ) -> PropertySpec:
        slot = self._slots.get(slot_name)
        if slot is None:
            raise BusError(
                f"cannot {role} undeclared slot {slot_name!r} (declared: {sorted(self._slots)})."
            )
        parsed = parsed_properties_of(component)
        for dict_name in dict_names:
            spec = parsed.get(dict_name, {}).get(slot_name)
            if spec is not None:
                if spec.units != slot.units:
                    raise BusError(
                        f"component {name_of(component)!r} wires slot {slot_name!r} "
                        f"with units {spec.units!r}, but the slot is declared "
                        f"{slot.units!r}."
                    )
                if slot.dims is not None and spec.dims != slot.dims:
                    raise BusError(
                        f"component {name_of(component)!r} wires slot {slot_name!r} "
                        f"with dims {spec.dims!r}, but the slot is declared "
                        f"{slot.dims!r}."
                    )
                return spec
        raise BusError(
            f"component {name_of(component)!r} cannot {role} slot {slot_name!r}: "
            f"the field is not declared in its {'/'.join(dict_names)}."
        )

    def publish(self, component: Any, *slot_names: str) -> None:
        """Record that ``component`` writes the named slots (validated against outputs)."""
        for slot_name in slot_names:
            self._slot_spec(
                component,
                slot_name,
                dict_names=output_dict_names_of(component),
                role="publish",
            )
            self._publishers.setdefault(slot_name, []).append(name_of(component))

    def consume(self, component: Any, *slot_names: str) -> None:
        """Record that ``component`` reads the named slots (validated against inputs)."""
        for slot_name in slot_names:
            self._slot_spec(component, slot_name, dict_names=("input_properties",), role="consume")
            self._consumers.setdefault(slot_name, []).append(name_of(component))

    def check(self) -> None:
        """The single-consumer check (frozen interface, SPEC S04 acceptance 3).

        Every published slot must have exactly one consumer; every consumed slot
        must have at least one publisher.

        Raises:
            BusError: Naming the slot and the offending components.
        """
        problems: list[str] = []
        for slot_name, publishers in sorted(self._publishers.items()):
            consumers = self._consumers.get(slot_name, [])
            if len(consumers) != 1:
                problems.append(
                    f"slot {slot_name!r} (published by {publishers!r}) has "
                    f"{len(consumers)} consumers {consumers!r}; exactly one is required."
                )
        for slot_name, consumers in sorted(self._consumers.items()):
            if slot_name not in self._publishers:
                problems.append(
                    f"slot {slot_name!r} is consumed by {consumers!r} but never published."
                )
        if problems:
            raise BusError("tendency-bus check failed:\n" + "\n".join(problems))
