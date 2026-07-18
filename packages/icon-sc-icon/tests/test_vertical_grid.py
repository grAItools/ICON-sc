"""S06 vertical grid: frozen interface, level tables, index semantics, SLEVE table.

Network-free tests; the grid-savepoint reproduction (acceptance 4, marker ``data``)
lives in ``test_vertical_grid_datatest.py``. The index semantics are cross-checked
against the pinned icon4py ``VerticalGrid`` on identical inputs — the adapter must
never drift from its donor.
"""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.testing import assert_allclose
from icon_sc.icon._constants import GRAV
from icon_sc.icon.grid.vertical import (
    SleveConfig,
    VerticalGrid,
    compute_vct_a_and_vct_b,
    reference_exner,
    reference_potential_temperature,
    reference_pressure,
    reference_rho,
    reference_temperature,
)


def _uniform_table(nlev: int, top: float) -> np.ndarray:
    return np.linspace(top, 0.0, nlev + 1)


class TestFrozenInterface:
    def test_positional_signature(self) -> None:
        vct_a = _uniform_table(10, 20_000.0)
        grid = VerticalGrid(vct_a, None, 10)
        assert grid.nlev == 10
        assert grid.num_interface_levels == 11

    def test_vct_b_optional_and_shape_checked(self) -> None:
        vct_a = _uniform_table(5, 10_000.0)
        grid = VerticalGrid(vct_a, np.exp(-vct_a / 5000.0), 5)
        assert grid.vct_b is not None
        with pytest.raises(ValueError, match="vct_b shape"):
            VerticalGrid(vct_a, np.zeros(3), 5)

    def test_nlev_mismatch_rejected(self) -> None:
        with pytest.raises(ValueError, match="nlev\\+1"):
            VerticalGrid(_uniform_table(10, 20_000.0), None, 9)

    def test_increasing_table_rejected(self) -> None:
        with pytest.raises(ValueError, match="decrease"):
            VerticalGrid(np.linspace(0.0, 20_000.0, 11), None, 10)

    def test_tables_are_read_only(self) -> None:
        grid = VerticalGrid(_uniform_table(4, 8000.0), None, 4)
        with pytest.raises(ValueError):
            grid.vct_a[0] = 0.0


class TestLevelTables:
    def test_full_levels_are_interface_midpoints(self) -> None:
        vct_a = _uniform_table(20, 20_000.0)
        grid = VerticalGrid(vct_a, None, 20)
        assert_allclose(
            grid.full_level_heights,
            0.5 * (vct_a[:-1] + vct_a[1:]),
            rtol=0.0,
            atol=0.0,
            names="full_level_heights",
        )
        assert grid.full_level_heights.shape == (20,)
        assert grid.interface_heights.shape == (21,)
        assert np.all(grid.layer_thickness > 0.0)
        assert grid.layer_thickness == pytest.approx(1000.0)

    def test_top_first_ordering(self) -> None:
        grid = VerticalGrid(_uniform_table(8, 16_000.0), None, 8)
        assert grid.interface_heights[0] == 16_000.0  # index 0 = model top (ICON)
        assert grid.interface_heights[-1] == 0.0


class TestIndicesMatchIcon4py:
    """The special indices must equal the donor's on identical inputs."""

    @pytest.mark.parametrize(
        ("nlev", "top", "damping", "flat", "moist"),
        [
            (60, 60_000.0, 34_000.0, 50_000.0, 22_500.0),
            (40, 12_000.0, 10_000.0, 11_000.0, 9_000.0),
            (65, 23_500.0, 12_500.0, 16_000.0, 22_500.0),
        ],
    )
    def test_special_indices(
        self, nlev: int, top: float, damping: float, flat: float, moist: float
    ) -> None:
        import gt4py.next as gtx
        from icon4py.model.common import dimension as dims
        from icon4py.model.common.grid import vertical as i4_vertical

        vct_a = _uniform_table(nlev, top)
        ours = VerticalGrid(
            vct_a,
            None,
            nlev,
            flat_height=flat,
            rayleigh_damping_height=damping,
            htop_moist_proc=moist,
        )
        theirs = i4_vertical.VerticalGrid(
            config=i4_vertical.VerticalGridConfig(
                num_levels=nlev,
                flat_height=flat,
                rayleigh_damping_height=damping,
                htop_moist_proc=moist,
            ),
            vct_a=gtx.as_field((dims.KDim,), vct_a),
            vct_b=None,
        )
        assert ours.nflatlev == int(theirs.nflatlev)
        assert ours.nrdmax == int(theirs.end_index_of_damping_layer)
        assert ours.kstart_moist == int(theirs.kstart_moist)


class TestSleveComputation:
    def test_uniform_branch(self) -> None:
        """lowest_layer_thickness <= 0.01 → uniform table H·(N-k)/N (icon4py/ICON)."""
        cfg = SleveConfig(num_levels=10, lowest_layer_thickness=0.0, model_top_height=10_000.0)
        vct_a, vct_b = compute_vct_a_and_vct_b(cfg)
        assert_allclose(vct_a, np.linspace(10_000.0, 0.0, 11), rtol=0.0, atol=0.0, names="vct_a")
        assert np.array_equal(vct_b, np.exp(-vct_a / 5000.0))

    def test_stretched_branch_endpoints_and_lowest_thickness(self) -> None:
        cfg = SleveConfig(num_levels=65)  # ICON namelist defaults
        vct_a, _ = compute_vct_a_and_vct_b(cfg)
        assert vct_a.shape == (66,)
        assert vct_a[0] == pytest.approx(cfg.model_top_height)
        assert vct_a[-1] == 0.0
        # d is chosen so the lowest layer has exactly the namelist thickness
        assert (vct_a[-2] - vct_a[-1]) == pytest.approx(cfg.lowest_layer_thickness)

    def test_from_config_roundtrip(self) -> None:
        cfg = SleveConfig(num_levels=30)
        grid = VerticalGrid.from_config(cfg)
        vct_a, vct_b = compute_vct_a_and_vct_b(cfg)
        assert np.array_equal(grid.vct_a, vct_a)
        assert grid.vct_b is not None and np.array_equal(grid.vct_b, vct_b)
        assert grid.nlev == 30


class TestReferenceAtmosphere:
    def test_sea_level_values(self) -> None:
        z0 = np.array([0.0])
        assert reference_temperature(z0)[0] == pytest.approx(288.15, abs=0.0)
        assert reference_pressure(z0)[0] == pytest.approx(101_325.0, rel=1e-15)
        assert reference_exner(z0)[0] == pytest.approx((101_325.0 / 1e5) ** (287.04 / 1004.64))

    def test_asymptotic_stratospheric_temperature(self) -> None:
        z = np.array([200_000.0])
        # T(z→∞) = t0sl_bg - del_t_bg = 213.15 K
        assert reference_temperature(z)[0] == pytest.approx(213.15, abs=1e-6)

    def test_profiles_dict_on_full_levels(self) -> None:
        grid = VerticalGrid.from_config(SleveConfig(num_levels=25))
        profiles = grid.reference_profiles()
        z_mc = grid.full_level_heights
        assert set(profiles) == {"icon:exner_ref_mc", "icon:theta_ref_mc", "icon:rho_ref_mc"}
        assert np.array_equal(profiles["icon:exner_ref_mc"], reference_exner(z_mc))
        assert np.array_equal(profiles["icon:theta_ref_mc"], reference_potential_temperature(z_mc))
        assert np.array_equal(profiles["icon:rho_ref_mc"], reference_rho(z_mc))

    def test_hydrostatic_consistency(self) -> None:
        """dp/dz ≈ -g·rho for the closed-form profile (midpoint finite difference)."""
        z = np.linspace(0.0, 30_000.0, 3001)
        p = reference_pressure(z)
        rho_mid = reference_rho(0.5 * (z[:-1] + z[1:]))
        dpdz = np.diff(p) / np.diff(z)
        assert_allclose(dpdz, -GRAV * rho_mid, rtol=1e-5, atol=0.0, names="dp/dz")
