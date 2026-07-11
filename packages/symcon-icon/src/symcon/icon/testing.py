"""Column-state builders and the icon4py datatest bridge (S06).

Builders return *valid symcon states* — ``time`` plus boundary DataArrays built via
:func:`symcon.core.state.make_dataarray` with canonical units from the registry seed
(:mod:`symcon.icon.names`) — shaped ``(cell, height)`` / ``(cell, height_interface)``
on nominal (flat-terrain) ICON levels.

Datatest bridge: symcon depends on icon4py's own serialbox datatest machinery for
reference data (pooch-style download + cache handled by icon4py — never re-hosted,
never in git). ``icon4py-testing`` is an *optional* dependency
(``symcon-icon[datatest]``); when it is missing every re-exported fixture degrades to
an informative skip via :func:`require_datatest`. Data-marked tests import the
fixtures from here so that the cache location default
(``~/.cache/symcon/icon4py-testdata``, override with ``ICON4PY_TEST_DATA_PATH``) is
applied before ``icon4py.model.testing`` reads the environment.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
from typing import Any

import numpy as np
import numpy.typing as npt

from symcon.core.state import canonical_units, make_dataarray
from symcon.core.time import datetime
from symcon.icon import names as _names  # noqa: F401  (imported for its seeding side effect)
from symcon.icon import thermo
from symcon.icon._constants import GRAV, P0SL_BG, RD
from symcon.icon.grid.vertical import (
    SleveConfig,
    VerticalGrid,
    reference_pressure,
    reference_temperature,
)

__all__ = [
    "DATATEST_AVAILABLE",
    "MOIST_PROFILE_IDS",
    "download_grid_file",
    "isothermal_column",
    "moist_test_column",
    "require_datatest",
]

_F64 = npt.NDArray[np.float64]

_COLUMN_DIMS = ("cell", "height")
_INTERFACE_DIMS = ("cell", "height_interface")


def _field(name: str, profile: _F64, n_cell: int, dims: tuple[str, str]) -> Any:
    values = np.broadcast_to(profile, (n_cell, profile.shape[0])).copy()
    return make_dataarray(
        values, name=name, dims=dims, units=canonical_units(name), location="cell"
    )


def _column_state(
    grid: VerticalGrid,
    temperature: _F64,
    pressure: _F64,
    pressure_ifc: _F64,
    qv: _F64,
    *,
    n_cell: int,
    time: Any | None,
) -> dict[str, Any]:
    """Assemble a thermodynamically consistent column state from (T, p, qv).

    Derived fields use :mod:`symcon.icon.thermo` exactly, so builder states satisfy
    the S06 round-trip identities by construction: ``exner = exner_from_pressure(p)``,
    ``theta_v = virtual_potential_temperature(T, exner, qv)``, ``rho = p/(rd·tempv)``
    (ideal gas). Condensate loading starts at zero — satad/graupel create it.
    """
    exner = thermo.exner_from_pressure(pressure)
    theta_v = thermo.virtual_potential_temperature(temperature, exner, qv)
    tempv = thermo.virtual_temperature(temperature, qv)
    rho = pressure / (RD * tempv)
    zeros = np.zeros_like(temperature)
    zeros_ifc = np.zeros(grid.num_interface_levels, dtype=np.float64)

    state: dict[str, Any] = {"time": time if time is not None else datetime(2000, 1, 1)}
    full = {
        "air_temperature": temperature,
        "air_pressure": pressure,
        "icon:exner_function": exner,
        "icon:virtual_potential_temperature": theta_v,
        "air_virtual_temperature": tempv,
        "air_density": rho,
        "specific_humidity": qv,
        "specific_cloud_content": zeros,
        "specific_ice_content": zeros,
        "specific_rain_content": zeros,
        "specific_snow_content": zeros,
        "specific_graupel_content": zeros,
        "altitude": grid.full_level_heights,
        "icon:ddqz_z_full": grid.layer_thickness,
    }
    interface = {
        "upward_air_velocity_on_interface_levels": zeros_ifc,
        "air_pressure_on_interface_levels": pressure_ifc,
        "altitude_on_interface_levels": grid.interface_heights,
    }
    for name, profile in full.items():
        state[name] = _field(name, profile, n_cell, _COLUMN_DIMS)
    for name, profile in interface.items():
        state[name] = _field(name, profile, n_cell, _INTERFACE_DIMS)
    return state


def isothermal_column(
    nlev: int = 65,
    n_cell: int = 1,
    *,
    temperature: float = 250.0,
    surface_pressure: float = P0SL_BG,
    time: Any | None = None,
) -> dict[str, Any]:
    """A dry isothermal hydrostatic column on the default ICON vertical grid.

    ``p(z) = p_sfc · exp(-g·z / (rd·T))`` — the closed-form hydrostatic balance of an
    isothermal dry atmosphere (barometric formula with ICON's ``grav``/``rd``).
    """
    grid = VerticalGrid.from_config(SleveConfig(num_levels=nlev))
    z_mc = grid.full_level_heights
    z_ifc = grid.interface_heights
    temp = np.full(nlev, float(temperature), dtype=np.float64)
    pres = surface_pressure * np.exp(-GRAV * z_mc / (RD * temperature))
    pres_ifc = surface_pressure * np.exp(-GRAV * z_ifc / (RD * temperature))
    qv = np.zeros(nlev, dtype=np.float64)
    return _column_state(grid, temp, pres, pres_ifc, qv, n_cell=n_cell, time=time)


#: Known ``moist_test_column`` profiles.
MOIST_PROFILE_IDS = ("reference_dry", "reference_moist")

#: Synthetic humidity profile parameters for ``reference_moist`` (test fixture, not a
#: mined scientific constant: near-surface mass fraction and e-folding height chosen
#: at typical low-latitude magnitudes; the *thermodynamics* applied to them is ICON's).
_QV_SURFACE = 0.01
_QV_SCALE_HEIGHT = 2500.0


def moist_test_column(
    profile_id: str,
    nlev: int = 65,
    n_cell: int = 1,
    *,
    time: Any | None = None,
) -> dict[str, Any]:
    """A test column on the ICON reference atmosphere (frozen interface, SPEC S06).

    - ``"reference_dry"``: T/p from the ICON decaying-isothermal reference atmosphere
      (``mo_vertical_grid.f90``), no moisture;
    - ``"reference_moist"``: same T/p with an exponentially decaying water-vapor
      profile ``qv(z) = qv0·exp(-z/hq)``; θv/tempv/rho pick up the moisture term.
    """
    if profile_id not in MOIST_PROFILE_IDS:
        raise ValueError(f"unknown profile_id {profile_id!r}; known: {MOIST_PROFILE_IDS}")
    grid = VerticalGrid.from_config(SleveConfig(num_levels=nlev))
    z_mc = grid.full_level_heights
    temp = reference_temperature(z_mc)
    pres = reference_pressure(z_mc)
    pres_ifc = reference_pressure(grid.interface_heights)
    if profile_id == "reference_moist":
        qv = _QV_SURFACE * np.exp(-z_mc / _QV_SCALE_HEIGHT)
    else:
        qv = np.zeros(nlev, dtype=np.float64)
    return _column_state(grid, temp, pres, pres_ifc, qv, n_cell=n_cell, time=time)


# --- icon4py datatest bridge ----------------------------------------------------------

# Default download/cache location for icon4py serialized test data; must be set
# before ``icon4py.model.testing.config`` is imported (it reads the env once).
# Guarded so that importing this module for the column builders alone (no
# ``symcon-icon[datatest]`` extra installed) mutates no process env.
if importlib.util.find_spec("icon4py.model.testing") is not None:
    os.environ.setdefault(
        "ICON4PY_TEST_DATA_PATH",
        str(pathlib.Path.home() / ".cache" / "symcon" / "icon4py-testdata"),
    )

try:
    import pytest as _pytest
    from icon4py.model.testing import definitions as icon4py_definitions
    from icon4py.model.testing.fixtures import (  # noqa: F401  (re-exported fixtures)
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        process_props,
    )
    from icon4py.model.testing.fixtures.datatest import (  # noqa: F401  (S11 re-exports)
        interpolation_savepoint,
        metrics_savepoint,
        topography_savepoint,
    )

    DATATEST_AVAILABLE = True

    @_pytest.fixture(params=[icon4py_definitions.Experiments.GAUSS3D], ids=lambda e: e.name)
    def experiment_description(request: Any) -> Any:
        """Default experiment for symcon datatests: GAUSS3D.

        Overrides icon4py's three-experiment default — ``exclaim_gauss3d`` is the
        smallest serialized archive (~57 MB vs 4-7 GB); parametrize explicitly in a
        test to use another experiment.
        """
        return request.param

except ImportError:  # icon4py-testing not installed (symcon-icon[datatest] extra)
    DATATEST_AVAILABLE = False
    icon4py_definitions = None  # type: ignore[assignment]


def require_datatest() -> None:
    """Skip the calling test when the icon4py datatest stack is unavailable."""
    import pytest

    if not DATATEST_AVAILABLE:
        pytest.skip(
            "icon4py datatest stack not installed — install symcon-icon[datatest] "
            "(icon4py-testing + serialbox4py) to run data-marked tests."
        )


def download_grid_file(grid_description: Any) -> pathlib.Path:
    """Fetch (or reuse from cache) the grid NetCDF for an icon4py ``GridDescription``.

    S11 helper: grid *files* download independently of the serialized experiment
    archives (``<root>/grids/<name>.tar.gz``, a few MB) into the shared datatest
    cache. Wraps icon4py's ``grid_utils._download_grid_file`` (private there — the
    public entry points bundle GridManager construction, which symcon does itself).
    """
    from icon4py.model.testing import grid_utils

    return pathlib.Path(grid_utils._download_grid_file(grid_description))
