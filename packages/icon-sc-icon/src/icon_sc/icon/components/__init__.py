"""ICON components hosted on icon_sc.core (architecture §4.3; S07+).

Subpackages mirror ICON's process taxonomy: :mod:`icon_sc.icon.components.fast`
(fast physics, every Δt, sequential-update split);
:mod:`icon_sc.icon.components.dycore` (S12: the icon4py nonhydrostatic solver as a
``DynamicalCore``); :mod:`icon_sc.icon.components.diffusion` (S13: the icon4py
horizontal-diffusion granule as a ``Stepper``). Real slow physics and transport
arrive with their own steps; :mod:`icon_sc.icon.components.idealized` carries the
S09 analytic stand-ins that exercise the slow-tendency bus.
"""

from icon_sc.icon.components.diffusion import (
    DiffusionConfig,
    HorizontalDiffusion,
)
from icon_sc.icon.components.dycore import (
    NonhydroConfig,
    NonhydroSolver,
    icon_namelist_origins,
)
from icon_sc.icon.components.fast import (
    Graupel,
    GraupelConfig,
    Microphysics,
    SaturationAdjustment,
    SaturationAdjustmentConfig,
)
from icon_sc.icon.components.idealized import (
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
