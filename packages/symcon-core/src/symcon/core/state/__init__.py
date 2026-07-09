"""State layer: canonical names/units registries and boundary DataArray construction."""

from symcon.core.state.dataarray import make_dataarray
from symcon.core.state.names import (
    INTERFACE_LEVEL_SUFFIX,
    NamesRegistryError,
    QuantityDef,
    base_name,
    is_on_interface_levels,
    known_quantities,
    lookup_quantity,
    on_interface_levels,
    register_quantity,
)
from symcon.core.state.units import UnitsError, canonical_units, units_identical, verify_noop

__all__ = [
    "INTERFACE_LEVEL_SUFFIX",
    "NamesRegistryError",
    "QuantityDef",
    "UnitsError",
    "base_name",
    "canonical_units",
    "is_on_interface_levels",
    "known_quantities",
    "lookup_quantity",
    "make_dataarray",
    "on_interface_levels",
    "register_quantity",
    "units_identical",
    "verify_noop",
]
