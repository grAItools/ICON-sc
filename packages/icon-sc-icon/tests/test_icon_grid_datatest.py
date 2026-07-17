"""S11 acceptance on real ICON grid files (marker ``data``).

- acceptance 1: reader round-trip — counts, dims, dtypes, uuid — on the global
  R02B04 grid (the horizontal grid of icon4py's JW/driver datatest) and the regional
  mch_ch_R04B09_DOM01 grid;
- acceptance 2: connectivity cross-check — the pure-numpy reader's index tables vs
  icon4py's grid object for the same file (independent ingestion paths);
- acceptance 4: ``grid.offset_providers`` accepted by a trivial gt4py neighbor-sum
  program on both backends (gpu leg marked, skips without a device);
- acceptance 5: refin_ctrl on both grids (regional: boundary zones populated; global:
  retained, no boundary points — the absent-variable default is unit-tested in
  test_grid_reader.py).

Grid files download through icon4py's datatest machinery (~15 MB each, cached under
``~/.cache/symcon/icon4py-testdata/grids``); no serialized experiment archive needed.
"""

from __future__ import annotations

import gt4py.next as gtx
import numpy as np
import pytest
from gt4py.next import neighbor_sum
from icon4py.model.common.dimension import C2E, C2EDim, CellDim, EdgeDim

from symcon.core.context import ComputeContext
from symcon.core.ingress.gt4py import make_backend
from symcon.icon.grid import from_file, read_grid_file
from symcon.icon.testing import DATATEST_AVAILABLE, download_grid_file

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (symcon-icon[datatest])",
    ),
]

#: File-sourced connectivities (present verbatim in the grid file).
_FILE_OFFSETS = ("C2E", "C2V", "C2E2C", "E2C", "E2V", "V2E", "V2C", "V2E2V")
#: icon4py-derived connectivities the wrapper must also expose.
_DERIVED_OFFSETS = ("E2C2V", "E2C2E", "E2C2EO", "C2E2CO", "C2E2C2E", "C2E2C2E2C")

_GRID_IDS = ("R02B04_GLOBAL", "MCH_CH_R04B09_DSL")


@pytest.fixture(scope="module", params=_GRID_IDS)
def grid_case(request):
    """(grid description, downloaded file path) for both S11 grids."""
    from icon4py.model.testing import definitions

    description = getattr(definitions.Grids, request.param)
    return description, download_grid_file(description)


@pytest.fixture(scope="module")
def file_data(grid_case):
    return read_grid_file(grid_case[1])


@pytest.fixture(scope="module")
def icon_grid_wrapped(grid_case):
    return from_file(grid_case[1], None, num_levels=4)


def test_reader_round_trip_counts_and_uuid(grid_case, file_data) -> None:
    """Acceptance 1 on real files: sizes consistent, uuid preserved, dtypes right."""
    import netCDF4

    _, path = grid_case
    with netCDF4.Dataset(path) as ds:
        assert file_data.n_cells == ds.dimensions["cell"].size
        assert file_data.n_edges == ds.dimensions["edge"].size
        assert file_data.n_vertices == ds.dimensions["vertex"].size
        assert file_data.uuid == ds.getncattr("uuidOfHGrid")
    # Euler characteristic of a closed/bounded triangulation: sanity of the trio.
    assert file_data.n_cells + file_data.n_vertices - file_data.n_edges in (2, 1)
    sizes = {
        "cell": file_data.n_cells,
        "edge": file_data.n_edges,
        "vertex": file_data.n_vertices,
    }
    for name, table in file_data.connectivities.items():
        assert table.dtype == np.int32, name
        assert table.ndim == 2 and table.shape[0] in sizes.values(), name
        assert table.max() < max(sizes.values())
        assert table.min() >= -1
    for location, size in sizes.items():
        assert file_data.refin_ctrl[location].shape == (size,)
        assert file_data.coordinates[f"{location}_lat"].shape == (size,)
        assert file_data.coordinates[f"{location}_lon"].shape == (size,)
    assert file_data.geometry_type == "icosahedron"
    assert file_data.grid_root > 0 and file_data.grid_level > 0


def test_wrapper_matches_reader_identity(grid_case, file_data, icon_grid_wrapped) -> None:
    grid = icon_grid_wrapped
    assert grid.uuid == file_data.uuid
    assert (grid.n_cells, grid.n_edges, grid.n_vertices) == (
        file_data.n_cells,
        file_data.n_edges,
        file_data.n_vertices,
    )
    assert grid.limited_area == file_data.limited_area
    assert grid.geometry_type == file_data.geometry_type


def test_connectivity_cross_check_reader_vs_icon4py(file_data, icon_grid_wrapped) -> None:
    """Acceptance 2: identical index arrays from the two ingestion paths.

    The wrapper delegates to icon4py's GridManager (``keep_skip_values=True``: raw
    ``-1`` preserved); the reader is an independent pure-numpy transcription — both
    normalize the file's 1-based Fortran indices identically.
    """
    for name in _FILE_OFFSETS:
        np.testing.assert_array_equal(
            icon_grid_wrapped.connectivities[name],
            file_data.connectivities[name],
            err_msg=name,
        )
    for name in _DERIVED_OFFSETS:
        assert name in icon_grid_wrapped.connectivities, name


def test_refin_ctrl_retained(grid_case, file_data, icon_grid_wrapped) -> None:
    """Acceptance 5 (see module docstring for the global-grid nuance)."""
    description, _ = grid_case
    for location in ("cell", "edge", "vertex"):
        np.testing.assert_array_equal(
            icon_grid_wrapped.refin_ctrl[location], file_data.refin_ctrl[location]
        )
    if description.limited_area:
        assert file_data.limited_area
        assert (file_data.refin_ctrl["cell"] > 0).any()  # lateral boundary zones
    else:
        # The global R02B04 file carries refin_ctrl (nest-parent values <= 0) — no
        # boundary zones; files without the variables default to zeros (unit test).
        assert not file_data.limited_area
        assert not (file_data.refin_ctrl["cell"] > 0).any()


def test_geometry_named_fields(icon_grid_wrapped) -> None:
    """§3.1 geometry surface: edge/dual lengths, areas, orientation, coriolis."""
    geometry = icon_grid_wrapped.geometry
    n_cells = icon_grid_wrapped.n_cells
    n_edges = icon_grid_wrapped.n_edges
    n_vertices = icon_grid_wrapped.n_vertices
    assert geometry.cell_area.shape == (n_cells,)
    assert geometry.dual_area.shape == (n_vertices,)
    assert geometry.edge_length.shape == (n_edges,)
    assert geometry.dual_edge_length.shape == (n_edges,)
    assert geometry.edge_area.shape == (n_edges,)
    assert geometry.vertex_vertex_length.shape == (n_edges,)
    assert geometry.tangent_orientation.shape == (n_edges,)
    assert geometry.coriolis_parameter.shape == (n_edges,)
    assert (geometry.cell_area > 0).all()
    assert (geometry.edge_length > 0).all()
    assert set(np.unique(geometry.tangent_orientation)) <= {-1.0, 1.0}
    # |f| <= 2 Omega
    assert np.abs(geometry.coriolis_parameter).max() <= 1.5e-4
    assert not geometry.cell_area.flags.writeable
    with pytest.raises(AttributeError, match="unknown geometry field"):
        geometry.get("no_such_field")


@gtx.field_operator
def _edge_sum_to_cells(
    edge_field: gtx.Field[gtx.Dims[EdgeDim], gtx.float64],
) -> gtx.Field[gtx.Dims[CellDim], gtx.float64]:
    return neighbor_sum(edge_field(C2E), axis=C2EDim)


def test_offset_providers_accepted_by_neighbor_sum(grid_case, backend) -> None:
    """Acceptance 4: a trivial gt4py neighbor-sum runs with ``grid.offset_providers``
    on every backend leg (embedded / gtfn_cpu / gpu-marked gtfn_gpu)."""
    _, path = grid_case
    ctx = ComputeContext(backend=make_backend(backend))
    grid = from_file(path, ctx, num_levels=1)

    rng = np.random.default_rng(42)
    edge_values = rng.random(grid.n_edges)
    xp = np if backend != "gtfn_gpu" else pytest.importorskip("cupy")
    edge_field = gtx.as_field((EdgeDim,), xp.asarray(edge_values))
    out = gtx.zeros({CellDim: grid.n_cells}, dtype=gtx.float64, allocator=ctx.backend.gt4py_backend)
    op = _edge_sum_to_cells.with_backend(ctx.backend.gt4py_backend)
    op(edge_field, out=out, offset_provider=grid.offset_providers)

    c2e = grid.connectivities["C2E"]
    expected = np.where(c2e >= 0, edge_values[c2e], 0.0).sum(axis=1)
    np.testing.assert_allclose(np.asarray(out.asnumpy()), expected, rtol=0, atol=0)
