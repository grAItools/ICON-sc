"""S06 acceptance 2: byte-compare symcon.icon._constants against pinned ICON Fortran.

The comparison table below is *extracted from* the pinned ICON sources (REFERENCES.lock
id ``icon-fortran``, https://gitlab.dkrz.de/icon/icon-model, commit
8597da45ef4b86323f3fb844caedc4ae5e1ffc01, tag icon-2026.04-public) and committed here:
each row cites the Fortran file:line and repeats the Fortran literal (or derivation
expression, evaluated with the same operations — fp64 Python arithmetic is IEEE 754
like ``REAL(wp)``, so the comparison is bitwise). Values must never be edited here
without re-mining the reference.
"""

from __future__ import annotations

import pytest

from symcon.icon import _constants as c

# (symcon constant, expected value, provenance) — mo_physical_constants.f90 unless
# noted. Expected values are the Fortran literals / derivation expressions verbatim.
_MO_PHYSICAL_CONSTANTS_TABLE = [
    (c.RD, 287.04, "rd = 287.04_wp (L109)"),
    (c.CPD, 1004.64, "cpd = 1004.64_wp (L111)"),
    (c.CVD, 1004.64 - 287.04, "cvd = cpd-rd (L113)"),
    (c.RV, 461.51, "rv = 461.51_wp (L123)"),
    (c.CPV, 1869.46, "cpv = 1869.46_wp (L125)"),
    (c.CVV, 1869.46 - 461.51, "cvv = cpv-rv (L126)"),
    (c.RHOH2O, 1000.0, "rhoh2o = 1000._wp (L130)"),
    (c.ALV, 2.5008e6, "alv = 2.5008e6_wp (L138)"),
    (c.ALS, 2.8345e6, "als = 2.8345e6_wp (L140)"),
    (c.ALF, 2.8345e6 - 2.5008e6, "alf = als-alv (L142)"),
    (c.TMELT, 273.15, "tmelt = 273.15_wp (L144)"),
    (c.T3, 273.16, "t3 = 273.16_wp (L145)"),
    (c.RDV, 287.04 / 461.51, "rdv = rd/rv (L148)"),
    (c.VTMPC1, 461.51 / 287.04 - 1.0, "vtmpc1 = rv/rd-1._wp (L150)"),
    (c.VTMPC2, 1869.46 / 1004.64 - 1.0, "vtmpc2 = cpv/cpd-1._wp (L152)"),
    (c.RCPD, 1.0 / 1004.64, "rcpd = 1._wp/cpd (L156)"),
    (c.RCVD, 1.0 / (1004.64 - 287.04), "rcvd = 1._wp/cvd (L157)"),
    (c.RCPL, 3.1733, "rcpl = 3.1733_wp (L158)"),
    (c.CLW, (3.1733 + 1.0) * 1004.64, "clw = (rcpl + 1.0_wp) * cpd (L160)"),
    (c.O_M_RDV, 1.0 - 287.04 / 461.51, "o_m_rdv = 1._wp-rd/rv (L164)"),
    (c.RD_O_CPD, 287.04 / 1004.64, "rd_o_cpd = rd/cpd (L166)"),
    (c.CVD_O_RD, (1004.64 - 287.04) / 287.04, "cvd_o_rd = cvd/rd (L168)"),
    (c.GRAV, 9.80665, "grav = 9.80665_wp (L97)"),
    (c.P0REF, 100000.0, "p0ref = 100000.0_wp (L171)"),
    (c.P0SL_BG, 101325.0, "p0sl_bg = 101325._wp (L205)"),
    (c.DTDZ_STANDARDATM, -6.5e-3, "dtdz_standardatm = -6.5e-3_wp (L178)"),
    (c.EARTH_RADIUS, 6.371229e6, "earth_radius = 6.371229e6_wp (L90)"),
    (c.EARTH_ANGULAR_VELOCITY, 7.29212e-5, "earth_angular_velocity = 7.29212e-5_wp (L92)"),
]

# src/atm_dyn_iconam/mo_vertical_grid.f90 module-level PARAMETERs (L80-L82).
_MO_VERTICAL_GRID_TABLE = [
    (c.H_SCAL_BG, 10000.0, "h_scal_bg = 10000._wp (mo_vertical_grid.f90 L80)"),
    (c.T0SL_BG, 288.15, "t0sl_bg = 288.15_wp (mo_vertical_grid.f90 L81)"),
    (c.DEL_T_BG, 75.0, "del_t_bg = 75._wp (mo_vertical_grid.f90 L82)"),
]


@pytest.mark.parametrize(
    ("actual", "expected", "provenance"),
    _MO_PHYSICAL_CONSTANTS_TABLE + _MO_VERTICAL_GRID_TABLE,
    ids=lambda arg: arg if isinstance(arg, str) else None,
)
def test_constant_matches_fortran(actual: float, expected: float, provenance: str) -> None:
    # Byte compare (== on fp64), not approx: constants are transcriptions, not results.
    assert actual == expected, f"mismatch vs pinned ICON Fortran: {provenance}"


def test_derived_ratios_are_derived_not_literals() -> None:
    """Composed constants must reproduce the Fortran derivation exactly (bitwise)."""
    assert c.CPD_O_RD == c.CPD / c.RD
    assert c.RD_O_CVD == c.RD / c.CVD
    assert c.RD_O_P0REF == c.RD / c.P0REF
    assert c.GRAV_O_RD == c.GRAV / c.RD
    assert c.GRAV_O_CPD == c.GRAV / c.CPD
