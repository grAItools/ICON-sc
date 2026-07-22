"""S06 acceptance 4 (marker ``data``): VerticalGrid reproduces the vertical
coordinate table of an icon4py datatest grid savepoint to 1e-12.

Experiment: GAUSS3D (``exclaim_gauss3d``) — the smallest serialized archive (~57 MB;
the alternatives are 4-7 GB). Download/caching is handled by icon4py's own datatest
machinery (pooch-style, cached under ``ICON4PY_TEST_DATA_PATH``, default
``~/.cache/icon-sc/icon4py-testdata``); no data touches git. Requires the
``icon-sc-icon[datatest]`` extra — skips cleanly without it.
"""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.testing import assert_allclose
from icon_sc.icon.grid.vertical import SLEVEConfig, VerticalGrid
from icon_sc.icon.testing import DATATEST_AVAILABLE

if DATATEST_AVAILABLE:
    # Re-exported icon4py fixtures (fixture *names* are what pytest resolves — the
    # icon4py `backend` fixture intentionally shadows ICON-sc's string-valued one
    # inside this module). experiment_description defaults to GAUSS3D via the bridge.
    from icon_sc.icon.testing import (  # noqa: F401
        backend,
        data_provider,
        download_ser_data,
        experiment,
        experiment_description,
        grid_savepoint,
        process_props,
    )

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

#: SPEC S06 acceptance-4 tolerance contract.
RTOL = 1e-12


@pytest.fixture
def savepoint_tables(grid_savepoint) -> tuple[np.ndarray, np.ndarray]:
    return (
        grid_savepoint.vct_a().asnumpy().astype(np.float64),
        grid_savepoint.vct_b().asnumpy().astype(np.float64),
    )


def test_vertical_grid_reproduces_savepoint_table(
    savepoint_tables: tuple[np.ndarray, np.ndarray],
    experiment,
) -> None:
    """Compute vct_a/vct_b from the experiment's namelist parameters through ICON-sc's
    SLEVE path and compare against the serialized ICON table."""
    vct_a_ref, vct_b_ref = savepoint_tables
    i4_cfg = experiment.config.vertical_grid
    config = SLEVEConfig(
        num_levels=i4_cfg.num_levels,
        lowest_layer_thickness=i4_cfg.lowest_layer_thickness,
        maximal_layer_thickness=i4_cfg.maximal_layer_thickness,
        top_height_limit_for_maximal_layer_thickness=(
            i4_cfg.top_height_limit_for_maximal_layer_thickness
        ),
        model_top_height=i4_cfg.model_top_height,
        flat_height=i4_cfg.flat_height,
        stretch_factor=i4_cfg.stretch_factor,
        rayleigh_damping_height=i4_cfg.rayleigh_damping_height,
        htop_moist_proc=i4_cfg.htop_moist_proc,
    )
    grid = VerticalGrid.from_config(config)
    assert grid.nlev == i4_cfg.num_levels
    assert_allclose(grid.vct_a, vct_a_ref, rtol=RTOL, atol=0.0, names="vct_a")
    assert grid.vct_b is not None
    assert_allclose(grid.vct_b, vct_b_ref, rtol=RTOL, atol=0.0, names="vct_b")


def test_ingested_savepoint_table_and_indices(
    savepoint_tables: tuple[np.ndarray, np.ndarray],
    grid_savepoint,
    experiment,
) -> None:
    """Ingest the serialized table directly (frozen constructor) and reproduce the
    savepoint's interface heights and nflatlev."""
    vct_a_ref, vct_b_ref = savepoint_tables
    i4_cfg = experiment.config.vertical_grid
    grid = VerticalGrid(
        vct_a_ref,
        vct_b_ref,
        vct_a_ref.shape[0] - 1,
        flat_height=i4_cfg.flat_height,
        rayleigh_damping_height=i4_cfg.rayleigh_damping_height,
        htop_moist_proc=i4_cfg.htop_moist_proc,
    )
    assert_allclose(
        grid.interface_heights, vct_a_ref, rtol=0.0, atol=0.0, names="interface_heights"
    )
    assert grid.nflatlev == int(grid_savepoint.nflatlev())
