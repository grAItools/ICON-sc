"""ICON components hosted on symcon.core (architecture §4.3; S07+).

Subpackages mirror ICON's process taxonomy: :mod:`symcon.icon.components.fast`
(fast physics, every Δt, sequential-update split). Real slow physics, dycore and
transport arrive with their own steps; :mod:`symcon.icon.components.idealized`
carries the S09 analytic stand-ins that exercise the slow-tendency bus.
"""

from symcon.icon.components.fast import (
    Graupel,
    GraupelConfig,
    Microphysics,
    SaturationAdjustment,
    SaturationAdjustmentConfig,
)
from symcon.icon.components.idealized import (
    ApplySlowTendencies,
    PrescribedCooling,
    PrescribedCoolingConfig,
)

__all__ = [
    "ApplySlowTendencies",
    "Graupel",
    "GraupelConfig",
    "Microphysics",
    "PrescribedCooling",
    "PrescribedCoolingConfig",
    "SaturationAdjustment",
    "SaturationAdjustmentConfig",
]
