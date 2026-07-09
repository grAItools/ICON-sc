"""Static and dynamic contract checkers (architecture §4.2 ← Ubbiali sympl fork).

The static/dynamic split is the internal structure of the negotiation phase (§8.2):

- :class:`StaticChecker` consumes **component definitions only** — it validates the
  property dicts of a component class at composition time (invoked from the
  ``__init_subclass__`` hook S03 wires).
- :class:`DynamicChecker` crosses **definitions with actual data** at bind time: it
  checks one property dict against a state (or a lightweight :class:`StateSchema`,
  so S05 can reuse it without real data). ``strict=True`` (production, §2.4) turns
  any ingress that would allocate — unit conversion, dim transpose, dtype cast,
  host↔device transfer — into an exception naming field and component;
  ``strict=False`` collects the needed conversions into a
  :class:`~symcon.core.contracts.operators.ConversionPlan` instead.

Neither checker runs on the step path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from symcon.core.contracts.properties import (
    PropertyDictError,
    PropertySpec,
    parse_properties,
)
from symcon.core.state.names import lookup_quantity
from symcon.core.state.units import units_identical
from symcon.core.typing import FieldBuffer, Location

if TYPE_CHECKING:
    import xarray as xr

    from symcon.core.contracts.operators import ConversionPlan

__all__ = [
    "PROPERTY_DICT_NAMES",
    "ContractViolation",
    "ContractViolationError",
    "DynamicChecker",
    "FieldSchema",
    "StateSchema",
    "StaticChecker",
]

#: The sympl property dicts a component may define (§2.4).
PROPERTY_DICT_NAMES: tuple[str, ...] = (
    "input_properties",
    "tendency_properties",
    "diagnostic_properties",
    "output_properties",
)

#: Property dicts whose entries are state-valued (same name ⇒ same canonical units);
#: tendency entries carry per-second units and are excluded from the cross-dict check.
_STATE_VALUED_DICTS: tuple[str, ...] = (
    "input_properties",
    "diagnostic_properties",
    "output_properties",
)


@dataclass(frozen=True, slots=True)
class FieldSchema:
    """Shape-free schema of one state field: what the dynamic checkers consume."""

    dims: tuple[str, ...]
    units: str
    dtype: np.dtype[Any]
    device: tuple[int, int]
    location: Location | None = None

    @classmethod
    def from_dataarray(cls, array: xr.DataArray) -> FieldSchema:
        buffer = array.data  # never .values: no duck-array coercion (§4.2)
        device = buffer.__dlpack_device__() if isinstance(buffer, FieldBuffer) else (1, 0)
        raw_location = array.attrs.get("location")
        return cls(
            dims=tuple(str(d) for d in array.dims),
            units=str(array.attrs.get("units", "")),
            dtype=np.dtype(buffer.dtype),
            device=(int(device[0]), int(device[1])),
            location=Location(raw_location) if raw_location is not None else None,
        )


@dataclass(frozen=True)
class StateSchema:
    """name → :class:`FieldSchema` map; the data-free face of a state (§8.2, S05)."""

    fields: Mapping[str, FieldSchema]

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> StateSchema:
        """Derive the schema of a dict-of-DataArrays state (skips the ``time`` key)."""
        fields = {
            name: FieldSchema.from_dataarray(value)
            for name, value in state.items()
            if name != "time"
        }
        return cls(fields=fields)


def _as_schema(state: Mapping[str, Any] | StateSchema) -> StateSchema:
    if isinstance(state, StateSchema):
        return state
    return StateSchema.from_state(state)


@dataclass(frozen=True, slots=True)
class ContractViolation:
    """One convertible contract violation: field, component, kind, actual vs wanted."""

    field: str
    component: str
    kind: str  # "units" | "dim_order" | "dtype" | "device"
    actual: str
    target: str

    def __str__(self) -> str:
        return (
            f"[{self.kind}] field {self.field!r} of component {self.component!r}: "
            f"state has {self.actual}, contract wants {self.target}"
        )


class ContractViolationError(ValueError):
    """Strict-mode contract failure; carries every violation found."""

    def __init__(self, violations: list[ContractViolation]) -> None:
        self.violations = tuple(violations)
        super().__init__(
            "strict mode: ingress would allocate/convert:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class StaticChecker:
    """Definition-only checks on a component class (frozen interface, SPEC S02).

    ``StaticChecker(component_cls)`` validates every property dict the class defines
    (schema of the dicts themselves), cross-dict consistency (dims and canonical
    units of same-named state-valued entries, alias bijectivity) and — for names
    known to the canonical registry — that declared units are the canonical units.
    Raises :class:`PropertyDictError` naming component and field; a constructed
    instance means the definition passed and exposes the parsed specs.
    """

    def __init__(self, component_cls: type) -> None:
        self.component_cls = component_cls
        self.component = component_cls.__name__
        self.specs: dict[str, Mapping[str, PropertySpec]] = {}
        try:
            self._check()
        except PropertyDictError as exc:
            raise PropertyDictError(f"{self.component}: {exc}") from None

    def _check(self) -> None:
        for dict_name in PROPERTY_DICT_NAMES:
            raw = getattr(self.component_cls, dict_name, None)
            if raw is None:
                continue
            self.specs[dict_name] = parse_properties(raw)
        self._check_cross_dict_consistency()
        self._check_alias_bijectivity()
        self._check_canonical_units()

    def _check_cross_dict_consistency(self) -> None:
        seen: dict[str, tuple[str, PropertySpec]] = {}
        for dict_name in _STATE_VALUED_DICTS:
            for name, spec in self.specs.get(dict_name, {}).items():
                if name in seen:
                    other_dict, other = seen[name]
                    if other.dims != spec.dims:
                        raise PropertyDictError(
                            f"{name!r}: dims {other.dims!r} in {other_dict} but "
                            f"{spec.dims!r} in {dict_name}."
                        )
                    if not units_identical(other.units, spec.units):
                        raise PropertyDictError(
                            f"{name!r}: units {other.units!r} in {other_dict} but "
                            f"{spec.units!r} in {dict_name}."
                        )
                else:
                    seen[name] = (dict_name, spec)

    def _check_alias_bijectivity(self) -> None:
        name_to_alias: dict[str, str] = {}
        alias_to_name: dict[str, str] = {}
        for dict_name in PROPERTY_DICT_NAMES:
            for name, spec in self.specs.get(dict_name, {}).items():
                if spec.alias is None:
                    continue
                if name_to_alias.setdefault(name, spec.alias) != spec.alias:
                    raise PropertyDictError(
                        f"{name!r}: multiple aliases {name_to_alias[name]!r} and {spec.alias!r}."
                    )
                if alias_to_name.setdefault(spec.alias, name) != name:
                    raise PropertyDictError(
                        f"alias {spec.alias!r} maps to both "
                        f"{alias_to_name[spec.alias]!r} and {name!r}."
                    )

    def _check_canonical_units(self) -> None:
        from symcon.core.state.names import NamesRegistryError
        from symcon.core.state.units import UnitsError, verify_noop

        for dict_name in _STATE_VALUED_DICTS:
            for name, spec in self.specs.get(dict_name, {}).items():
                try:
                    canonical = lookup_quantity(name).units
                except NamesRegistryError:
                    continue  # unregistered names are the component author's claim
                try:
                    verify_noop(spec.units, canonical)
                except UnitsError as exc:
                    raise PropertyDictError(f"{name!r} in {dict_name}: {exc}") from None


class DynamicChecker:
    """Definition x data checks (frozen interface, SPEC S02).

    ``DynamicChecker(spec, state)`` — ``spec`` is a parsed property dict
    (``Mapping[str, PropertySpec]``), ``state`` a dict-of-DataArrays or a
    :class:`StateSchema`. Missing fields, incompatible dim *sets* and location
    mismatches raise unconditionally (no conversion exists). Convertible
    mismatches — units, dim order, dtype, device — raise under ``strict=True``
    (each named by field + component) and are collected into ``self.plan`` (a
    :class:`~symcon.core.contracts.operators.ConversionPlan`) under
    ``strict=False``.

    Device expectation: ``device`` (a DLPack device tuple) is normally supplied by
    the caller (S03's ComputeContext / S05's plan compiler). With ``device=None``
    the checker only enforces that all spec'd fields share **one** device, adopting
    the device of the *first field in property-dict order* as the expectation — so
    which field gets flagged on a mixed-device state depends on property-dict
    order. Pass ``device`` explicitly whenever a backend-mandated device exists.
    """

    def __init__(
        self,
        spec: Mapping[str, PropertySpec],
        state: Mapping[str, Any] | StateSchema,
        *,
        component: str = "<component>",
        strict: bool = True,
        device: tuple[int, int] | None = None,
    ) -> None:
        from symcon.core.contracts.operators import ConversionPlan, ConversionStep

        self.component = component
        self.strict = strict
        schema = _as_schema(state)
        violations: list[ContractViolation] = []
        steps: list[ConversionStep] = []
        expected_device = device

        for name, field_spec in spec.items():
            field = self._resolve(name, field_spec, schema)
            if expected_device is None:
                expected_device = field.device

            if field.location is not None and field.location is not field_spec.location:
                raise ContractViolationError(
                    [
                        ContractViolation(
                            field=name,
                            component=component,
                            kind="location",
                            actual=field.location.value,
                            target=field_spec.location.value,
                        )
                    ]
                )
            if set(field.dims) != set(field_spec.dims):
                raise ContractViolationError(
                    [
                        ContractViolation(
                            field=name,
                            component=component,
                            kind="dims",
                            actual=repr(field.dims),
                            target=repr(field_spec.dims),
                        )
                    ]
                )

            if not units_identical(field.units, field_spec.units):
                violations.append(
                    ContractViolation(
                        field=name,
                        component=component,
                        kind="units",
                        actual=repr(field.units),
                        target=repr(field_spec.units),
                    )
                )
                steps.append(
                    ConversionStep(
                        field=name,
                        kind="convert_units",
                        source=field.units,
                        target=field_spec.units,
                    )
                )
            if field.dims != field_spec.dims:
                violations.append(
                    ContractViolation(
                        field=name,
                        component=component,
                        kind="dim_order",
                        actual=repr(field.dims),
                        target=repr(field_spec.dims),
                    )
                )
                steps.append(
                    ConversionStep(
                        field=name,
                        kind="transpose",
                        source=",".join(field.dims),
                        target=",".join(field_spec.dims),
                    )
                )
            if field_spec.dtype is not None and field.dtype != field_spec.dtype:
                violations.append(
                    ContractViolation(
                        field=name,
                        component=component,
                        kind="dtype",
                        actual=str(field.dtype),
                        target=str(field_spec.dtype),
                    )
                )
                steps.append(
                    ConversionStep(
                        field=name,
                        kind="cast",
                        source=str(field.dtype),
                        target=str(field_spec.dtype),
                    )
                )
            if field.device != expected_device:
                violations.append(
                    ContractViolation(
                        field=name,
                        component=component,
                        kind="device",
                        actual=str(field.device),
                        target=str(expected_device),
                    )
                )
                steps.append(
                    ConversionStep(
                        field=name,
                        kind="transfer",
                        source=str(field.device),
                        target=str(expected_device),
                    )
                )

        if strict and violations:
            raise ContractViolationError(violations)
        self.violations: tuple[ContractViolation, ...] = tuple(violations)
        self.plan: ConversionPlan = ConversionPlan(steps=tuple(steps))

    def _resolve(self, name: str, field_spec: PropertySpec, schema: StateSchema) -> FieldSchema:
        if name in schema.fields:
            return schema.fields[name]
        if field_spec.alias is not None and field_spec.alias in schema.fields:
            return schema.fields[field_spec.alias]
        raise KeyError(
            f"field {name!r} required by component {self.component!r} is missing "
            f"from the state (present: {sorted(schema.fields)})."
        )
