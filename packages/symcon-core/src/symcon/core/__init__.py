"""symcon.core — model-agnostic composition framework.

Curated public API re-exports (S02: state layer + contracts). Keeping the
namespace-level ``symcon`` package implicit (PEP 420) is what lets ``symcon-icon`` and
``symcon-bridges`` install into the same import root.
"""

from symcon.core.config import Config, provenance_stamp
from symcon.core.contracts import (
    ContractViolation,
    ContractViolationError,
    ConversionPlan,
    ConversionStep,
    Differentiable,
    DynamicChecker,
    EgressPlan,
    FieldSchema,
    HaloPolicy,
    IngressPlan,
    PropertyDictError,
    PropertySpec,
    StateSchema,
    StaticChecker,
    parse_properties,
)
from symcon.core.profiling import Timer
from symcon.core.registry import Factory, MetaFactory, RegistrationError
from symcon.core.state import (
    NamesRegistryError,
    QuantityDef,
    UnitsError,
    canonical_units,
    make_dataarray,
    register_quantity,
    units_identical,
    verify_noop,
)
from symcon.core.typing import FieldBuffer, HaloState, Location

__version__ = "0.1.0"

__all__ = [
    "Config",
    "ContractViolation",
    "ContractViolationError",
    "ConversionPlan",
    "ConversionStep",
    "Differentiable",
    "DynamicChecker",
    "EgressPlan",
    "Factory",
    "FieldBuffer",
    "FieldSchema",
    "HaloPolicy",
    "HaloState",
    "IngressPlan",
    "Location",
    "MetaFactory",
    "NamesRegistryError",
    "PropertyDictError",
    "PropertySpec",
    "QuantityDef",
    "RegistrationError",
    "StateSchema",
    "StaticChecker",
    "Timer",
    "UnitsError",
    "canonical_units",
    "make_dataarray",
    "parse_properties",
    "provenance_stamp",
    "register_quantity",
    "units_identical",
    "verify_noop",
]
