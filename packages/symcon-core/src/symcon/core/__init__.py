"""symcon.core — model-agnostic composition framework.

Curated public API re-exports (S02: state layer + contracts; S03: component
taxonomy + wrappers + context + T0 driver/monitors). Keeping the namespace-level
``symcon`` package implicit (PEP 420) is what lets ``symcon-icon`` and
``symcon-bridges`` install into the same import root.
"""

from symcon.core.components import (
    CallingFrequency,
    Component,
    DiagnosticComponent,
    ImplicitTendencyComponent,
    Monitor,
    OutputSchema,
    ScalingWrapper,
    Stepper,
    Subcycle,
    TendencyComponent,
)
from symcon.core.config import Config, provenance_stamp
from symcon.core.context import Allocator, ComputeContext
from symcon.core.contracts import (
    ContractViolation,
    ContractViolationError,
    ConversionError,
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
    apply_conversion_plan,
    parse_properties,
)
from symcon.core.driver import timeloop
from symcon.core.io import MemoryMonitor, NetCDFMonitor
from symcon.core.profiling import Timer
from symcon.core.registry import Factory, MetaFactory, RegistrationError
from symcon.core.state import (
    NamesRegistryError,
    QuantityDef,
    UnitsError,
    canonical_units,
    convert_array,
    make_dataarray,
    register_quantity,
    units_identical,
    verify_noop,
)
from symcon.core.typing import FieldBuffer, HaloState, Location

__version__ = "0.1.0"

__all__ = [
    "Allocator",
    "CallingFrequency",
    "Component",
    "ComputeContext",
    "Config",
    "ContractViolation",
    "ContractViolationError",
    "ConversionError",
    "ConversionPlan",
    "ConversionStep",
    "DiagnosticComponent",
    "Differentiable",
    "DynamicChecker",
    "EgressPlan",
    "Factory",
    "FieldBuffer",
    "FieldSchema",
    "HaloPolicy",
    "HaloState",
    "ImplicitTendencyComponent",
    "IngressPlan",
    "Location",
    "MemoryMonitor",
    "MetaFactory",
    "Monitor",
    "NamesRegistryError",
    "NetCDFMonitor",
    "OutputSchema",
    "PropertyDictError",
    "PropertySpec",
    "QuantityDef",
    "RegistrationError",
    "ScalingWrapper",
    "StateSchema",
    "StaticChecker",
    "Stepper",
    "Subcycle",
    "TendencyComponent",
    "Timer",
    "UnitsError",
    "apply_conversion_plan",
    "canonical_units",
    "convert_array",
    "make_dataarray",
    "parse_properties",
    "provenance_stamp",
    "register_quantity",
    "timeloop",
    "units_identical",
    "verify_noop",
]
