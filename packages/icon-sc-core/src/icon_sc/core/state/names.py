"""Canonical-name registry (architecture §2.5).

One table maps each canonical quantity name to its canonical units, CF standard name
(if any), ICON Fortran short name (if any) and GRIB2 triplet (ingestion only).

Namespacing (§2.5): CF standard names are the canonical names and carry **no** prefix
(the ``cf:`` namespace is implicit — spelling it out is rejected). Solver-internal
quantities — those *without* a CF standard name — live in the explicit ``icon:``
namespace (``icon:exner_function``, ``icon:normal_wind``, …). The registry enforces
that split both ways:

- an unprefixed registration claims CF identity (``cf_name`` defaults to the name);
- an unprefixed registration that *disclaims* CF identity (``cf_name=NO_CF``) is the
  "unnamespaced icon" error: it must be registered as ``icon:<name>`` instead;
- an ``icon:`` registration passing a ``cf_name`` is contradictory: quantities with a
  CF standard name are registered under it, unprefixed;
- any namespace prefix other than ``icon:`` is rejected.

The ``_on_interface_levels`` suffix (sympl convention) marks the ``height_interface``
dim variant of a quantity; unit lookups for a suffixed name fall back to its base
quantity, since the physical quantity — hence its canonical units — is the same.

Seed rows: icon4py v0.2.0 ``model/common/states/data.py`` (see REFERENCES.lock).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

__all__ = [
    "INTERFACE_LEVEL_SUFFIX",
    "NO_CF",
    "NamesRegistryError",
    "QuantityDef",
    "base_name",
    "is_on_interface_levels",
    "known_quantities",
    "lookup_quantity",
    "on_interface_levels",
    "register_quantity",
]

INTERFACE_LEVEL_SUFFIX: Final[str] = "_on_interface_levels"

#: Sentinel for "this quantity has no CF standard name" (distinct from the default
#: ``None`` = "the canonical name *is* the CF standard name").
NO_CF: Final[str] = "<no-cf-standard-name>"

_ICON_NAMESPACE: Final[str] = "icon"
_NAME_RE: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*\Z")


class NamesRegistryError(ValueError):
    """Invalid or conflicting canonical-name registration/lookup."""


@dataclass(frozen=True, slots=True)
class QuantityDef:
    """One row of the canonical registry: name ↔ units ↔ CF ↔ ICON ↔ GRIB2."""

    name: str
    units: str
    cf_name: str | None
    icon_name: str | None
    grib2: tuple[int, int, int] | None


_REGISTRY: dict[str, QuantityDef] = {}


def register_quantity(
    name: str,
    units: str,
    cf_name: str | None = None,
    icon_name: str | None = None,
    grib2: tuple[int, int, int] | None = None,
) -> QuantityDef:
    """Register a canonical quantity (frozen interface, SPEC S02).

    ``units`` is the canonical unit string for the quantity; component contracts are
    verified against it by :func:`icon_sc.core.state.units.verify_noop`.
    """
    namespace, _, local = name.rpartition(":")
    if namespace and namespace != _ICON_NAMESPACE:
        raise NamesRegistryError(
            f"cannot register {name!r}: unknown namespace {namespace!r}. CF standard "
            f"names are unprefixed (the cf: namespace is implicit); solver-internal "
            f"quantities use the icon: namespace."
        )
    if not _NAME_RE.match(local):
        raise NamesRegistryError(
            f"cannot register {name!r}: {local!r} is not a valid quantity identifier "
            f"(lowercase letters, digits and underscores)."
        )
    if name in _REGISTRY:
        raise NamesRegistryError(
            f"cannot register {name!r}: already registered (units {_REGISTRY[name].units!r})."
        )
    if namespace == _ICON_NAMESPACE:
        if cf_name is not None and cf_name != NO_CF:
            raise NamesRegistryError(
                f"cannot register {name!r} with cf_name={cf_name!r}: quantities with a "
                f"CF standard name are registered under it, unprefixed."
            )
        resolved_cf: str | None = None
    else:
        if cf_name == NO_CF:
            raise NamesRegistryError(
                f"cannot register {name!r}: a quantity without a CF standard name is "
                f"solver-internal and must be namespaced as 'icon:{name}'."
            )
        resolved_cf = cf_name if cf_name is not None else name
    quantity = QuantityDef(
        name=name, units=units, cf_name=resolved_cf, icon_name=icon_name, grib2=grib2
    )
    _REGISTRY[name] = quantity
    return quantity


def lookup_quantity(name: str) -> QuantityDef:
    """Return the registered quantity, resolving the interface-levels fallback."""
    if name in _REGISTRY:
        return _REGISTRY[name]
    if is_on_interface_levels(name):
        base = base_name(name)
        if base in _REGISTRY:
            return _REGISTRY[base]
    raise NamesRegistryError(f"unknown quantity {name!r}; known: {sorted(_REGISTRY)}")


def known_quantities() -> tuple[str, ...]:
    """Sorted canonical names currently registered."""
    return tuple(sorted(_REGISTRY))


def is_on_interface_levels(name: str) -> bool:
    """True if ``name`` carries the ``_on_interface_levels`` suffix."""
    return name.endswith(INTERFACE_LEVEL_SUFFIX)


def on_interface_levels(name: str) -> str:
    """The interface-level variant of a canonical name (idempotent)."""
    return name if is_on_interface_levels(name) else name + INTERFACE_LEVEL_SUFFIX


def base_name(name: str) -> str:
    """Strip the ``_on_interface_levels`` suffix (identity when absent)."""
    if is_on_interface_levels(name):
        return name[: -len(INTERFACE_LEVEL_SUFFIX)]
    return name


def _register_seed_table() -> None:
    """Seed rows mined from icon4py v0.2.0 states/data.py (REFERENCES.lock S02).

    icon4py files exner/theta_v/vn under CF-style standard names; per architecture
    §2.5 these are solver-internal in ICON-sc and live in the icon: namespace.
    """
    # prognostics
    register_quantity("air_density", "kg m-3", icon_name="rho")
    register_quantity("upward_air_velocity", "m s-1", icon_name="w")
    register_quantity("icon:virtual_potential_temperature", "K", icon_name="theta_v")
    register_quantity("icon:exner_function", "1", icon_name="exner")
    register_quantity("icon:normal_wind", "m s-1", icon_name="vn")
    register_quantity("icon:tangential_wind", "m s-1", icon_name="vt")
    # common tracers
    register_quantity("specific_humidity", "1", icon_name="qv")
    register_quantity("specific_cloud_content", "1", icon_name="qc")
    register_quantity("specific_ice_content", "1", icon_name="qi")
    register_quantity("specific_rain_content", "1", icon_name="qr")
    register_quantity("specific_snow_content", "1", icon_name="qs")
    register_quantity("specific_graupel_content", "1", icon_name="qg")
    # diagnostics
    register_quantity("eastward_wind", "m s-1", icon_name="u")
    register_quantity("northward_wind", "m s-1", icon_name="v")
    register_quantity("air_temperature", "K", icon_name="temp")
    register_quantity("air_virtual_temperature", "K", icon_name="tempv")
    register_quantity("air_pressure", "Pa", icon_name="pres")
    register_quantity("air_pressure_at_ground_level", "Pa", icon_name="pres_sfc")


_register_seed_table()
