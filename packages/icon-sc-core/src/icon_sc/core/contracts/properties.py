"""Typed property-dict schema (architecture §2.4, §8.6).

Components keep sympl's ``input_properties`` / ``tendency_properties`` /
``diagnostic_properties`` / ``output_properties`` dicts; ICON-sc's schema extends the
sympl entries (``dims``, ``units``, ``alias``) with ``location``, ``halo``,
``differentiable`` (§8.6) and ``params`` (§8.6), and drops sympl's wildcard/dims-like
machinery — canonical names + canonical units make target dims explicit.

:func:`parse_properties` validates the *dicts themselves* (definition-only, no data)
and normalizes them into frozen, slotted :class:`PropertySpec` records; it is the
substrate the static checker runs on.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from icon_sc.core.typing import HORIZONTAL_DIMS, Location

__all__ = [
    "Differentiable",
    "HaloPolicy",
    "PropertyDictError",
    "PropertySpec",
    "parse_properties",
]


class PropertyDictError(ValueError):
    """A property dict is malformed (definition-time error, names the component)."""


class HaloPolicy(str, enum.Enum):
    """Contract-side halo requirement of one field in one property dict (§2.4)."""

    OWNED = "owned"  # computes on owned points only
    REQUIRED = "required"  # needs valid ghost points
    INVALIDATED = "invalidated"  # output dirties the halo

    def __str__(self) -> str:
        return self.value


class Differentiable(str, enum.Enum):
    """Differentiability axis of the contract (§8.6)."""

    NATIVE = "native"
    CUSTOM = "custom"
    NONE = "none"

    def __str__(self) -> str:
        return self.value


#: Keys admitted in a property-dict entry.
_KNOWN_KEYS = frozenset(
    {"dims", "units", "location", "halo", "alias", "dtype", "differentiable", "params"}
)


@dataclass(frozen=True, slots=True)
class PropertySpec:
    """Normalized, immutable form of one property-dict entry (frozen interface)."""

    name: str
    dims: tuple[str, ...]
    units: str
    location: Location
    halo: HaloPolicy | None = None
    alias: str | None = None
    dtype: np.dtype[Any] | None = None
    differentiable: Differentiable = Differentiable.NONE
    params: tuple[str, ...] = field(default=())


def _infer_location(name: str, dims: tuple[str, ...], raw: Mapping[str, Any]) -> Location:
    declared = raw.get("location")
    horizontal = [d for d in dims if d in HORIZONTAL_DIMS]
    if len(horizontal) > 1:
        raise PropertyDictError(f"{name!r}: multiple horizontal dims {horizontal!r}.")
    if declared is not None:
        try:
            loc = Location(declared)
        except ValueError:
            raise PropertyDictError(
                f"{name!r}: invalid location {declared!r}; "
                f"expected one of {[m.value for m in Location]}."
            ) from None
        if horizontal and horizontal[0] != loc.value:
            raise PropertyDictError(
                f"{name!r}: horizontal dim {horizontal[0]!r} contradicts location={loc.value!r}."
            )
        return loc
    if horizontal:
        return Location(horizontal[0])
    return Location.SCALAR


def _parse_entry(name: str, raw: Any) -> PropertySpec:
    if not isinstance(raw, Mapping):
        raise PropertyDictError(f"{name!r}: entry is {type(raw).__name__}, expected a mapping.")
    unknown = set(raw) - _KNOWN_KEYS
    if unknown:
        raise PropertyDictError(
            f"{name!r}: unknown property keys {sorted(unknown)!r}; "
            f"known keys: {sorted(_KNOWN_KEYS)!r}."
        )
    if "units" not in raw:
        raise PropertyDictError(f"{name!r}: missing required key 'units'.")
    units = raw["units"]
    if not isinstance(units, str):
        raise PropertyDictError(f"{name!r}: units must be a string, got {units!r}.")
    if "dims" not in raw:
        raise PropertyDictError(f"{name!r}: missing required key 'dims'.")
    raw_dims = raw["dims"]
    if isinstance(raw_dims, str) or not all(isinstance(d, str) for d in raw_dims):
        raise PropertyDictError(f"{name!r}: dims must be a sequence of strings, got {raw_dims!r}.")
    dims = tuple(raw_dims)
    if len(set(dims)) != len(dims):
        raise PropertyDictError(f"{name!r}: repeated dims in {dims!r}.")
    if any(d == "*" for d in dims):
        raise PropertyDictError(
            f"{name!r}: wildcard dims are not part of the ICON-sc schema "
            f"(canonical names make target dims explicit)."
        )
    location = _infer_location(name, dims, raw)
    halo: HaloPolicy | None = None
    if raw.get("halo") is not None:
        try:
            halo = HaloPolicy(raw["halo"])
        except ValueError:
            raise PropertyDictError(
                f"{name!r}: invalid halo {raw['halo']!r}; "
                f"expected one of {[m.value for m in HaloPolicy]}."
            ) from None
    try:
        differentiable = Differentiable(raw.get("differentiable", Differentiable.NONE))
    except ValueError:
        raise PropertyDictError(
            f"{name!r}: invalid differentiable {raw['differentiable']!r}; "
            f"expected one of {[m.value for m in Differentiable]}."
        ) from None
    alias = raw.get("alias")
    if alias is not None and not isinstance(alias, str):
        raise PropertyDictError(f"{name!r}: alias must be a string, got {alias!r}.")
    dtype: np.dtype[Any] | None = None
    if raw.get("dtype") is not None:
        try:
            dtype = np.dtype(raw["dtype"])
        except TypeError:
            raise PropertyDictError(f"{name!r}: invalid dtype {raw['dtype']!r}.") from None
    raw_params = raw.get("params", ())
    try:
        params_ok = not isinstance(raw_params, str) and all(isinstance(p, str) for p in raw_params)
    except TypeError:
        params_ok = False
    if not params_ok:
        raise PropertyDictError(
            f"{name!r}: params must be a sequence of parameter names, got {raw_params!r}."
        )
    return PropertySpec(
        name=name,
        dims=dims,
        units=units,
        location=location,
        halo=halo,
        alias=alias,
        dtype=dtype,
        differentiable=differentiable,
        params=tuple(raw_params),
    )


def parse_properties(properties: Mapping[str, Any]) -> Mapping[str, PropertySpec]:
    """Validate a property dict and normalize it (frozen interface, SPEC S02).

    Checks the dict itself — entry types, required/unknown keys, enum values, alias
    bijectivity — with errors naming the offending field. Insertion order is kept
    (it is the ingress argument order).
    """
    if not isinstance(properties, Mapping):
        raise PropertyDictError(
            f"property dict is {type(properties).__name__}, expected a mapping."
        )
    specs: dict[str, PropertySpec] = {}
    alias_to_name: dict[str, str] = {}
    for name, raw in properties.items():
        if not isinstance(name, str):
            raise PropertyDictError(f"field names must be strings, got {name!r}.")
        spec = _parse_entry(name, raw)
        if spec.alias is not None:
            holder = alias_to_name.setdefault(spec.alias, name)
            if holder != name:
                raise PropertyDictError(
                    f"alias {spec.alias!r} maps to both {holder!r} and {name!r}."
                )
        specs[name] = spec
    return specs
