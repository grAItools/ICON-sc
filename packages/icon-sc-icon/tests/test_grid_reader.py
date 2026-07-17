"""S11 reader unit tests on synthetic grid files (SPEC acceptance 1: dtypes, index
normalization, actionable malformed-file errors; acceptance 5: refin_ctrl
absent-but-defaulted). Real-grid round-trips live in test_icon_grid_datatest.py."""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from icon_sc.icon.grid.reader import GridFileData, GridFileError, read_grid_file

netCDF4 = pytest.importorskip("netCDF4")

# Arbitrary (topologically meaningless) sizes: the reader validates layout, not
# mesh consistency.
N_CELLS, N_EDGES, N_VERTICES = 4, 9, 6

#: (variable, first dim, sparse dim or None, integer?) — the full required set.
_VARIABLES: tuple[tuple[str, str, str | None, bool], ...] = (
    ("edge_of_cell", "nv", "cell", True),
    ("vertex_of_cell", "nv", "cell", True),
    ("neighbor_cell_index", "nv", "cell", True),
    ("adjacent_cell_of_edge", "nc", "edge", True),
    ("edge_vertices", "nc", "edge", True),
    ("edges_of_vertex", "ne", "vertex", True),
    ("cells_of_vertex", "ne", "vertex", True),
    ("vertices_of_vertex", "ne", "vertex", True),
    ("cell_area", "cell", None, False),
    ("dual_area", "vertex", None, False),
    ("edge_length", "edge", None, False),
    ("dual_edge_length", "edge", None, False),
    ("edge_cell_distance", "nc", "edge", False),
    ("edge_vert_distance", "nc", "edge", False),
    ("edge_system_orientation", "edge", None, True),
    ("orientation_of_normal", "nv", "cell", True),
    ("edge_orientation", "ne", "vertex", True),
    ("clat", "cell", None, False),
    ("clon", "cell", None, False),
    ("elat", "edge", None, False),
    ("elon", "edge", None, False),
    ("vlat", "vertex", None, False),
    ("vlon", "vertex", None, False),
)

_UUID = "deadbeef-0000-1111-2222-333344445555"


def _write_grid_file(
    path: pathlib.Path,
    *,
    with_refin_ctrl: bool = True,
    refin_c_value: int = 0,
    skip_variables: tuple[str, ...] = (),
    skip_attributes: tuple[str, ...] = (),
    seed: int = 0,
) -> pathlib.Path:
    rng = np.random.default_rng(seed)
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("cell", N_CELLS)
        ds.createDimension("edge", N_EDGES)
        ds.createDimension("vertex", N_VERTICES)
        ds.createDimension("nv", 3)
        ds.createDimension("nc", 2)
        ds.createDimension("ne", 6)
        sizes = {
            "cell": N_CELLS,
            "edge": N_EDGES,
            "vertex": N_VERTICES,
            "nv": 3,
            "nc": 2,
            "ne": 6,
        }
        for attr, value in (
            ("uuidOfHGrid", _UUID),
            ("grid_root", 2),
            ("grid_level", 4),
        ):
            if attr not in skip_attributes:
                ds.setncattr(attr, value)
        for name, dim0, dim1, integer in _VARIABLES:
            if name in skip_variables:
                continue
            dims = (dim0,) if dim1 is None else (dim0, dim1)
            shape = tuple(sizes[d] for d in dims)
            if integer:
                # 1-based indices with one invalid (-1) entry per table.
                data = rng.integers(1, 4, size=shape).astype(np.int32)
                data.flat[0] = -1
                var = ds.createVariable(name, "i4", dims)
            else:
                data = rng.random(shape)
                var = ds.createVariable(name, "f8", dims)
            var[:] = data
        if with_refin_ctrl:
            for name, dim in (
                ("refin_c_ctrl", "cell"),
                ("refin_e_ctrl", "edge"),
                ("refin_v_ctrl", "vertex"),
            ):
                var = ds.createVariable(name, "i4", (dim,))
                var[:] = np.full(sizes[dim], refin_c_value if dim == "cell" else 0, np.int32)
    return path


@pytest.fixture
def grid_file(tmp_path: pathlib.Path) -> pathlib.Path:
    return _write_grid_file(tmp_path / "synthetic_grid.nc")


def test_round_trip_counts_dims_dtypes(grid_file: pathlib.Path) -> None:
    data = read_grid_file(grid_file)
    assert isinstance(data, GridFileData)
    assert (data.n_cells, data.n_edges, data.n_vertices) == (N_CELLS, N_EDGES, N_VERTICES)
    assert data.uuid == _UUID
    assert (data.grid_root, data.grid_level) == (2, 4)
    assert data.geometry_type == "icosahedron"  # no MPI-M attribute -> default
    expected_shapes = {
        "C2E": (N_CELLS, 3),
        "C2V": (N_CELLS, 3),
        "C2E2C": (N_CELLS, 3),
        "E2C": (N_EDGES, 2),
        "E2V": (N_EDGES, 2),
        "V2E": (N_VERTICES, 6),
        "V2C": (N_VERTICES, 6),
        "V2E2V": (N_VERTICES, 6),
    }
    assert set(data.connectivities) == set(expected_shapes)
    for name, table in data.connectivities.items():
        assert table.shape == expected_shapes[name], name
        assert table.dtype == np.int32, name
        assert not table.flags.writeable
    for array in (*data.geometry.values(), *data.coordinates.values()):
        assert array.dtype == np.float64
        assert not array.flags.writeable


def test_index_normalization_zero_based_invalid_kept(tmp_path: pathlib.Path) -> None:
    """1-based -> 0-based; INVALID_INDEX=-1 passes through untouched (icon4py rule)."""
    path = _write_grid_file(tmp_path / "grid.nc", seed=7)
    data = read_grid_file(path)
    with netCDF4.Dataset(path) as ds:
        raw = np.asarray(ds.variables["edge_of_cell"][:]).T
    expected = np.where(raw == -1, -1, raw - 1)
    np.testing.assert_array_equal(data.connectivities["C2E"], expected)
    assert (data.connectivities["C2E"] == -1).any()  # the planted invalid entry


def test_refin_ctrl_present_and_limited_area(tmp_path: pathlib.Path) -> None:
    data = read_grid_file(
        _write_grid_file(tmp_path / "lam.nc", with_refin_ctrl=True, refin_c_value=3)
    )
    assert data.has_refin_ctrl
    assert data.limited_area  # boundary points (refin_ctrl > 0) exist
    assert set(data.refin_ctrl) == {"cell", "edge", "vertex"}
    assert data.refin_ctrl["cell"].dtype == np.int32


def test_refin_ctrl_absent_but_defaulted(tmp_path: pathlib.Path) -> None:
    """SPEC acceptance 5: a file without refin_ctrl reads as all-interior zeros."""
    data = read_grid_file(_write_grid_file(tmp_path / "global.nc", with_refin_ctrl=False))
    assert not data.has_refin_ctrl
    assert not data.limited_area
    for location, size in (("cell", N_CELLS), ("edge", N_EDGES), ("vertex", N_VERTICES)):
        np.testing.assert_array_equal(data.refin_ctrl[location], np.zeros(size, np.int32))


def test_missing_file_raises_file_not_found(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"no_such_grid\.nc"):
        read_grid_file(tmp_path / "no_such_grid.nc")


def test_not_a_netcdf_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "garbage.nc"
    path.write_bytes(b"this is not netcdf")
    with pytest.raises(GridFileError, match="not a readable NetCDF"):
        read_grid_file(path)


def test_missing_dimension_is_actionable(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "no_dims.nc"
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("cell", 3)
    with pytest.raises(GridFileError, match="dimension 'edge'"):
        read_grid_file(path)


def test_missing_connectivity_variable_is_actionable(tmp_path: pathlib.Path) -> None:
    path = _write_grid_file(tmp_path / "no_c2e.nc", skip_variables=("edge_of_cell",))
    with pytest.raises(GridFileError, match="'edge_of_cell'"):
        read_grid_file(path)


def test_missing_uuid_is_actionable(tmp_path: pathlib.Path) -> None:
    path = _write_grid_file(tmp_path / "no_uuid.nc", skip_attributes=("uuidOfHGrid",))
    with pytest.raises(GridFileError, match="'uuidOfHGrid'"):
        read_grid_file(path)


def test_bad_variable_shape_is_actionable(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "bad_shape.nc"
    _write_grid_file(path)
    with netCDF4.Dataset(path, "a") as ds:
        ds.renameVariable("cell_area", "cell_area_orig")
        var = ds.createVariable("cell_area", "f8", ("edge",))
        var[:] = np.zeros(N_EDGES)
    with pytest.raises(GridFileError, match="cell_area"):
        read_grid_file(path)


def test_from_file_missing_file(tmp_path: pathlib.Path) -> None:
    from icon_sc.icon.grid import from_file

    with pytest.raises(FileNotFoundError, match=r"nowhere\.nc"):
        from_file(tmp_path / "nowhere.nc", None)


def test_from_file_rejects_bad_num_levels(tmp_path: pathlib.Path) -> None:
    from icon_sc.icon.grid import from_file

    path = _write_grid_file(tmp_path / "grid.nc")
    with pytest.raises(ValueError, match="num_levels"):
        from_file(path, None, num_levels=0)
