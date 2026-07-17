"""Canonical-name registry acceptance (SPEC S02 §1: duplicates, namespacing)."""

from __future__ import annotations

import pytest

from icon_sc.core.state import names
from icon_sc.core.state.names import (
    NO_CF,
    NamesRegistryError,
    base_name,
    is_on_interface_levels,
    known_quantities,
    lookup_quantity,
    on_interface_levels,
    register_quantity,
)


@pytest.fixture(autouse=True)
def _restore_registry() -> object:
    saved = dict(names._REGISTRY)
    yield
    names._REGISTRY.clear()
    names._REGISTRY.update(saved)


def test_duplicate_registration_rejected() -> None:
    register_quantity("test_quantity", "K")
    with pytest.raises(NamesRegistryError, match="already registered"):
        register_quantity("test_quantity", "K")


def test_duplicate_rejected_even_with_different_units() -> None:
    with pytest.raises(NamesRegistryError, match="already registered"):
        register_quantity("air_temperature", "degC")  # seeded as K


def test_unnamespaced_icon_registration_rejected() -> None:
    # A quantity that disclaims CF identity is solver-internal and must be icon:.
    with pytest.raises(NamesRegistryError, match="icon:ddt_vn_phy"):
        register_quantity("ddt_vn_phy", "m s-2", cf_name=NO_CF)


def test_icon_name_with_cf_name_rejected() -> None:
    with pytest.raises(NamesRegistryError, match="unprefixed"):
        register_quantity("icon:some_quantity", "K", cf_name="air_temperature")


def test_foreign_namespace_rejected() -> None:
    with pytest.raises(NamesRegistryError, match="namespace"):
        register_quantity("cosmo:some_quantity", "K")


def test_explicit_cf_prefix_rejected() -> None:
    # cf: is implicit — spelling it out is an error, not an alias.
    with pytest.raises(NamesRegistryError, match="namespace"):
        register_quantity("cf:air_potential_temperature", "K")


def test_invalid_identifier_rejected() -> None:
    with pytest.raises(NamesRegistryError, match="identifier"):
        register_quantity("Air Temperature", "K")


def test_unprefixed_name_gets_implicit_cf_identity() -> None:
    quantity = register_quantity("air_potential_temperature", "K", icon_name="theta")
    assert quantity.cf_name == "air_potential_temperature"
    assert quantity.icon_name == "theta"


def test_icon_namespaced_has_no_cf_name() -> None:
    quantity = lookup_quantity("icon:exner_function")
    assert quantity.cf_name is None
    assert quantity.icon_name == "exner"
    assert quantity.units == "1"


def test_unknown_lookup_lists_known_names() -> None:
    with pytest.raises(NamesRegistryError, match="air_temperature"):
        lookup_quantity("no_such_quantity")


def test_seed_table_from_icon4py() -> None:
    # Spot checks against icon4py v0.2.0 states/data.py (REFERENCES.lock S02).
    assert lookup_quantity("air_temperature").units == "K"
    assert lookup_quantity("air_temperature").icon_name == "temp"
    assert lookup_quantity("air_pressure").units == "Pa"
    assert lookup_quantity("air_density").units == "kg m-3"
    assert lookup_quantity("specific_humidity").units == "1"
    assert lookup_quantity("icon:normal_wind").units == "m s-1"
    assert lookup_quantity("icon:virtual_potential_temperature").units == "K"
    assert "air_temperature" in known_quantities()


def test_interface_level_suffix_convention() -> None:
    assert on_interface_levels("upward_air_velocity") == ("upward_air_velocity_on_interface_levels")
    assert on_interface_levels("x_on_interface_levels") == "x_on_interface_levels"
    assert is_on_interface_levels("x_on_interface_levels")
    assert not is_on_interface_levels("x")
    assert base_name("x_on_interface_levels") == "x"
    assert base_name("x") == "x"


def test_interface_level_lookup_falls_back_to_base_quantity() -> None:
    variant = lookup_quantity("upward_air_velocity_on_interface_levels")
    assert variant.units == "m s-1"  # same physical quantity, same canonical units
