"""ICON components hosted on symcon.core (architecture §4.3; S07+).

Subpackages mirror ICON's process taxonomy: :mod:`symcon.icon.components.fast`
(fast physics, every Δt, sequential-update split);
:mod:`symcon.icon.components.dycore` (S12: the icon4py nonhydrostatic solver as a
``DynamicalCore``); :mod:`symcon.icon.components.diffusion` (S13: the icon4py
horizontal-diffusion granule as a ``Stepper``). Real slow physics and transport
arrive with their own steps; :mod:`symcon.icon.components.idealized` carries the
S09 analytic stand-ins that exercise the slow-tendency bus.
"""

from symcon.icon.components.diffusion import (
    DiffusionConfig,
    HorizontalDiffusion,
)
from symcon.icon.components.dycore import (
    NonhydroConfig,
    NonhydroSolver,
    icon_namelist_origins,
)
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
    "DiffusionConfig",
    "Graupel",
    "GraupelConfig",
    "HorizontalDiffusion",
    "Microphysics",
    "NonhydroConfig",
    "NonhydroSolver",
    "PrescribedCooling",
    "PrescribedCoolingConfig",
    "SaturationAdjustment",
    "SaturationAdjustmentConfig",
    "icon_namelist_origins",
]
