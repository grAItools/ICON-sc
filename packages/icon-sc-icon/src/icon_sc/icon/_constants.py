"""ICON physical constants — one flat module (the shared-constants pattern, layout §5).

Every value is transcribed from the pinned ICON Fortran sources (REFERENCES.lock, id
``icon-fortran``, commit 8597da45, tag icon-2026.04-public), never from memory:

- ``src/shared/mo_physical_constants.f90`` for the thermodynamic constants;
- ``src/atm_dyn_iconam/mo_vertical_grid.f90`` for the reference-atmosphere parameters
  (``h_scal_bg``/``t0sl_bg``/``del_t_bg`` are module-level PARAMETERs there, not in
  ``mo_physical_constants``).

Each constant cites its Fortran symbol; *derived* constants reproduce the Fortran
derivation expression operation-for-operation (e.g. ``CVD = CPD - RD``, not a decimal
literal) so equality with the reference is bitwise. The byte-compare table against the
Fortran literals is committed in ``tests/test_constants_fortran.py`` (acceptance 2);
equality with icon4py v0.2.0 ``model/common/constants.py`` is asserted in
``tests/test_icon4py_crosscheck.py``.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ALF",
    "ALS",
    "ALV",
    "CLW",
    "CPD",
    "CPD_O_RD",
    "CPV",
    "CVD",
    "CVD_O_RD",
    "CVV",
    "DEL_T_BG",
    "DTDZ_STANDARDATM",
    "EARTH_ANGULAR_VELOCITY",
    "EARTH_RADIUS",
    "GRAV",
    "GRAV_O_CPD",
    "GRAV_O_RD",
    "H_SCAL_BG",
    "O_M_RDV",
    "P0REF",
    "P0SL_BG",
    "RCPD",
    "RCPL",
    "RCVD",
    "RD",
    "RDV",
    "RD_O_CPD",
    "RD_O_CVD",
    "RD_O_P0REF",
    "RHOH2O",
    "RV",
    "T0SL_BG",
    "T3",
    "TMELT",
    "VTMPC1",
    "VTMPC2",
]

# --- dry air (mo_physical_constants.f90) -------------------------------------------

#: Gas constant of dry air [J K-1 kg-1] — Fortran ``rd = 287.04_wp``.
RD: Final[float] = 287.04
#: Specific heat of dry air at constant pressure [J K-1 kg-1] — ``cpd = 1004.64_wp``.
CPD: Final[float] = 1004.64
#: Specific heat of dry air at constant volume [J K-1 kg-1] — ``cvd = cpd-rd``.
CVD: Final[float] = CPD - RD

# --- water vapor / hydrometeors (mo_physical_constants.f90) ------------------------

#: Gas constant of water vapor [J K-1 kg-1] — ``rv = 461.51_wp``.
RV: Final[float] = 461.51
#: Specific heat of water vapor at constant pressure [J K-1 kg-1] — ``cpv = 1869.46_wp``.
CPV: Final[float] = 1869.46
#: Specific heat of water vapor at constant volume [J K-1 kg-1] — ``cvv = cpv-rv``.
CVV: Final[float] = CPV - RV
#: Density of liquid water [kg m-3] — ``rhoh2o = 1000._wp``.
RHOH2O: Final[float] = 1000.0
#: ``cp_d / cp_l - 1`` [1] — ``rcpl = 3.1733_wp``.
RCPL: Final[float] = 3.1733
#: Specific heat of liquid water [J K-1 kg-1] — ``clw = (rcpl + 1.0_wp) * cpd``.
CLW: Final[float] = (RCPL + 1.0) * CPD
#: Latent heat of vaporisation [J kg-1] — ``alv = 2.5008e6_wp``.
ALV: Final[float] = 2.5008e6
#: Latent heat of sublimation [J kg-1] — ``als = 2.8345e6_wp``.
ALS: Final[float] = 2.8345e6
#: Latent heat of fusion [J kg-1] — ``alf = als-alv``.
ALF: Final[float] = ALS - ALV
#: Melting temperature of ice/snow [K] — ``tmelt = 273.15_wp``.
TMELT: Final[float] = 273.15
#: Triple point of water at 611 hPa [K] — ``t3 = 273.16_wp``.
T3: Final[float] = 273.16

# --- auxiliary ratios (mo_physical_constants.f90) -----------------------------------

#: ``rdv = rd/rv`` [1].
RDV: Final[float] = RD / RV
#: ``o_m_rdv = 1._wp-rd/rv`` [1].
O_M_RDV: Final[float] = 1.0 - RD / RV
#: Virtual-temperature moisture coefficient [1] — ``vtmpc1 = rv/rd-1._wp``.
VTMPC1: Final[float] = RV / RD - 1.0
#: ``vtmpc2 = cpv/cpd-1._wp`` [1].
VTMPC2: Final[float] = CPV / CPD - 1.0
#: ``rcpd = 1._wp/cpd`` [K kg J-1].
RCPD: Final[float] = 1.0 / CPD
#: ``rcvd = 1._wp/cvd`` [K kg J-1].
RCVD: Final[float] = 1.0 / CVD
#: Exner exponent of the *pressure* (cpd) path [1] — ``rd_o_cpd = rd/cpd``.
RD_O_CPD: Final[float] = RD / CPD
#: ``cvd_o_rd = cvd/rd`` [1].
CVD_O_RD: Final[float] = CVD / RD
#: Inverse Exner exponent, pressure (cpd) path [1] — ``cpd_o_rd`` (icon4py ``CPD_O_RD``;
#: used e.g. in ``mo_nh_diagnose_pres_temp.f90`` surface-pressure diagnosis).
CPD_O_RD: Final[float] = CPD / RD
#: Exner exponent of the *density* (cvd) path [1] — ``rd_o_cvd`` (icon4py ``RD_O_CVD``;
#: used e.g. in ``mo_nh_nest_utilities.f90`` exner-from-(rho, theta_v)).
RD_O_CVD: Final[float] = RD / CVD

# --- gravity, reference pressures (mo_physical_constants.f90) -----------------------

#: Average gravitational acceleration [m s-2] — ``grav = 9.80665_wp``.
GRAV: Final[float] = 9.80665
#: ``grav/rd`` [K m-1] (icon4py ``GRAV_O_RD``; ``grav_o_rd`` in diagnose_pres_temp).
GRAV_O_RD: Final[float] = GRAV / RD
#: ``grav/cpd`` [K m-1] (icon4py ``GRAV_O_CPD``; dry-adiabatic lapse rate).
GRAV_O_CPD: Final[float] = GRAV / CPD
#: Reference pressure of the Exner function [Pa] — ``p0ref = 100000.0_wp``.
P0REF: Final[float] = 100000.0
#: ``rd/p0ref`` [J K-1 kg-1 Pa-1] (icon4py ``RD_O_P0REF``; ``rd_o_p0ref`` in feedback).
RD_O_P0REF: Final[float] = RD / P0REF
#: Sea-level pressure of the reference atmosphere [Pa] — ``p0sl_bg = 101325._wp``.
P0SL_BG: Final[float] = 101325.0

# --- reference atmosphere (mo_vertical_grid.f90 module PARAMETERs) ------------------

#: Scale height of the reference atmosphere [m] — ``h_scal_bg = 10000._wp``.
H_SCAL_BG: Final[float] = 10000.0
#: Sea-level temperature of the reference atmosphere [K] — ``t0sl_bg = 288.15_wp``.
T0SL_BG: Final[float] = 288.15
#: Sea-level minus asymptotic stratospheric temperature [K] — ``del_t_bg = 75._wp``.
DEL_T_BG: Final[float] = 75.0

# --- miscellaneous (mo_physical_constants.f90) ---------------------------------------

#: U.S. standard atmosphere tropospheric lapse rate [K m-1] —
#: ``dtdz_standardatm = -6.5e-3_wp``.
DTDZ_STANDARDATM: Final[float] = -6.5e-3
#: Average Earth radius [m] — ``earth_radius = 6.371229e6_wp``.
EARTH_RADIUS: Final[float] = 6.371229e6
#: Earth angular velocity [rad s-1] — ``earth_angular_velocity = 7.29212e-5_wp``.
EARTH_ANGULAR_VELOCITY: Final[float] = 7.29212e-5
