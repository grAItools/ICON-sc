"""icon_sc.icon grid stack (architecture §3).

S06 ships the vertical grid; S11 adds the horizontal grid on real ICON grid files —
the pure NetCDF reader, ``IconGrid`` (:func:`from_file`), named geometry, and the
metrics/interpolation static-state factories.
"""

from icon_sc.icon.grid.geometry import Geometry
from icon_sc.icon.grid.grid import IconGrid, from_file
from icon_sc.icon.grid.interpolation import INTERPOLATION_FIELDS, interpolation
from icon_sc.icon.grid.metrics import METRICS_FIELDS, metrics
from icon_sc.icon.grid.reader import GridFileData, GridFileError, read_grid_file
from icon_sc.icon.grid.vertical import (
    SLEVEConfig,
    VerticalGrid,
    compute_vct_a_and_vct_b,
    reference_exner,
    reference_potential_temperature,
    reference_pressure,
    reference_rho,
    reference_temperature,
)

__all__ = [
    "INTERPOLATION_FIELDS",
    "METRICS_FIELDS",
    "Geometry",
    "GridFileData",
    "GridFileError",
    "IconGrid",
    "SLEVEConfig",
    "VerticalGrid",
    "compute_vct_a_and_vct_b",
    "from_file",
    "interpolation",
    "metrics",
    "read_grid_file",
    "reference_exner",
    "reference_potential_temperature",
    "reference_pressure",
    "reference_rho",
    "reference_temperature",
]
