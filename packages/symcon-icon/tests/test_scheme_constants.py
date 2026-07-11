"""S10: scheme-constants modules vs a live icon4py import — bitwise (§11.8).

The functional cores and the gt4py granules must draw on one source of
numerical truth; these tables pin the symcon transcriptions to icon4py v0.2.0's
``MicrophysicsConstants``/``PhysicsConstants`` so the pair cannot drift.
"""

from __future__ import annotations

import pytest

from symcon.icon._constants import ALV, CLW, CVD, RHOH2O, RV, TMELT
from symcon.icon.components.fast import graupel_constants as g
from symcon.icon.components.fast import satad_constants as s

icon4py_mp = pytest.importorskip(
    "icon4py.model.atmosphere.subgrid_scale_physics.microphysics.microphysics_constants"
)
icon4py_common = pytest.importorskip("icon4py.model.common.constants")

M = icon4py_mp.MicrophysicsConstants
P = icon4py_common.PhysicsConstants

#: symcon graupel_constants name -> icon4py MicrophysicsConstants member.
GRAUPEL_TABLE = {
    "GRAUPEL_QMIN": "QMIN",
    "TETENS_P0": "TETENS_P0",
    "TETENS_AW": "TETENS_AW",
    "TETENS_BW": "TETENS_BW",
    "TETENS_AI": "TETENS_AI",
    "TETENS_BI": "TETENS_BI",
    "THRESHOLD_FREEZE_TEMPERATURE": "THRESHOLD_FREEZE_TEMPERATURE",
    "COEFF_RAIN_FREEZE1": "COEFF_RAIN_FREEZE1",
    "COEFF_RAIN_FREEZE2": "COEFF_RAIN_FREEZE2",
    "HOMOGENEOUS_FREEZE_TEMPERATURE": "HOMOGENEOUS_FREEZE_TEMPERATURE",
    "THRESHOLD_FREEZE_TEMPERATURE_MIXEDPHASE": "THRESHOLD_FREEZE_TEMPERATURE_MIXEDPHASE",
    "HETEROGENEOUS_FREEZE_TEMPERATURE": "HETEROGENEOUS_FREEZE_TEMPERATURE",
    "TMIN_ICEAUTOCONV": "TMIN_ICEAUTOCONV",
    "POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED": "POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED",
    "REF_AIR_DENSITY": "REF_AIR_DENSITY",
    "MINIMUM_RAIN_FALL_SPEED": "MINIMUM_RAIN_FALL_SPEED",
    "MINIMUM_SNOW_FALL_SPEED": "MINIMUM_SNOW_FALL_SPEED",
    "MINIMUM_GRAUPEL_FALL_SPEED": "MINIMUM_GRAUPEL_FALL_SPEED",
    "NIMAX_THOM": "NIMAX_THOM",
    "POWER_LAW_COEFF_FOR_SNOW_MD_RELATION": "POWER_LAW_COEFF_FOR_SNOW_MD_RELATION",
    "SNOW_DEFAULT_INTERCEPT_PARAM": "SNOW_DEFAULT_INTERCEPT_PARAM",
    "GRAUPEL_RIMEXP": "GRAUPEL_RIMEXP",
    "POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED": (
        "POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED"
    ),
    "POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED": "POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED",
    "ICE_INITIAL_MASS": "ICE_INITIAL_MASS",
    "ICE_MAX_MASS": "ICE_MAX_MASS",
    "MSMIN": "MSMIN",
    "ICE_STICKING_EFF_FACTOR": "ICE_STICKING_EFF_FACTOR",
    "DIST_CLDTOP_REF": "DIST_CLDTOP_REF",
    "REDUCE_DEP_REF": "REDUCE_DEP_REF",
    "HOWELL_FACTOR": "HOWELL_FACTOR",
    "SNOW_CLOUD_COLLECTION_EFF": "SNOW_CLOUD_COLLECTION_EFF",
    "POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED": "POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED",
    "AIR_KINEMATIC_VISCOSITY": "AIR_KINEMATIC_VISCOSITY",
    "DIFFUSION_COEFF_FOR_WATER_VAPOR": "DIFFUSION_COEFF_FOR_WATER_VAPOR",
    "THERMAL_CONDUCTIVITY_DRY_AIR": "THERMAL_CONDUCTIVITY_DRY_AIR",
    "POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION": "POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION",
    "CP_V": "CP_V",
    "RCVD": "RCVD",
    "SNOW_INTERCEPT_PARAMETER_N0S1": "SNOW_INTERCEPT_PARAMETER_N0S1",
    "SNOW_INTERCEPT_PARAMETER_N0S2": "SNOW_INTERCEPT_PARAMETER_N0S2",
    "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_CLOUD": (
        "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_CLOUD"
    ),
    "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_RAIN": (
        "KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_RAIN"
    ),
    "KPHI1": "KPHI1",
    "KPHI2": "KPHI2",
    "KPHI3": "KPHI3",
    "KCAU": "KCAU",
    "KCAC": "KCAC",
    "CNUE": "CNUE",
    "XSTAR": "XSTAR",
    "CRIM_G": "CRIM_G",
    "CAGG_G": "CAGG_G",
    "CIAU": "CIAU",
    "CICRI": "CICRI",
    "CRCRI": "CRCRI",
    "ASMEL": "ASMEL",
    "TCRIT": "TCRIT",
    "QC0": "QC0",
    "QI0": "QI0",
    "NIMIX": "NIMIX",
    "CCSDEP": "CCSDEP",
    "CCSVXP": "CCSVXP",
    "CCSLAM": "CCSLAM",
    "CCSLXP": "CCSLXP",
    "CCSWXP": "CCSWXP",
    "CCSAXP": "CCSAXP",
    "CCSDXP": "CCSDXP",
    "CCSHI1": "CCSHI1",
    "CCDVTP": "CCDVTP",
    "CCIDEP": "CCIDEP",
    "CCSWXP_LN1O2": "CCSWXP_LN1O2",
    "PVSW0": "PVSW0",
}


@pytest.mark.parametrize("symcon_name", sorted(GRAUPEL_TABLE))
def test_graupel_constant_bitwise(symcon_name: str) -> None:
    icon4py_value = float(getattr(M, GRAUPEL_TABLE[symcon_name]).value)
    assert getattr(g, symcon_name) == icon4py_value, symcon_name


@pytest.mark.parametrize("index", range(10))
def test_snow_intercept_moment_tables_bitwise(index: int) -> None:
    assert g.SNOW_INTERCEPT_PARAMETER_MMA[index] == float(
        getattr(M, f"SNOW_INTERCEPT_PARAMETER_MMA{index + 1}").value
    )
    assert g.SNOW_INTERCEPT_PARAMETER_MMB[index] == float(
        getattr(M, f"SNOW_INTERCEPT_PARAMETER_MMB{index + 1}").value
    )


def test_graupel_physics_constants_bitwise() -> None:
    assert g.WATER_DENSITY == float(P.water_density.value)
    assert g.CPI == float(P.cpi.value)


@pytest.mark.parametrize(
    ("symcon_value", "icon4py_member"),
    [
        (s.TETENS_P0, "TETENS_P0"),
        (s.TETENS_AW, "TETENS_AW"),
        (s.TETENS_BW, "TETENS_BW"),
        (s.TETENS_DER, "TETENS_DER"),
        (s.CP_V, "CP_V"),
    ],
)
def test_satad_constants_bitwise(symcon_value: float, icon4py_member: str) -> None:
    assert symcon_value == float(getattr(M, icon4py_member).value)


def test_satad_closure_constants_match_physics_constants() -> None:
    # The Kirchhoff/qsat closures draw ALV/CLW/CVD/RV/TMELT from _constants;
    # those must equal the granule's PhysicsConstants members bitwise.
    assert ALV == float(P.lh_vaporise.value)
    assert CLW == float(P.cpl.value)
    assert CVD == float(P.cvd.value)
    assert RV == float(P.rv.value)
    assert TMELT == float(P.tmelt.value)
    assert RHOH2O == float(P.water_density.value)
