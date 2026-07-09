"""The coupling algebra (architecture §4.2, after Tasmania): couplings, steppers,
federations, the slow-tendency bus and coupling constraints."""

from symcon.core.coupling.bus import BusError, SlowTendencyBus, TendencySlot
from symcon.core.coupling.concurrent import ConcurrentCoupling
from symcon.core.coupling.constraints import (
    CouplingConstraintError,
    CouplingConstraints,
    constraints_of,
    validate_composition,
)
from symcon.core.coupling.dictops import dict_axpy, dict_fma
from symcon.core.coupling.federations import (
    SSUS,
    ParallelSplitting,
    SequentialTendencySplitting,
    SequentialUpdateSplitting,
)
from symcon.core.coupling.steppers import SequentialTendencyStepper, TendencyStepper

__all__ = [
    "SSUS",
    "BusError",
    "ConcurrentCoupling",
    "CouplingConstraintError",
    "CouplingConstraints",
    "ParallelSplitting",
    "SequentialTendencySplitting",
    "SequentialTendencyStepper",
    "SequentialUpdateSplitting",
    "SlowTendencyBus",
    "TendencySlot",
    "TendencyStepper",
    "constraints_of",
    "dict_axpy",
    "dict_fma",
    "validate_composition",
]
