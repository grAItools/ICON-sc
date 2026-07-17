"""ICON grid NetCDF reader (architecture §3.1, S11) — pure numpy, no gt4py.

Reads the grid files Zonda / the DWD grid generator / the MPI-M grid generator
produce into plain numpy arrays: sizes, ``uuidOfHGrid``, connectivity index tables,
primal/dual geometry, coordinates and ``refin_ctrl``. The variable names, layouts and
index normalization are transcribed from pinned icon4py's ``grid/gridfile.py`` /
``grid/grid_manager.py`` (REFERENCES.lock id ``icon4py-grid-stack``); equivalence with
icon4py's grid object is asserted in ``tests/test_icon_grid_datatest.py``.

Kept free of gt4py imports on purpose (PLAN S11 pitfall): the reader stays reusable in
P4 tooling and keeps the dependency surface of pure ingestion minimal. The gt4py-facing
``IconGrid`` wrapper lives in :mod:`symcon.icon.grid.grid`.

Normalization (identical to icon4py's ``ToZeroBasedIndexTransformation``):

- connectivity tables are stored transposed in the file — ``(sparse, horizontal)`` —
  and 1-based; the reader transposes to ``(horizontal, sparse)`` and subtracts 1,
  keeping the invalid marker ``-1`` untouched;
- ``refin_ctrl`` and orientation tables are read as int32 without index offset;
- coordinates are radians (both MPI-M and DWD files); torus files add cartesian
  center coordinates.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final

import numpy as np
import numpy.typing as npt

__all__ = ["GridFileData", "GridFileError", "read_grid_file"]

_I32 = npt.NDArray[np.int32]
_F64 = npt.NDArray[np.float64]

#: Invalid-neighbor marker used by ICON grid files (pentagon points, LAM boundaries).
INVALID_INDEX: Final[int] = -1

#: File-level connectivities: offset name -> (netCDF variable, target dim, sparse size).
#: (Derived connectivities — E2C2V, E2C2E(O), C2E2C(O)2E(2C) — are *not* in the file;
#: icon4py constructs them and so does the S11 ``IconGrid`` wrapper by delegation.)
_CONNECTIVITY_VARS: Final[Mapping[str, tuple[str, str, int]]] = MappingProxyType(
    {
        "C2E": ("edge_of_cell", "cell", 3),
        "C2V": ("vertex_of_cell", "cell", 3),
        "C2E2C": ("neighbor_cell_index", "cell", 3),
        "E2C": ("adjacent_cell_of_edge", "edge", 2),
        "E2V": ("edge_vertices", "edge", 2),
        "V2E": ("edges_of_vertex", "vertex", 6),
        "V2C": ("cells_of_vertex", "vertex", 6),
        "V2E2V": ("vertices_of_vertex", "vertex", 6),
    }
)

#: refin_ctrl variables per horizontal location.
_REFIN_CTRL_VARS: Final[Mapping[str, str]] = MappingProxyType(
    {"cell": "refin_c_ctrl", "edge": "refin_e_ctrl", "vertex": "refin_v_ctrl"}
)

#: Float geometry variables: name -> (netCDF variable, target dim, sparse size | None).
_GEOMETRY_VARS: Final[Mapping[str, tuple[str, str, int | None]]] = MappingProxyType(
    {
        "cell_area": ("cell_area", "cell", None),
        "dual_area": ("dual_area", "vertex", None),
        "edge_length": ("edge_length", "edge", None),
        "dual_edge_length": ("dual_edge_length", "edge", None),
        "edge_cell_distance": ("edge_cell_distance", "edge", 2),
        "edge_vertex_distance": ("edge_vert_distance", "edge", 2),
        "tangent_orientation": ("edge_system_orientation", "edge", None),
    }
)

#: Integer orientation tables (no index offset — they hold ±1 signs).
_ORIENTATION_VARS: Final[Mapping[str, tuple[str, str, int]]] = MappingProxyType(
    {
        "cell_normal_orientation": ("orientation_of_normal", "cell", 3),
        "vertex_edge_orientation": ("edge_orientation", "vertex", 6),
    }
)

#: Geographic coordinates [rad]; always present.
_COORDINATE_VARS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "cell_lat": "clat",
        "cell_lon": "clon",
        "edge_lat": "elat",
        "edge_lon": "elon",
        "vertex_lat": "vlat",
        "vertex_lon": "vlon",
    }
)

#: Cartesian coordinates, present in torus (planar) grid files.
_TORUS_COORDINATE_VARS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "cell_x": "cell_circumcenter_cartesian_x",
        "cell_y": "cell_circumcenter_cartesian_y",
        "cell_z": "cell_circumcenter_cartesian_z",
        "edge_x": "edge_middle_cartesian_x",
        "edge_y": "edge_middle_cartesian_y",
        "edge_z": "edge_middle_cartesian_z",
        "vertex_x": "cartesian_x_vertices",
        "vertex_y": "cartesian_y_vertices",
        "vertex_z": "cartesian_z_vertices",
    }
)

#: ``grid_geometry`` attribute values (mo_grid_geometry_info.f90 / icon4py GeometryType).
_GEOMETRY_TYPES: Final[Mapping[int, str]] = MappingProxyType({1: "icosahedron", 2: "torus"})


class GridFileError(ValueError):
    """A grid file is missing required content or has an unexpected layout."""


@dataclasses.dataclass(frozen=True)
class GridFileData:
    """Plain-numpy content of one ICON grid NetCDF file (all arrays read-only).

    ``connectivities`` are 0-based ``(horizontal, sparse)`` int32 tables with ``-1``
    marking missing neighbors; ``refin_ctrl`` maps location name to the raw refinement
    control field (all-zeros when the file carries none — ``has_refin_ctrl`` records
    which); ``limited_area`` follows icon4py's criterion (any cell refin_ctrl > 0).
    """

    path: str
    uuid: str
    n_cells: int
    n_edges: int
    n_vertices: int
    grid_root: int
    grid_level: int
    geometry_type: str
    limited_area: bool
    has_refin_ctrl: bool
    connectivities: Mapping[str, _I32]
    refin_ctrl: Mapping[str, _I32]
    geometry: Mapping[str, _F64]
    orientations: Mapping[str, _I32]
    coordinates: Mapping[str, _F64]
    sphere_radius: float | None = None
    domain_length: float | None = None
    domain_height: float | None = None


def _frozen(array: npt.NDArray[Any]) -> npt.NDArray[Any]:
    array.setflags(write=False)
    return array


class _Reader:
    """One open dataset + actionable error reporting."""

    def __init__(self, dataset: Any, path: str) -> None:
        self._ds = dataset
        self._path = path

    def dimension(self, name: str) -> int:
        if name not in self._ds.dimensions:
            raise GridFileError(
                f"{self._path}: required dimension {name!r} is missing — not an ICON "
                f"grid file? (found: {sorted(self._ds.dimensions)[:8]}...)"
            )
        return int(self._ds.dimensions[name].size)

    def attribute(self, name: str) -> Any:
        if name not in self._ds.ncattrs():
            raise GridFileError(
                f"{self._path}: required global attribute {name!r} is missing — "
                f"ICON grid files carry it (DWD icon-tools and MPI-M generators alike)."
            )
        return self._ds.getncattr(name)

    def try_attribute(self, name: str) -> Any | None:
        return self._ds.getncattr(name) if name in self._ds.ncattrs() else None

    def has_variable(self, name: str) -> bool:
        return name in self._ds.variables

    def raw(self, name: str) -> npt.NDArray[Any]:
        if name not in self._ds.variables:
            raise GridFileError(
                f"{self._path}: required variable {name!r} is missing from the grid file."
            )
        return np.asarray(self._ds.variables[name][:])

    def field(
        self,
        name: str,
        target_dim: str,
        target_size: int,
        sparse_size: int | None,
        *,
        dtype: Any,
    ) -> npt.NDArray[Any]:
        """Read + validate a per-``target_dim`` variable, transposing 2-d tables."""
        data = self.raw(name).astype(dtype)
        expected: tuple[int, ...] = (
            (target_size,) if sparse_size is None else (sparse_size, target_size)
        )
        if data.shape != expected:
            raise GridFileError(
                f"{self._path}: variable {name!r} has shape {data.shape}, expected "
                f"{expected} ((sparse, {target_dim}) file layout)."
            )
        return data.T if sparse_size is not None else data


def read_grid_file(path: str | pathlib.Path) -> GridFileData:
    """Read an ICON grid NetCDF file into :class:`GridFileData` (frozen surface, S11).

    Raises ``FileNotFoundError`` for a missing file and :class:`GridFileError` (with
    the offending file and variable/attribute named) for malformed content.
    """
    from netCDF4 import Dataset

    file_path = pathlib.Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"ICON grid file not found: {file_path}")
    try:
        dataset = Dataset(str(file_path), "r", format="NETCDF4")
    except OSError as exc:
        raise GridFileError(f"{file_path}: not a readable NetCDF file ({exc}).") from exc
    try:
        return _read(_Reader(dataset, str(file_path)))
    finally:
        dataset.close()


def _read(reader: _Reader) -> GridFileData:
    n_cells = reader.dimension("cell")
    n_edges = reader.dimension("edge")
    n_vertices = reader.dimension("vertex")
    sizes = {"cell": n_cells, "edge": n_edges, "vertex": n_vertices}

    uuid = str(reader.attribute("uuidOfHGrid"))
    grid_root = int(reader.attribute("grid_root"))
    grid_level = int(reader.attribute("grid_level"))

    raw_geometry_type = reader.try_attribute("grid_geometry")
    if raw_geometry_type is None:
        geometry_type = "icosahedron"  # DWD files carry no MPI-M geometry attribute
    else:
        try:
            geometry_type = _GEOMETRY_TYPES[int(raw_geometry_type)]
        except (KeyError, ValueError):
            raise GridFileError(
                f"{reader._path}: unknown grid_geometry={raw_geometry_type!r} "
                f"(known: {dict(_GEOMETRY_TYPES)})."
            ) from None

    connectivities: dict[str, _I32] = {}
    for offset, (var, target_dim, sparse) in _CONNECTIVITY_VARS.items():
        table = reader.field(var, target_dim, sizes[target_dim], sparse, dtype=np.int32)
        # 1-based Fortran -> 0-based, invalid entries stay INVALID_INDEX.
        table = np.where(table == INVALID_INDEX, INVALID_INDEX, table - 1).astype(np.int32)
        connectivities[offset] = _frozen(table)

    has_refin_ctrl = all(reader.has_variable(var) for var in _REFIN_CTRL_VARS.values())
    refin_ctrl: dict[str, _I32] = {}
    for location, var in _REFIN_CTRL_VARS.items():
        if has_refin_ctrl:
            field = reader.field(var, location, sizes[location], None, dtype=np.int32)
        else:  # absent-but-defaulted (SPEC acceptance 5): interior everywhere
            field = np.zeros(sizes[location], dtype=np.int32)
        refin_ctrl[location] = _frozen(field)

    geometry: dict[str, _F64] = {
        name: _frozen(reader.field(var, target_dim, sizes[target_dim], sparse, dtype=np.float64))
        for name, (var, target_dim, sparse) in _GEOMETRY_VARS.items()
    }
    orientations: dict[str, _I32] = {
        name: _frozen(reader.field(var, target_dim, sizes[target_dim], sparse, dtype=np.int32))
        for name, (var, target_dim, sparse) in _ORIENTATION_VARS.items()
    }

    coordinate_vars = dict(_COORDINATE_VARS)
    if geometry_type == "torus":
        coordinate_vars.update(_TORUS_COORDINATE_VARS)
    coordinates: dict[str, _F64] = {
        name: _frozen(
            reader.field(var, name.split("_")[0], sizes[name.split("_")[0]], None, dtype=np.float64)
        )
        for name, var in coordinate_vars.items()
    }

    sphere_radius = reader.try_attribute("sphere_radius")
    domain_length = reader.try_attribute("domain_length")
    domain_height = reader.try_attribute("domain_height")

    return GridFileData(
        path=reader._path,
        uuid=uuid,
        n_cells=n_cells,
        n_edges=n_edges,
        n_vertices=n_vertices,
        grid_root=grid_root,
        grid_level=grid_level,
        geometry_type=geometry_type,
        # icon4py grid_refinement.is_limited_area_grid: boundary points exist.
        limited_area=bool(np.any(refin_ctrl["cell"] > 0)),
        has_refin_ctrl=has_refin_ctrl,
        connectivities=MappingProxyType(connectivities),
        refin_ctrl=MappingProxyType(refin_ctrl),
        geometry=MappingProxyType(geometry),
        orientations=MappingProxyType(orientations),
        coordinates=MappingProxyType(coordinates),
        sphere_radius=None if sphere_radius is None else float(sphere_radius),
        domain_length=None if domain_length is None else float(domain_length),
        domain_height=None if domain_height is None else float(domain_height),
    )
