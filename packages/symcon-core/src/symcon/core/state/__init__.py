"""State layer: names/units registries, boundary DataArrays, and the S05 vault."""

from symcon.core.state.dataarray import make_dataarray
from symcon.core.state.facade import VaultFacade
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
from symcon.core.state.units import (
    UnitsError,
    canonical_units,
    convert_array,
    units_identical,
    verify_noop,
)
from symcon.core.state.vault import SlotMeta, StateVault

__all__ = [
    "INTERFACE_LEVEL_SUFFIX",
    "NamesRegistryError",
    "QuantityDef",
    "SlotMeta",
    "StateVault",
    "UnitsError",
    "VaultFacade",
    "base_name",
    "canonical_units",
    "convert_array",
    "is_on_interface_levels",
    "known_quantities",
    "lookup_quantity",
    "make_dataarray",
    "on_interface_levels",
    "register_quantity",
    "units_identical",
    "verify_noop",
]
