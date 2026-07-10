"""ICON components hosted on symcon.core (architecture §4.3; S07+).

Subpackages mirror ICON's process taxonomy: :mod:`symcon.icon.components.fast`
(fast physics, every Δt, sequential-update split). Slow physics, dycore and
transport arrive with their own steps.
"""

from symcon.icon.components.fast import (
    Graupel,
    GraupelConfig,
    Microphysics,
    SaturationAdjustment,
    SaturationAdjustmentConfig,
)

__all__ = [
    "Graupel",
    "GraupelConfig",
    "Microphysics",
    "SaturationAdjustment",
    "SaturationAdjustmentConfig",
]
