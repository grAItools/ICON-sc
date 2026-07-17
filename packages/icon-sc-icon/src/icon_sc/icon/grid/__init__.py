"""symcon.icon grid stack (architecture §3).

S06 ships the vertical grid; S11 adds the horizontal grid on real ICON grid files —
the pure NetCDF reader, ``IconGrid`` (:func:`from_file`), named geometry, and the
metrics/interpolation static-state factories.
"""

from symcon.icon.grid.geometry import Geometry
from symcon.icon.grid.grid import IconGrid, from_file
from symcon.icon.grid.interpolation import INTERPOLATION_FIELDS, interpolation
from symcon.icon.grid.metrics import METRICS_FIELDS, metrics
from symcon.icon.grid.reader import GridFileData, GridFileError, read_grid_file
from symcon.icon.grid.vertical import (
    SleveConfig,
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
    "SleveConfig",
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
