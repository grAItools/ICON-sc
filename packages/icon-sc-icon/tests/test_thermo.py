"""S06 acceptance 1: thermo round-trips to 1e-12 fp64 on a realistic (p, T, qv) grid."""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.testing import assert_allclose
from icon_sc.icon import thermo
from icon_sc.icon._constants import P0REF, RD, RD_O_CVD, RD_O_P0REF, VTMPC1

#: SPEC S06 tolerance contract: identity to 1e-12 (fp64).
RTOL = 1e-12


def _realistic_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """A dense (p, T, qv, qc) grid spanning the whole NWP envelope.

    p: 10 hPa stratosphere → 1080 hPa deep low surface; T: 180 K polar stratopause →
    330 K desert boundary layer; qv: 0 → 0.035 (saturated tropics); condensate 0 →
    0.02. All fp64, all combinations.
    """
    p = np.geomspace(1.0e3, 1.08e5, 25)
    t = np.linspace(180.0, 330.0, 21)
    qv = np.linspace(0.0, 0.035, 8)
    qc = np.linspace(0.0, 0.02, 5)
    pp, tt, qq, cc = np.meshgrid(p, t, qv, qc, indexing="ij")
    return pp, tt, qq, cc


def test_pressure_exner_roundtrip() -> None:
    p, _, _, _ = _realistic_grid()
    exner = thermo.exner_from_pressure(p)
    assert_allclose(thermo.pressure_from_exner(exner), p, rtol=RTOL, atol=0.0, names="air_pressure")
    # and the reverse orientation
    assert_allclose(
        thermo.exner_from_pressure(thermo.pressure_from_exner(exner)),
        exner,
        rtol=RTOL,
        atol=0.0,
        names="icon:exner_function",
    )


def test_temperature_thetav_roundtrip_with_moisture() -> None:
    p, t, qv, qc = _realistic_grid()
    exner = thermo.exner_from_pressure(p)
    theta_v = thermo.virtual_potential_temperature(t, exner, qv, qc)
    t_back = thermo.temperature_from_thetav_exner(theta_v, exner, qv, qc)
    assert_allclose(t_back, t, rtol=RTOL, atol=0.0, names="air_temperature")


def test_virtual_temperature_moisture_term() -> None:
    """tempv = temp·(1 + vtmpc1·qv - qsum) — ICON diag_temp, spot-checked."""
    t = np.array([250.0, 288.15, 300.0])
    qv = np.array([0.0, 0.01, 0.02])
    qc = np.array([0.0, 0.001, 0.005])
    expected = t * (1.0 + VTMPC1 * qv - qc)
    assert_allclose(
        thermo.virtual_temperature(t, qv, qc), expected, rtol=0.0, atol=0.0, names="tempv"
    )
    # dry limit: tempv == temp exactly
    assert np.all(thermo.virtual_temperature(t, np.zeros_like(t)) == t)


def test_exner_paths_agree_on_consistent_state() -> None:
    """cpd path (from p) and cvd path (from rho, θv) meet on an ideal-gas state.

    With rho = p/(rd·tempv) and θv = tempv/exner, rd·rho·θv/p0ref = (p/p0ref)/exner =
    exner**(cpd/rd)/exner = exner**(cvd/rd), so exner_from_rho_thetav recovers exner.
    """
    p, t, qv, qc = _realistic_grid()
    exner = thermo.exner_from_pressure(p)
    tempv = thermo.virtual_temperature(t, qv, qc)
    theta_v = tempv / exner
    rho = p / (RD * tempv)
    assert_allclose(
        thermo.exner_from_rho_thetav(rho, theta_v),
        exner,
        rtol=1e-12,
        atol=0.0,
        names=("exner (cvd path)", "exner (cpd path)"),
    )


def test_exner_from_rho_thetav_matches_fortran_form() -> None:
    """The cvd path is EXP(rd_o_cvd·LOG(rd_o_p0ref·rho·θv)) operation-for-operation."""
    rho = np.array([0.02, 0.5, 1.2, 1.4])
    theta_v = np.array([900.0, 400.0, 300.0, 285.0])
    expected = np.exp(RD_O_CVD * np.log(RD_O_P0REF * rho * theta_v))
    assert np.array_equal(thermo.exner_from_rho_thetav(rho, theta_v), expected)


def test_scalars_and_python_floats_pass_through() -> None:
    exner = thermo.exner_from_pressure(np.float64(P0REF))
    assert exner == pytest.approx(1.0, abs=0.0)
    assert thermo.pressure_from_exner(np.float64(1.0)) == P0REF


def test_array_namespace_genericity_numpy() -> None:
    """numpy in → numpy out; dtype preserved (fp64 stays fp64, no upcasts)."""
    p = np.linspace(5e4, 1e5, 7)
    out = thermo.exner_from_pressure(p)
    assert isinstance(out, np.ndarray) and out.dtype == np.float64
    rho = np.full(7, 1.0)
    theta = np.full(7, 300.0)
    out2 = thermo.exner_from_rho_thetav(rho, theta)
    assert isinstance(out2, np.ndarray) and out2.dtype == np.float64
