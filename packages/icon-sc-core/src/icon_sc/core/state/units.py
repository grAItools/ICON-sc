"""Canonical-units table access and the no-op-conversion verifier (architecture §2.4).

Canonical units are stored as plain strings in the names registry; Pint is consulted
only at negotiation time (registration/verification), through a cached identity check
(pattern from stubbiali/sympl ``oop``: ``lru_cache`` on the registry call). Nothing on
the execution path — in particular :meth:`IngressPlan.apply` — may import Pint; the
import happens lazily inside :func:`units_identical`, and only when two unit strings
are not literally equal.

Unit-string cleanup (``%`` → ``percent``, ``°`` → ``degree``) and the extra
``degrees_north``/``degrees_east``/``percent`` definitions are ported from upstream
sympl ``_core/units.py`` (see REFERENCES.lock).
"""

from __future__ import annotations

import functools
import re
from typing import TYPE_CHECKING, Any

from icon_sc.core.state.names import lookup_quantity

if TYPE_CHECKING:
    import pint

__all__ = ["UnitsError", "canonical_units", "convert_array", "units_identical", "verify_noop"]


class UnitsError(ValueError):
    """A component's declared units are not the canonical units (no-op violation)."""


def canonical_units(name: str) -> str:
    """Canonical unit string of a registered quantity (frozen interface, SPEC S02).

    ``*_on_interface_levels`` variants fall back to their base quantity.
    """
    return lookup_quantity(name).units


@functools.cache
def _registry() -> pint.UnitRegistry:
    import pint

    registry = pint.UnitRegistry()
    registry.define("degrees_north = degree_north = degree_N = degrees_N = degreeN = degreesN")
    registry.define("degrees_east = degree_east = degree_E = degrees_E = degreeE = degreesE")
    registry.define("percent = 0.01*count = %")
    return registry


#: CF/UDUNITS exponent syntax (``m s-1``, ``kg m-3``, ``m^3``) → pint (``m s**-1``).
_CF_EXPONENT_RE = re.compile(r"(?<=[A-Za-z])\^?(-?\d+)")


def _clean(units: str) -> str:
    cleaned = units.replace("%", "percent").replace("°", "degree")
    return _CF_EXPONENT_RE.sub(r"**\1", cleaned)


@functools.cache
def _parse(units: str) -> Any:
    return _registry()(_clean(units))


@functools.cache
def units_identical(units_a: str, units_b: str) -> bool:
    """True iff Pint deems the two unit strings the *same* unit (identity, not mere
    dimensional compatibility): conversion between them is a no-op."""
    if units_a == units_b:
        return True
    try:
        return bool(_parse(units_a) == _parse(units_b))
    except Exception:  # offset units, undefined units, … — never identical
        return False


def convert_array(values: Any, source: str, target: str) -> Any:
    """Convert an array from ``source`` to ``target`` units via Pint (allocating).

    **Negotiation-time only** (non-strict ingress executing a
    :class:`~icon_sc.core.contracts.operators.ConversionPlan`, S03); strict mode
    forbids the call sites, and nothing on the apply path may reach this.

    Raises:
        UnitsError: When Pint cannot convert (undefined/incompatible units).
    """
    if units_identical(source, target):
        return values
    quantity = _registry().Quantity(values, _clean(source))
    try:
        return quantity.to(_clean(target)).magnitude
    except Exception as exc:
        raise UnitsError(f"cannot convert {source!r} to {target!r}: {exc}") from None


def verify_noop(component_units: str, canonical: str) -> None:
    """Verify a component's declared units equal the canonical units (§2.4).

    sympl's Pint conversion path must compile to a no-op in production; any pair Pint
    deems non-identity (``K`` vs ``degC``, ``m s-1`` vs ``km h-1``, ``1`` vs
    ``g/kg``, …) is rejected. Called at negotiation time only.
    """
    if not units_identical(component_units, canonical):
        raise UnitsError(
            f"declared units {component_units!r} are not the canonical units "
            f"{canonical!r}: the conversion would not be a no-op."
        )
