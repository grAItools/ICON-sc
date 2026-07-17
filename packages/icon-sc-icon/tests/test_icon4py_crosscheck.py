"""S06 acceptance 3: cross-check ICON-sc thermo/constants against pinned icon4py.

icon4py v0.2.0 exposes the same constants (``model/common/constants.py``) and, as
embedded-executable gt4py field operators, the θv/T diagnosis
(``diagnose_temperature.py``) and the reference atmosphere
(``metrics/reference_atmosphere.py``). Where exposed, ICON-sc must agree to 1e-12
(constants: byte compare). The pressure↔Exner pair has no standalone icon4py helper —
it appears only fused inside larger stencils (e.g. ``diagnose_surface_pressure``,
``mo_nh_vert_extrap_utils``) — so it is covered by the Fortran-formula tests in
``test_thermo.py`` instead (recorded justification, SPEC S06 acceptance 3).
"""

from __future__ import annotations

import numpy as np
from icon4py.model.common import constants as i4_constants

from icon_sc.core.testing import assert_allclose
from icon_sc.icon import _constants as c
from icon_sc.icon import thermo
from icon_sc.icon.grid import vertical as vgrid

RTOL = 1e-12


def test_constants_match_icon4py() -> None:
    """Byte compare against icon4py v0.2.0 constants (both transcribe the Fortran)."""
    pairs = [
        (c.RD, i4_constants.GAS_CONSTANT_DRY_AIR),
        (c.CPD, i4_constants.SPECIFIC_HEAT_CAPACITY_PRESSURE_DRY_AIR),
        (c.CVD, i4_constants.SPECIFIC_HEAT_CAPACITY_VOLUME_DRY_AIR),
        (c.RV, i4_constants.GAS_CONSTANT_WATER_VAPOR),
        (c.CPV, i4_constants.SPECIFIC_HEAT_CAPACITY_PRESSURE_WATER_VAPOR),
        (c.CVV, i4_constants.SPECIFIC_HEAT_CAPACITY_VOLUME_WATER_VAPOR),
        (c.CLW, i4_constants.SPECIFIC_HEAT_CAPACITY_LIQUID_WATER),
        (c.RHOH2O, i4_constants.WATER_DENSITY),
        (c.TMELT, i4_constants.MELTING_TEMPERATURE),
        (c.T3, i4_constants.WATER_TRIPLE_POINT_TEMPERATURE),
        (c.ALV, i4_constants.LATENT_HEAT_FOR_VAPORISATION),
        (c.ALS, i4_constants.LATENT_HEAT_FOR_SUBLIMATION),
        (c.ALF, i4_constants.LATENT_HEAT_FOR_FUSION),
        (c.VTMPC1, i4_constants.RV_O_RD_MINUS_1),
        (c.GRAV, i4_constants.GRAVITATIONAL_ACCELERATION),
        (c.GRAV_O_RD, i4_constants.GRAV_O_RD),
        (c.GRAV_O_CPD, i4_constants.GRAV_O_CPD),
        (c.P0REF, i4_constants.REFERENCE_PRESSURE),
        (c.RD_O_P0REF, i4_constants.RD_O_P0REF),
        (c.P0SL_BG, i4_constants.SEA_LEVEL_PRESSURE),
        (c.T0SL_BG, i4_constants.SEA_LEVEL_TEMPERATURE),
        (c.DEL_T_BG, i4_constants.DELTA_TEMPERATURE),
        (c.H_SCAL_BG, i4_constants.HEIGHT_SCALE_FOR_REFERENCE_ATMOSPHERE),
        (c.RD_O_CPD, i4_constants.RD_O_CPD),
        (c.CPD_O_RD, i4_constants.CPD_O_RD),
        (c.RD_O_CVD, i4_constants.RD_O_CVD),
        (c.CVD_O_RD, i4_constants.CVD_O_RD),
        (c.EARTH_RADIUS, i4_constants.EARTH_RADIUS),
        (c.EARTH_ANGULAR_VELOCITY, i4_constants.EARTH_ANGULAR_VELOCITY),
    ]
    for ours, theirs in pairs:
        assert ours == float(theirs)


def _cell_k_fields(*arrays: np.ndarray) -> tuple:
    import gt4py.next as gtx
    from icon4py.model.common import dimension as dims

    return tuple(gtx.as_field((dims.CellDim, dims.KDim), a) for a in arrays)


def test_thetav_temperature_diagnosis_matches_icon4py_field_operator() -> None:
    """ICON-sc thermo vs icon4py ``_diagnose_virtual_temperature_and_temperature``
    (embedded execution) on a realistic (θv, exner, q…) sample — 1e-12."""
    from icon4py.model.common.diagnostic_calculations.stencils.diagnose_temperature import (
        _diagnose_virtual_temperature_and_temperature,
    )

    rng = np.random.default_rng(42)
    shape = (8, 12)
    exner = rng.uniform(0.4, 1.01, shape)
    theta_v = rng.uniform(260.0, 500.0, shape)
    qv = rng.uniform(0.0, 0.03, shape)
    qc, qi, qr, qs, qg = (rng.uniform(0.0, 0.004, shape) for _ in range(5))

    fields = _cell_k_fields(qv, qc, qi, qr, qs, qg, theta_v, exner)
    tempv_out, temp_out = _cell_k_fields(np.zeros(shape), np.zeros(shape))
    _diagnose_virtual_temperature_and_temperature(
        *fields, out=(tempv_out, temp_out), offset_provider={}
    )

    qsum = qc + qi + qr + qs + qg
    temp_icon_sc = thermo.temperature_from_thetav_exner(theta_v, exner, qv, qsum)
    assert_allclose(temp_icon_sc, temp_out.asnumpy(), rtol=RTOL, atol=0.0, names="air_temperature")
    # and the inverse direction reproduces theta_v from the icon4py-diagnosed temp
    theta_back = thermo.virtual_potential_temperature(temp_out.asnumpy(), exner, qv, qsum)
    assert_allclose(
        theta_back, theta_v, rtol=RTOL, atol=0.0, names="icon:virtual_potential_temperature"
    )


def test_reference_atmosphere_matches_icon4py_field_operator() -> None:
    """ICON-sc reference-state helpers vs icon4py
    ``_compute_reference_atmosphere_cell_fields`` (embedded) — 1e-12."""
    from icon4py.model.common.metrics.reference_atmosphere import (
        _compute_reference_atmosphere_cell_fields,
    )

    z = np.linspace(0.0, 40_000.0, 41)
    z_mc = np.broadcast_to(z, (3, z.size)).copy()
    (z_field,) = _cell_k_fields(z_mc)
    theta_out, exner_out, rho_out = _cell_k_fields(*(np.zeros_like(z_mc) for _ in range(3)))
    _compute_reference_atmosphere_cell_fields(
        z_mc=z_field,
        p0ref=c.P0REF,
        p0sl_bg=c.P0SL_BG,
        grav=c.GRAV,
        cpd=c.CPD,
        rd=c.RD,
        h_scal_bg=c.H_SCAL_BG,
        t0sl_bg=c.T0SL_BG,
        del_t_bg=c.DEL_T_BG,
        out=(theta_out, exner_out, rho_out),
        offset_provider={},
    )
    assert_allclose(
        vgrid.reference_exner(z_mc),
        exner_out.asnumpy(),
        rtol=RTOL,
        atol=0.0,
        names="icon:exner_ref_mc",
    )
    assert_allclose(
        vgrid.reference_potential_temperature(z_mc),
        theta_out.asnumpy(),
        rtol=RTOL,
        atol=0.0,
        names="icon:theta_ref_mc",
    )
    assert_allclose(
        vgrid.reference_rho(z_mc),
        rho_out.asnumpy(),
        rtol=RTOL,
        atol=0.0,
        names="icon:rho_ref_mc",
    )
