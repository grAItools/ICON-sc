"""Canonical-units no-op verification acceptance (SPEC S02 §1).

Property-based: ``verify_noop`` must reject exactly those unit pairs Pint deems
non-identity (an independently constructed Pint registry is the oracle).
"""

from __future__ import annotations

import functools
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from icon_sc.core.state.units import UnitsError, canonical_units, units_identical, verify_noop

UNIT_POOL = [
    "K",
    "degC",
    "m s-1",
    "m/s",
    "m s^-1",
    "km h-1",
    "Pa",
    "hPa",
    "kg m-3",
    "kg/m^3",
    "1",
    "",
    "%",
    "g/kg",
    "W m-2",
    "s-1",
    "degrees_north",
]


@functools.cache
def _oracle_registry() -> object:
    import pint

    registry = pint.UnitRegistry()
    registry.define("degrees_north = degree_north = degree_N = degrees_N = degreeN = degreesN")
    registry.define("degrees_east = degree_east = degree_E = degrees_E = degreeE = degreesE")
    registry.define("percent = 0.01*count = %")
    return registry


def _cf_to_pint(units: str) -> str:
    # ICON-sc's spelled-out convention: canonical strings use CF/UDUNITS exponent
    # syntax ("m s-1"); pint wants "m s**-1". Same normalization as the module.
    return re.sub(r"(?<=[A-Za-z])\^?(-?\d+)", r"**\1", units.replace("%", "percent"))


def _pint_identity(units_a: str, units_b: str) -> bool:
    registry = _oracle_registry()
    try:
        return bool(registry(_cf_to_pint(units_a)) == registry(_cf_to_pint(units_b)))
    except Exception:  # offset units etc.: not an identity
        return False


@settings(deadline=None)  # first example pays lazy Pint UnitRegistry construction
@given(st.sampled_from(UNIT_POOL), st.sampled_from(UNIT_POOL))
def test_verify_noop_matches_pint_identity(units_a: str, units_b: str) -> None:
    if _pint_identity(units_a, units_b):
        verify_noop(units_a, units_b)  # must not raise
    else:
        with pytest.raises(UnitsError):
            verify_noop(units_a, units_b)


@given(st.sampled_from(UNIT_POOL))
def test_identical_strings_are_always_noop(units: str) -> None:
    verify_noop(units, units)


@pytest.mark.parametrize(
    ("component_units", "canonical"),
    [("degC", "K"), ("km h-1", "m s-1"), ("hPa", "Pa"), ("g/kg", "1"), ("%", "1")],
)
def test_convertible_but_not_identical_is_rejected(component_units: str, canonical: str) -> None:
    # Pint *could* convert every one of these — that is exactly what production
    # forbids: the conversion would not compile to a no-op.
    with pytest.raises(UnitsError, match="no-op"):
        verify_noop(component_units, canonical)


def test_spelling_variants_are_identity() -> None:
    assert units_identical("m s-1", "m/s")
    assert units_identical("m s-1", "m s^-1")
    verify_noop("m/s", "m s-1")


def test_canonical_units_lookup() -> None:
    assert canonical_units("air_temperature") == "K"
    assert canonical_units("icon:exner_function") == "1"
    assert canonical_units("upward_air_velocity_on_interface_levels") == "m s-1"


def test_undefined_units_never_identical() -> None:
    assert not units_identical("furlong_per_fortnight_x", "m s-1")
