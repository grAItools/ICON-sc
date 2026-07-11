"""Graupel scheme constants consumed on the symcon side (S08/S10; architecture §8.6).

One scheme-constants module per scheme (single source of numerical truth for the
imperative kernel *and* the S10 functional core). The imperative kernel is
icon4py's granule, whose full constant set lives in its own
``microphysics_constants.MicrophysicsConstants``; since S10 this module carries
the **full transcription** of the graupel-relevant subset (REFERENCES.lock
``icon4py-graupel-stencils``, v0.2.0) because the JAX functional core
re-implements the scan and must draw every number from here. *Derived* constants
reproduce icon4py's derivation expressions operation-for-operation (``math.gamma``
etc., never decimal literals), so equality with the granule's values is bitwise;
the equality table against a live icon4py import is asserted in
``tests/test_scheme_constants.py``.

Only ``GRAUPEL_QMIN`` and ``CLOUD_NUM`` predate S10 (their provenance notes are
kept verbatim below); everything else cites its icon4py symbol, whose docstrings
carry the COSMO-documentation equation numbers and original ICON names.
"""

from __future__ import annotations

import math
from typing import Final

from symcon.icon._constants import ALS, CVD, RHOH2O, RV, TMELT

__all__ = [
    "AIR_KINEMATIC_VISCOSITY",
    "ASMEL",
    "CAGG_G",
    "CCDVTP",
    "CCIDEP",
    "CCSAXP",
    "CCSDEP",
    "CCSDXP",
    "CCSHI1",
    "CCSLAM",
    "CCSLXP",
    "CCSVXP",
    "CCSWXP",
    "CCSWXP_LN1O2",
    "CIAU",
    "CICRI",
    "CLOUD_NUM",
    "CNUE",
    "COEFF_RAIN_FREEZE1",
    "COEFF_RAIN_FREEZE2",
    "CPI",
    "CP_V",
    "CRCRI",
    "CRIM_G",
    "DIFFUSION_COEFF_FOR_WATER_VAPOR",
    "DIST_CLDTOP_REF",
    "GRAUPEL_QMIN",
    "GRAUPEL_RIMEXP",
    "HETEROGENEOUS_FREEZE_TEMPERATURE",
    "HOMOGENEOUS_FREEZE_TEMPERATURE",
    "HOWELL_FACTOR",
    "ICE_INITIAL_MASS",
    "ICE_MAX_MASS",
    "ICE_STICKING_EFF_FACTOR",
    "KCAC",
    "KCAU",
    "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_CLOUD",
    "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_RAIN",
    "KPHI1",
    "KPHI2",
    "KPHI3",
    "MINIMUM_GRAUPEL_FALL_SPEED",
    "MINIMUM_RAIN_FALL_SPEED",
    "MINIMUM_SNOW_FALL_SPEED",
    "MSMIN",
    "NIMAX_THOM",
    "NIMIX",
    "POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED",
    "POWER_LAW_COEFF_FOR_SNOW_MD_RELATION",
    "POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED",
    "POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED",
    "POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED",
    "POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION",
    "PVSW0",
    "QC0",
    "QI0",
    "RCVD",
    "REDUCE_DEP_REF",
    "REF_AIR_DENSITY",
    "SNOW_CLOUD_COLLECTION_EFF",
    "SNOW_DEFAULT_INTERCEPT_PARAM",
    "SNOW_INTERCEPT_PARAMETER_MMA",
    "SNOW_INTERCEPT_PARAMETER_MMB",
    "SNOW_INTERCEPT_PARAMETER_N0S1",
    "SNOW_INTERCEPT_PARAMETER_N0S2",
    "TCRIT",
    "TETENS_AI",
    "TETENS_AW",
    "TETENS_BI",
    "TETENS_BW",
    "TETENS_P0",
    "THERMAL_CONDUCTIVITY_DRY_AIR",
    "THRESHOLD_FREEZE_TEMPERATURE",
    "THRESHOLD_FREEZE_TEMPERATURE_MIXEDPHASE",
    "TMIN_ICEAUTOCONV",
    "WATER_DENSITY",
    "XSTAR",
]

#: Threshold for lowest detectable mixing ratios [kg/kg] (icon4py QMIN; ICON zqmin).
GRAUPEL_QMIN: Final[float] = 1.0e-15

#: Default cloud droplet number concentration [1/m3] (ICON gscp_data.f90 cloud_num).
CLOUD_NUM: Final[float] = 200.00e6

# --- Tetens saturation-pressure constants (icon4py TETENS_*; ICON c1es..c4ies) -------

#: p0 in the Tetens formula [Pa] — icon4py ``TETENS_P0`` (ICON ``c1es``).
TETENS_P0: Final[float] = 610.78
#: aw in the Tetens water formula — icon4py ``TETENS_AW`` (ICON ``c3les``).
TETENS_AW: Final[float] = 17.269
#: bw in the Tetens water formula [K] — icon4py ``TETENS_BW`` (ICON ``c4les``).
TETENS_BW: Final[float] = 35.86
#: ai in the Tetens ice formula — icon4py ``TETENS_AI`` (ICON ``c3ies``).
TETENS_AI: Final[float] = 21.875
#: bi in the Tetens ice formula [K] — icon4py ``TETENS_BI`` (ICON ``c4ies``).
TETENS_BI: Final[float] = 7.66

# --- thresholds and empirical temperatures ------------------------------------------

#: Threshold T for heterogeneous raindrop freezing [K] — ``THRESHOLD_FREEZE_TEMPERATURE``.
THRESHOLD_FREEZE_TEMPERATURE: Final[float] = 271.15
#: 1st immersion-freezing coefficient — ``COEFF_RAIN_FREEZE1`` (ICON ``crfrz1``).
COEFF_RAIN_FREEZE1: Final[float] = 9.95e-5
#: 2nd immersion-freezing coefficient — ``COEFF_RAIN_FREEZE2`` (ICON ``crfrz2``).
COEFF_RAIN_FREEZE2: Final[float] = 0.66
#: Homogeneous freezing temperature of cloud water [K] — (ICON ``thn``).
HOMOGENEOUS_FREEZE_TEMPERATURE: Final[float] = 236.15
#: Mixed-phase freezing threshold [K] (Forbes 2012) — (ICON ``tmix``).
THRESHOLD_FREEZE_TEMPERATURE_MIXEDPHASE: Final[float] = 250.15
#: Heterogeneous ice-nucleation temperature [K] — (ICON ``thet``).
HETEROGENEOUS_FREEZE_TEMPERATURE: Final[float] = 248.15
#: T at which cloud-ice autoconversion starts [K] — ``TMIN_ICEAUTOCONV``.
TMIN_ICEAUTOCONV: Final[float] = 188.15

# --- fall speeds, size distributions, particle masses --------------------------------

#: v-rhoqi exponent for ice fall speed — (ICON ``bvi``).
POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED: Final[float] = 0.16
#: Reference air density [kg/m3] — (ICON ``rho0``).
REF_AIR_DENSITY: Final[float] = 1.225e0
#: Minimum rain fall speed near the ground [m/s] — (ICON ``v_sedi_rain_min``).
MINIMUM_RAIN_FALL_SPEED: Final[float] = 0.7
#: Minimum snow fall speed near the ground [m/s] — (ICON ``v_sedi_snow_min``).
MINIMUM_SNOW_FALL_SPEED: Final[float] = 0.1
#: Minimum graupel fall speed near the ground [m/s] — (ICON ``v_sedi_graupel_min``).
MINIMUM_GRAUPEL_FALL_SPEED: Final[float] = 0.4
#: Maximal ice-crystal number concentration [1/m3] — ``NIMAX_THOM``.
NIMAX_THOM: Final[float] = 250.0e3
#: Formfactor of the snow m-D relation — (ICON ``ams``).
POWER_LAW_COEFF_FOR_SNOW_MD_RELATION: Final[float] = 0.069
#: Constant snow intercept parameter — (ICON ``n0s0``).
SNOW_DEFAULT_INTERCEPT_PARAM: Final[float] = 8.0e5
#: Mixing-ratio exponent in graupel riming/aggregation — (ICON ``rimexp_g``).
GRAUPEL_RIMEXP: Final[float] = 0.94878
#: v-rhoqg exponent for graupel fall speed — (ICON ``expsedg``).
POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED: Final[float] = 0.217
#: v-rhoqg coefficient for graupel fall speed — (ICON ``vz0g``).
POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED: Final[float] = 12.24
#: Initial ice-crystal mass [kg] — (ICON ``mi0``).
ICE_INITIAL_MASS: Final[float] = 1.0e-12
#: Maximum ice-crystal mass [kg] — (ICON ``mimax``).
ICE_MAX_MASS: Final[float] = 1.0e-9
#: Initial snow-crystal mass [kg] — icon4py ``MSMIN``/``SNOW_MIN_MASS`` (ICON ``msmin``).
MSMIN: Final[float] = 3.0e-9
#: Scaling factor [1/K] of the T-dependent ice sticking efficiency — (ICON ``ceff_min``).
ICE_STICKING_EFF_FACTOR: Final[float] = 3.5e-3
#: Reference cloud-top distance [m] (Forbes 2012) — ``DIST_CLDTOP_REF``.
DIST_CLDTOP_REF: Final[float] = 500.0
#: Lower bound of the deposition reduction — ``REDUCE_DEP_REF``.
REDUCE_DEP_REF: Final[float] = 0.1
#: Howell factor in depositional growth — (ICON ``hw``).
HOWELL_FACTOR: Final[float] = 2.270603
#: Snow-cloud collection efficiency — (ICON ``ecs``).
SNOW_CLOUD_COLLECTION_EFF: Final[float] = 0.9
#: v-D exponent for snow fall speed — (ICON ``v1s``).
POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED: Final[float] = 0.5
#: Kinematic viscosity of air [m2/s] — (ICON ``eta``).
AIR_KINEMATIC_VISCOSITY: Final[float] = 1.75e-5
#: Molecular diffusion coefficient of water vapor [m2/s] — (ICON ``dv``).
DIFFUSION_COEFF_FOR_WATER_VAPOR: Final[float] = 2.22e-5
#: Thermal conductivity of dry air — (ICON ``lheat``).
THERMAL_CONDUCTIVITY_DRY_AIR: Final[float] = 2.40e-2
#: Exponent of the snow m-D relation — (ICON ``bms``).
POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION: Final[float] = 2.0
#: Density of liquid water [kg/m3] — icon4py ``PhysicsConstants.water_density``.
WATER_DENSITY: Final[float] = RHOH2O
#: Specific heat of water vapor [J/K/kg] used by the microphysics latent-heat closure —
#: icon4py ``CP_V`` ("NOTE THAT THIS IS DIFFERENT FROM VALUE USED IN THE MODEL
#: CONSTANTS"; a local Landolt-Börnstein literal, distinct from ``CPV = 1869.46``).
CP_V: Final[float] = 1850.0
#: Specific heat of ice [J/K/kg] — icon4py ``PhysicsConstants.cpi`` (ICON
#: ``mo_physical_constants`` has 2106.0; the icon4py value is the verification
#: target — S06/S08 ``ci`` flag; enters only the dead non-constant-latent-heat
#: branch).
CPI: Final[float] = 2108.0
#: Reciprocal heat capacity of dry air at constant volume — icon4py ``RCVD``
#: (isochoric heating: ``l_cv`` hardcoded true, S08 provenance).
RCVD: Final[float] = 1.0 / CVD

# --- snow intercept parameterizations (Field et al. 2005) -----------------------------

#: Best-fit intercept parameter 1 — (ICON ``zn0s1``).
SNOW_INTERCEPT_PARAMETER_N0S1: Final[float] = 13.5 * 5.65e5
#: Best-fit intercept parameter 2 — (ICON ``zn0s2``).
SNOW_INTERCEPT_PARAMETER_N0S2: Final[float] = -0.107
#: General-moment coefficients (ICON ``mma``), icon4py ``SNOW_INTERCEPT_PARAMETER_MMA1..10``.
SNOW_INTERCEPT_PARAMETER_MMA: Final[tuple[float, ...]] = (
    5.065339,
    -0.062659,
    -3.032362,
    0.029469,
    -0.000285,
    0.312550,
    0.000204,
    0.003199,
    0.000000,
    -0.015952,
)
#: General-moment coefficients (ICON ``mmb``), icon4py ``SNOW_INTERCEPT_PARAMETER_MMB1..10``.
SNOW_INTERCEPT_PARAMETER_MMB: Final[tuple[float, ...]] = (
    0.476221,
    -0.015896,
    0.165977,
    0.007468,
    -0.000141,
    0.060366,
    0.000079,
    0.000594,
    0.000000,
    -0.003577,
)

# --- autoconversion / accretion ------------------------------------------------------

#: Kessler (1969) cloud→rain autoconversion coefficient — (ICON ``ccau``).
KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_CLOUD: Final[float] = 4.0e-4
#: Kessler (1969) rain-accretion coefficient — (ICON ``cac``).
KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_RAIN: Final[float] = 1.72
#: Seifert-Beheng (2001) phi-function constant — ``KPHI1``.
KPHI1: Final[float] = 6.00e02
#: Seifert-Beheng (2001) phi-function exponent — ``KPHI2``.
KPHI2: Final[float] = 0.68e00
#: Seifert-Beheng (2001) accretion phi exponent — ``KPHI3``.
KPHI3: Final[float] = 5.00e-05
#: Seifert-Beheng (2001) autoconversion kernel coefficient — ``KCAU``
#: (the tunable "autoconversion parameter" exposed in the S10 ParamTree).
KCAU: Final[float] = 9.44e09
#: Seifert-Beheng (2001) accretion kernel coefficient — ``KCAC``.
KCAC: Final[float] = 5.25e00
#: Gamma exponent of the cloud size distribution (Seifert-Beheng) — ``CNUE``.
CNUE: Final[float] = 2.00e00
#: Separating mass between cloud and rain (Seifert-Beheng) — ``XSTAR``.
XSTAR: Final[float] = 2.60e-10

# --- riming / aggregation / melting coefficients --------------------------------------

#: Graupel riming coefficient — ``CRIM_G``.
CRIM_G: Final[float] = 4.43
#: Graupel-ice aggregation coefficient — ``CAGG_G``.
CAGG_G: Final[float] = 2.46
#: Cloud-ice→snow autoconversion coefficient — ``CIAU``.
CIAU: Final[float] = 1.0e-3
#: Rain-ice accretion (ice loss) coefficient — ``CICRI``.
CICRI: Final[float] = 1.72
#: Rain-ice accretion (rain loss) coefficient — ``CRCRI``.
CRCRI: Final[float] = 1.24e-3
#: DIFF·LH_v·RHO/LHEAT in the melting critical temperature — ``ASMEL``.
ASMEL: Final[float] = 2.95e3
#: Factor in the melting critical-temperature calculation — ``TCRIT``.
TCRIT: Final[float] = 3339.5
#: Minimum specific cloud content [kg/kg] — ``QC0``.
QC0: Final[float] = 0.0
#: Minimum specific ice content [kg/kg] — ``QI0``.
QI0: Final[float] = 0.0

# --- derived constants (icon4py derivation expressions, operation-for-operation) ------

#: Ice-crystal number concentration at the mixed-phase threshold — ``NIMIX``.
NIMIX: Final[float] = 5.0 * math.exp(0.304 * (TMELT - THRESHOLD_FREEZE_TEMPERATURE_MIXEDPHASE))

#: Snow-deposition ventilation coefficient — ``CCSDEP``.
CCSDEP: Final[float] = (
    0.26
    * math.gamma((POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED + 5.0) / 2.0)
    * math.sqrt(1.0 / AIR_KINEMATIC_VISCOSITY)
)
_CCSVXP_MINUS: Final[float] = -(
    POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED / (POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION + 1.0) + 1.0
)
#: Snow-sedimentation n0s exponent — ``CCSVXP`` (= ``_ccsvxp + 1``).
CCSVXP: Final[float] = _CCSVXP_MINUS + 1.0
#: Snow-lambda coefficient — ``CCSLAM``.
CCSLAM: Final[float] = POWER_LAW_COEFF_FOR_SNOW_MD_RELATION * math.gamma(
    POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION + 1.0
)
#: Snow-lambda exponent — ``CCSLXP``.
CCSLXP: Final[float] = 1.0 / (POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION + 1.0)
#: Snow terminal-velocity exponent (in rhoqs) — ``CCSWXP``.
CCSWXP: Final[float] = POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED * CCSLXP
#: Snow riming/aggregation lambda exponent — ``CCSAXP``.
CCSAXP: Final[float] = -(POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED + 3.0)
#: Snow deposition lambda exponent — ``CCSDXP``.
CCSDXP: Final[float] = -(POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED + 1.0) / 2.0
#: L_s^2 / (K_T R_v) in the deposition denominator — ``CCSHI1``.
CCSHI1: Final[float] = ALS * ALS / (THERMAL_CONDUCTIVITY_DRY_AIR * RV)
#: Vapor-diffusivity prefactor — ``CCDVTP``.
CCDVTP: Final[float] = 2.22e-5 * TMELT ** (-1.94) * 101325.0
#: Ice deposition coefficient — ``CCIDEP`` (ICON ``ami`` = 130 is the ice m-D formfactor).
CCIDEP: Final[float] = 4.0 * 130.0 ** (-1.0 / 3.0)
#: (0.5)^CCSWXP model-top factor — ``CCSWXP_LN1O2``.
CCSWXP_LN1O2: Final[float] = math.exp(CCSWXP * math.log(0.5))
#: Saturation water pressure at T = tmelt [Pa] — ``PVSW0``.
PVSW0: Final[float] = TETENS_P0 * math.exp(TETENS_AW * (TMELT - TMELT) / (TMELT - TETENS_BW))
