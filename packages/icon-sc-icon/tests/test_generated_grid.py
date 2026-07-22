"""Task 26: generated synthetic grids through the ICON-sc grid stack.

The compatibility contract with the optional ``icon-grid-generator`` package
(``icon-sc-icon[gridgen]``, pinned in constraints/cpu-ci.txt): a generated
ICON-style file must load through the S11 reader and ``from_file`` (icon4py
``GridManager``), build offset providers, and feed the metrics/interpolation
factories to all-finite fields. If either side drifts — a generator release
changing its NetCDF payload, or a icon_sc/icon4py reader change — these tests
localize the break.

Boundary (do not blur it): generated grids are NOT numerically equivalent to
official DWD gridgen output. They must never appear in savepoint-parity tests;
their role is archive-independent fixtures (reader/factory smoke, convergence
ladders, torus experiments).
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("grid_generator")

import icon_sc.icon.names  # noqa: F401  (registry seed side effect)
from icon_sc.core import ComputeContext
from icon_sc.icon.grid import interpolation, metrics
from icon_sc.icon.grid.reader import read_grid_file
from icon_sc.icon.grid.vertical import SLEVEConfig, VerticalGrid
from icon_sc.icon.testing import generated_grid, generated_grid_file

#: Smallest spec exercising real global topology (12 pentagon points included).
SPEC = "R2B2"
N_CELLS, N_EDGES, N_VERTICES = 1280, 1920, 642
NUM_LEVELS = 35


def test_generated_file_reads_through_reader() -> None:
    raw = read_grid_file(str(generated_grid_file(SPEC)))
    connectivities = raw.connectivities
    assert connectivities["C2E"].shape == (N_CELLS, 3)
    assert connectivities["C2V"].shape == (N_CELLS, 3)
    assert connectivities["E2C"].shape == (N_EDGES, 2)
    assert raw.coordinates["vertex_lat"].shape == (N_VERTICES,)
    # S11 normalization contract: 0-based with -1 as the invalid marker.
    for name, table in connectivities.items():
        assert table.min() >= -1, f"{name} violates 0-based/-1 normalization"
    assert raw.uuid  # uuidOfHGrid present (generator stamps a deterministic uuid5)


def test_generation_is_deterministic(tmp_path: object) -> None:
    """uuid AND content are bitwise-stable across independent generations."""
    import pathlib

    base = pathlib.Path(str(tmp_path))
    raw_a = read_grid_file(str(generated_grid_file(SPEC, cache_dir=base / "a")))
    raw_b = read_grid_file(str(generated_grid_file(SPEC, cache_dir=base / "b")))
    assert raw_a.uuid == raw_b.uuid
    for name in ("C2E", "C2V", "E2C"):
        np.testing.assert_array_equal(raw_a.connectivities[name], raw_b.connectivities[name])
    for name, values in raw_a.coordinates.items():
        np.testing.assert_array_equal(values, raw_b.coordinates[name], err_msg=name)


def test_icongrid_offset_providers_and_refin_ctrl() -> None:
    grid = generated_grid(SPEC, num_levels=NUM_LEVELS)
    providers = grid.offset_providers
    for key in ("C2E", "C2V", "E2C", "C2E2C", "E2C2E", "Koff"):
        assert key in providers, f"offset provider {key} missing"
    # Global generated grid: refin_ctrl present for all three locations, and the
    # domain is a single global patch (no nest boundary zones, values <= 0).
    for location in ("cell", "edge", "vertex"):
        values = grid.refin_ctrl[location]
        assert values.shape[0] > 0
        assert values.max() <= 0, f"unexpected nest-boundary refin_ctrl on {location}"


@pytest.mark.slow
@pytest.mark.parametrize(
    "backend",
    ["gtfn_cpu", pytest.param("gtfn_gpu", marks=pytest.mark.gpu)],
)
def test_factories_all_finite_on_generated_grid(backend: str) -> None:
    """The S12/S13 static-state set computes finitely on a generated grid.

    slow: first run per grid size compiles gtfn variants into the persistent
    cache. The icon4py factories do not support the embedded backend upstream
    (``embedded_remap_error``), hence gtfn only.
    """
    ctx = ComputeContext(backend)
    grid = generated_grid(SPEC, ctx=ctx, num_levels=NUM_LEVELS)
    vgrid = VerticalGrid.from_config(SLEVEConfig(num_levels=NUM_LEVELS))

    metric_fields = metrics(grid, vgrid)
    interpolation_fields = interpolation(grid)

    assert len(metric_fields) == 38
    assert len(interpolation_fields) == 16
    for name, field in {**metric_fields, **interpolation_fields}.items():
        values = np.asarray(field.data) if backend != "gtfn_gpu" else field.data.get()
        assert np.isfinite(values).all(), f"non-finite values in {name}"
