"""Dynamic operators: ingress/egress plans and conversion plans (§2.3, §4.2, §8.2).

An :class:`IngressPlan` is built **once** at bind time from a property dict and a
:class:`~symcon.core.contracts.checkers.StateSchema` (S05 pre-resolves it into bound
argument packs) and applied per step by S03's interpreted tier. The plan holds field
*names only* — schema in, raw buffers out; no xarray objects, no Pint, no per-step
negotiation. ``apply`` is a plain tuple comprehension over ``state[name].data``:
zero-copy by construction (buffer identities are stable across applications).

:class:`ConversionPlan` is what the non-strict dynamic checker returns instead of
raising: the ordered allocating conversions (units/transpose/cast/transfer) that
would reconcile a state with a contract. S03 executes it; strict mode forbids it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from symcon.core.contracts.checkers import DynamicChecker, StateSchema
from symcon.core.contracts.properties import PropertySpec
from symcon.core.typing import FieldBuffer

__all__ = ["ConversionPlan", "ConversionStep", "EgressPlan", "IngressPlan"]


@dataclass(frozen=True, slots=True)
class ConversionStep:
    """One allocating reconciliation of a field with its contract."""

    field: str
    kind: str  # "convert_units" | "transpose" | "cast" | "transfer"
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class ConversionPlan:
    """Ordered conversions the non-strict checker proposes (empty = no-op ingress)."""

    steps: tuple[ConversionStep, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.steps)


@dataclass(frozen=True, slots=True)
class IngressPlan:
    """Pre-resolved zero-copy ingress (frozen interface, SPEC S02).

    ``names`` are the state keys to pull, in property-dict (= argument) order, with
    aliases already resolved; ``fields`` are the contract names they satisfy.
    """

    component: str
    fields: tuple[str, ...]
    names: tuple[str, ...]

    @classmethod
    def build(
        cls,
        spec: Mapping[str, PropertySpec],
        state_schema: StateSchema | Mapping[str, Any],
        *,
        component: str = "<component>",
    ) -> IngressPlan:
        """Build the plan at bind time; strict by construction.

        Runs the strict dynamic checker: a state that would need any allocating
        conversion cannot be pre-resolved (run the
        :class:`~symcon.core.contracts.checkers.DynamicChecker` with
        ``strict=False`` and execute its plan first).
        """
        schema = (
            state_schema
            if isinstance(state_schema, StateSchema)
            else StateSchema.from_state(state_schema)
        )
        DynamicChecker(spec, schema, component=component, strict=True)
        fields = tuple(spec)
        names: list[str] = []
        for name in fields:
            alias = spec[name].alias
            if name not in schema.fields and alias is not None and alias in schema.fields:
                names.append(alias)
            else:
                names.append(name)
        return cls(component=component, fields=fields, names=tuple(names))

    def apply(self, state: Mapping[str, Any]) -> tuple[FieldBuffer, ...]:
        """Extract the raw buffers, in plan order (frozen interface, SPEC S02).

        Pure lookups: no validation, no conversion, no copies — negotiation already
        happened in :meth:`build`. Never touches ``.values`` (§4.2).
        """
        return tuple(state[name].data for name in self.names)


class EgressPlan(IngressPlan):
    """Egress twin of :class:`IngressPlan`: resolves a component's *output* buffers.

    Mechanically identical — outputs are caller-provided/preallocated DataArrays
    living in the same state mapping (§8.2 buffer-identity contract), so egress is
    the same pre-resolved raw-buffer extraction, kept as its own type so plans are
    self-describing in S03/S05 op lists.
    """
