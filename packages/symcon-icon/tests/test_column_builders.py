"""S06 column-state builders: valid symcon states, thermodynamically consistent."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from symcon.core.state import canonical_units
from symcon.core.testing import assert_allclose
from symcon.core.typing import FieldBuffer, HaloState, Location
from symcon.icon import thermo
from symcon.icon._constants import GRAV, P0SL_BG, RD
from symcon.icon.testing import MOIST_PROFILE_IDS, isothermal_column, moist_test_column

RTOL = 1e-12


def _assert_valid_state(state: dict) -> None:
    """A valid symcon state: time key + boundary DataArrays with the attrs schema
    (make_dataarray output), canonical units, coherent dims/shapes."""
    assert "time" in state
    fields = {k: v for k, v in state.items() if k != "time"}
    for name, field in fields.items():
        assert isinstance(field, xr.DataArray), name
        assert isinstance(field.data, FieldBuffer), name
        assert field.attrs["units"] == canonical_units(name), name
        assert field.attrs["location"] is Location.CELL, name
        assert field.attrs["halo"] is HaloState.VALID, name
        assert field.dims[0] == "cell", name
        if name.endswith("_on_interface_levels"):
            assert field.dims[1] == "height_interface", name
        else:
            assert field.dims[1] == "height", name
        assert field.dtype == np.float64, name


@pytest.mark.parametrize("n_cell", [1, 4])
def test_isothermal_column_is_valid_state(n_cell: int) -> None:
    state = isothermal_column(nlev=30, n_cell=n_cell)
    _assert_valid_state(state)
    assert state["air_temperature"].shape == (n_cell, 30)
    assert state["air_pressure_on_interface_levels"].shape == (n_cell, 31)


def test_isothermal_column_hydrostatics_and_thermo() -> None:
    state = isothermal_column(nlev=40, temperature=250.0)
    t = np.asarray(state["air_temperature"].data)
    p = np.asarray(state["air_pressure"].data)
    z = np.asarray(state["altitude"].data)
    assert np.all(t == 250.0)
    # barometric formula with ICON constants
    assert_allclose(
        p, P0SL_BG * np.exp(-GRAV * z / (RD * 250.0)), rtol=RTOL, atol=0.0, names="air_pressure"
    )
    # dry: tempv == temp, theta_v == temp/exner, rho ideal-gas consistent
    exner = np.asarray(state["icon:exner_function"].data)
    assert np.array_equal(exner, thermo.exner_from_pressure(p))
    assert np.array_equal(np.asarray(state["air_virtual_temperature"].data), t)
    rho = np.asarray(state["air_density"].data)
    assert_allclose(rho, p / (RD * t), rtol=RTOL, atol=0.0, names="air_density")
    theta_v = np.asarray(state["icon:virtual_potential_temperature"].data)
    qv = np.asarray(state["specific_humidity"].data)
    assert_allclose(
        thermo.temperature_from_thetav_exner(theta_v, exner, qv),
        t,
        rtol=RTOL,
        atol=0.0,
        names="air_temperature",
    )


@pytest.mark.parametrize("profile_id", MOIST_PROFILE_IDS)
def test_moist_test_column_profiles(profile_id: str) -> None:
    state = moist_test_column(profile_id, nlev=35)
    _assert_valid_state(state)
    qv = np.asarray(state["specific_humidity"].data)
    if profile_id == "reference_dry":
        assert np.all(qv == 0.0)
    else:
        assert qv[0, -1] > qv[0, 0] > 0.0  # decays with height (index 0 = top)
    # thermo round-trip closes on the builder state (acceptance-1 property, in vivo)
    t = np.asarray(state["air_temperature"].data)
    exner = np.asarray(state["icon:exner_function"].data)
    theta_v = np.asarray(state["icon:virtual_potential_temperature"].data)
    assert_allclose(
        thermo.temperature_from_thetav_exner(theta_v, exner, qv),
        t,
        rtol=RTOL,
        atol=0.0,
        names="air_temperature",
    )
    # condensate starts at zero (satad/graupel create it)
    for tracer in (
        "specific_cloud_content",
        "specific_ice_content",
        "specific_rain_content",
        "specific_snow_content",
        "specific_graupel_content",
    ):
        assert np.all(np.asarray(state[tracer].data) == 0.0)


def test_moist_test_column_unknown_profile() -> None:
    with pytest.raises(ValueError, match="unknown profile_id"):
        moist_test_column("nope")


def test_layer_thickness_field_matches_grid() -> None:
    state = isothermal_column(nlev=12)
    dz = np.asarray(state["icon:ddqz_z_full"].data)
    z_ifc = np.asarray(state["altitude_on_interface_levels"].data)
    assert_allclose(dz, z_ifc[:, :-1] - z_ifc[:, 1:], rtol=0.0, atol=0.0, names="icon:ddqz_z_full")
