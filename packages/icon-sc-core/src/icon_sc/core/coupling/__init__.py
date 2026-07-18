"""The coupling algebra (architecture §4.2, after Tasmania): couplings, steppers,
federations, the slow-tendency bus and coupling constraints."""

from icon_sc.core.coupling.bus import BusError, SlowTendencyBus, TendencySlot
from icon_sc.core.coupling.concurrent import ConcurrentCoupling
from icon_sc.core.coupling.constraints import (
    CouplingConstraintError,
    CouplingConstraints,
    constraints_of,
    validate_composition,
)
from icon_sc.core.coupling.dictops import dict_axpy, dict_fma
from icon_sc.core.coupling.federations import (
    SSUS,
    ParallelSplitting,
    SequentialTendencySplitting,
    SequentialUpdateSplitting,
)
from icon_sc.core.coupling.steppers import SequentialTendencyStepper, TendencyStepper

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
