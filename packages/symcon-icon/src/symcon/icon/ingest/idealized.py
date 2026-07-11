"""Jablonowski-Williamson baroclinic-wave initial state (SPEC S13; architecture §7.3).

``jablonowski_williamson(grid, vgrid, cfg, *, static, ...)`` builds the JW initial
state as a valid symcon state dict. Reference algorithm: the icon4py driver testcase
``model_initialization_jabw`` (REFERENCES.lock ``icon4py-driver-jw``), which
transcribes ICON's ``mo_nh_jabw_exp.f90::init_nh_state_prog_jabw`` (REFERENCES.lock
``icon-fortran-diffusion-jabw``); DCMIP/JW-paper constants are byte-identical between
the two.

Delegation policy (SPEC: "delegate to the latter if importable"): the wind projection
(``zonalwind_2_normalwind_ndarray`` — which takes the perturbation amplitude ``jw_up``
as an *argument*) and the hydrostatic adjustment (``hydrostatic_adjustment_ndarray``)
are called on the pinned icon4py driver directly. The per-level Newton fit of η
against the geopotential and the η_v cell→edge interpolation are transcribed in numpy
(the donor buries ``jw_up = 0.0`` as a function-local constant and its cell→edge step
is a gt4py program bound to its own serialbox reads, so the *loop* cannot be
delegated with a configurable perturbation); with
``cfg.perturbation_amplitude == 0`` the result must equal the donor's output to
1e-12 — asserted by the S13 delegation-parity datatest, not assumed.

The upstream fit runs against the **serialized** ``geopot`` metric field (the donor is
not fully analytic); symcon takes it through the ``static`` mapping under the
registry name ``icon:geopot`` (from the archive's metrics savepoint or a metrics
source that provides it).
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import Any, Final

import numpy as np

from symcon.core.state import canonical_units, make_dataarray
from symcon.core.time import datetime
from symcon.icon import names as _names  # noqa: F401  (registry seed side effect)
from symcon.icon.grid.grid import IconGrid
from symcon.icon.grid.vertical import VerticalGrid

__all__ = ["JablonowskiWilliamsonConfig", "jablonowski_williamson"]

#: The static fields the initializer consumes (registry names; all but
#: ``icon:geopot``/``icon:c_lin_e`` feed the hydrostatic adjustment).
STATIC_FIELDS: Final[tuple[str, ...]] = (
    "icon:c_lin_e",
    "icon:d_exner_dz_ref_ic",
    "icon:ddqz_z_half",
    "icon:exner_ref_mc",
    "icon:geopot",
    "icon:theta_ref_ic",
    "icon:theta_ref_mc",
    "icon:wgtfac_c",
)

#: JW paper / ICON ``mo_nh_jabw_exp.f90`` defined parameters (module PARAMETERs there;
#: function-locals in the icon4py donor — both transcribed, values identical).
_ETA_0: Final[float] = 0.252
_ETA_T: Final[float] = 0.2  # tropopause
_GAMMA: Final[float] = 0.005  # temperature lapse rate [K/m]
_DTEMP: Final[float] = 4.8e5  # empirical temperature difference [K]
_LON_PERTURBATION_CENTER: Final[float] = math.pi / 9.0  # 20 deg east
_LAT_PERTURBATION_CENTER: Final[float] = 2.0 * math.pi / 9.0  # 40 deg north
_NEWTON_ITERATIONS: Final[int] = 100


@dataclasses.dataclass(frozen=True)
class JablonowskiWilliamsonConfig:
    """JW testcase knobs (ICON ``nh_test_nml``: ``jw_up``/``jw_u0``/``jw_temp0``).

    ``perturbation_amplitude`` is ICON's ``jw_up`` [m/s]: 0 (default, and the icon4py
    donor's hard-wired value) gives the zonally symmetric steady state ("jabw_s");
    the classic baroclinic-wave test uses 1.0 (JW06 paper §4; values ≤ 1e-20 are
    treated as off, matching the donor's guard).
    """

    perturbation_amplitude: float = 0.0  # ICON nh_test_nml:jw_up [m/s]
    u0: float = 35.0  # ICON nh_test_nml:jw_u0 [m/s]
    temperature0: float = 288.0  # ICON nh_test_nml:jw_temp0 [K]
    surface_pressure: float = 100000.0  # p_sfc [Pa]
    time: Any | None = None  #: state["time"] (None -> datetime(2000, 1, 1))


def _as_numpy(value: Any) -> np.ndarray:
    """Host numpy view of a static entry (DataArray, gt4py field or ndarray)."""
    if hasattr(value, "asnumpy"):
        return np.asarray(value.asnumpy())
    data = value.data if hasattr(value, "data") and hasattr(value, "dims") else value
    data = data.get() if hasattr(data, "get") else data
    return np.asarray(data)


def _geometry_arrays(
    grid: IconGrid | Any,
    edge_geometry: Any | None,
    cell_geometry: Any | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(cell_lat, edge_lat, edge_lon, primal_normal_x) as numpy arrays."""
    if edge_geometry is not None and cell_geometry is not None:
        return (
            np.asarray(cell_geometry.cell_center_lat.asnumpy()),
            np.asarray(edge_geometry.edge_center[0].asnumpy()),
            np.asarray(edge_geometry.edge_center[1].asnumpy()),
            np.asarray(edge_geometry.primal_normal[0].asnumpy()),
        )
    if isinstance(grid, IconGrid):
        from icon4py.model.common.grid import geometry_attributes as geometry_meta

        source = grid.icon4py_geometry
        return (
            np.asarray(source.get(geometry_meta.CELL_LAT).asnumpy()),
            np.asarray(source.get(geometry_meta.EDGE_LAT).asnumpy()),
            np.asarray(source.get(geometry_meta.EDGE_LON).asnumpy()),
            np.asarray(source.get(geometry_meta.EDGE_NORMAL_U).asnumpy()),
        )
    raise ValueError(
        "jablonowski_williamson: hosting on a raw icon4py grid requires explicit "
        "edge_geometry and cell_geometry."
    )


def jablonowski_williamson(
    grid: IconGrid | Any,
    vgrid: VerticalGrid | Any,
    cfg: JablonowskiWilliamsonConfig | None = None,
    *,
    static: Mapping[str, Any],
    edge_geometry: Any | None = None,
    cell_geometry: Any | None = None,
) -> dict[str, Any]:
    """The JW initial state as a symcon state dict (frozen interface, SPEC S13).

    ``grid``/``vgrid`` follow the S12/S13 component convention (symcon objects or
    raw icon4py ones — raw grids need explicit geometry). ``static`` must provide
    :data:`STATIC_FIELDS` (S11 DataArrays, icon4py fields or ndarrays).

    Returns ``time`` + the five prognostics (``icon:normal_wind``,
    ``upward_air_velocity_on_interface_levels`` = 0, ``air_density``,
    ``icon:exner_function``, ``icon:virtual_potential_temperature``) + the analytic
    diagnostics the donor also produces (``air_temperature``, ``air_pressure``,
    ``air_pressure_on_interface_levels`` — surface slot = p_sfc, rest 0, exactly as
    upstream initializes them).
    """
    from icon4py.model.common import constants as phy_const
    from icon4py.model.common.grid import horizontal as h_grid
    from icon4py.model.driver.testcases import utils as testcases_utils

    cfg = cfg if cfg is not None else JablonowskiWilliamsonConfig()
    i4_grid = grid.icon4py_grid if isinstance(grid, IconGrid) else grid
    nlev = int(i4_grid.num_levels)
    vgrid_nlev = vgrid.nlev if isinstance(vgrid, VerticalGrid) else int(vgrid.num_levels)
    if vgrid_nlev != nlev:
        raise ValueError(
            f"jablonowski_williamson: grid carries num_levels={nlev} but vgrid has "
            f"nlev={vgrid_nlev}."
        )
    missing = [f for f in STATIC_FIELDS if f not in static]
    if missing:
        raise ValueError(f"jablonowski_williamson: static state is missing {missing!r}.")

    cell_lat, edge_lat, edge_lon, primal_normal_x = _geometry_arrays(
        grid, edge_geometry, cell_geometry
    )
    wgtfac_c = _as_numpy(static["icon:wgtfac_c"])
    ddqz_z_half = _as_numpy(static["icon:ddqz_z_half"])
    theta_ref_mc = _as_numpy(static["icon:theta_ref_mc"])
    theta_ref_ic = _as_numpy(static["icon:theta_ref_ic"])
    exner_ref_mc = _as_numpy(static["icon:exner_ref_mc"])
    d_exner_dz_ref_ic = _as_numpy(static["icon:d_exner_dz_ref_ic"])
    geopot = _as_numpy(static["icon:geopot"])
    c_lin_e = _as_numpy(static["icon:c_lin_e"])

    num_cells = int(i4_grid.num_cells)
    jw_up = float(cfg.perturbation_amplitude)
    jw_u0 = float(cfg.u0)
    jw_temp0 = float(cfg.temperature0)
    p_sfc = float(cfg.surface_pressure)
    ps_o_p0ref = p_sfc / phy_const.P0REF
    lapse_rate = phy_const.RD * _GAMMA / phy_const.GRAV

    # -- per-level Newton fit of eta against the serialized geopotential (donor
    #    model_initialization_jabw l.158-228, transcribed; numpy == its CPU path) ------
    sin_lat = np.sin(cell_lat)
    cos_lat = np.cos(cell_lat)
    fac1 = 1.0 / 6.3 - 2.0 * (sin_lat**6) * (cos_lat**2 + 1.0 / 3.0)
    fac2 = (
        (8.0 / 5.0 * (cos_lat**3) * (sin_lat**2 + 2.0 / 3.0) - 0.25 * math.pi)
        * phy_const.EARTH_RADIUS
        * phy_const.EARTH_ANGULAR_VELOCITY
    )

    eta_v = np.zeros((num_cells, nlev), dtype=np.float64)
    exner = np.zeros((num_cells, nlev), dtype=np.float64)
    rho = np.zeros((num_cells, nlev), dtype=np.float64)
    theta_v = np.zeros((num_cells, nlev), dtype=np.float64)
    temperature = np.zeros((num_cells, nlev), dtype=np.float64)
    pressure = np.zeros((num_cells, nlev), dtype=np.float64)

    for k in range(nlev - 1, -1, -1):
        eta_old = np.full(num_cells, 1.0e-7, dtype=np.float64)
        temperature_jw = np.zeros(num_cells, dtype=np.float64)
        for _ in range(_NEWTON_ITERATIONS):
            eta_v[:, k] = (eta_old - _ETA_0) * math.pi * 0.5
            cos_etav = np.cos(eta_v[:, k])
            sin_etav = np.sin(eta_v[:, k])

            temperature_avg = jw_temp0 * (eta_old**lapse_rate)
            geopot_avg = jw_temp0 * phy_const.GRAV / _GAMMA * (1.0 - eta_old**lapse_rate)
            temperature_avg = np.where(
                eta_old < _ETA_T,
                temperature_avg + _DTEMP * ((_ETA_T - eta_old) ** 5),
                temperature_avg,
            )
            geopot_avg = np.where(
                eta_old < _ETA_T,
                geopot_avg
                - phy_const.RD
                * _DTEMP
                * (
                    (np.log(eta_old / _ETA_T) + 137.0 / 60.0) * (_ETA_T**5)
                    - 5.0 * (_ETA_T**4) * eta_old
                    + 5.0 * (_ETA_T**3) * (eta_old**2)
                    - 10.0 / 3.0 * (_ETA_T**2) * (eta_old**3)
                    + 1.25 * _ETA_T * (eta_old**4)
                    - 0.2 * (eta_old**5)
                ),
                geopot_avg,
            )

            geopot_jw = geopot_avg + jw_u0 * (cos_etav**1.5) * (
                fac1 * jw_u0 * (cos_etav**1.5) + fac2
            )
            temperature_jw = (
                temperature_avg
                + 0.75
                * eta_old
                * math.pi
                * jw_u0
                / phy_const.RD
                * sin_etav
                * np.sqrt(cos_etav)
                * (2.0 * jw_u0 * fac1 * (cos_etav**1.5) + fac2)
            )
            newton_function = geopot_jw - geopot[:, k]
            newton_function_prime = -phy_const.RD / eta_old * temperature_jw
            eta_old = eta_old - newton_function / newton_function_prime

        eta_v[:, k] = (eta_old - _ETA_0) * math.pi * 0.5
        exner[:, k] = (eta_old * ps_o_p0ref) ** phy_const.RD_O_CPD
        theta_v[:, k] = temperature_jw / exner[:, k]
        rho[:, k] = (
            exner[:, k] ** phy_const.CVD_O_RD * phy_const.P0REF / phy_const.RD / theta_v[:, k]
        )
        pressure[:, k] = phy_const.P0REF * exner[:, k] ** phy_const.CPD_O_RD
        temperature[:, k] = temperature_jw

    # -- eta_v cell -> edge (donor uses the cell_2_edge_interpolation program over
    #    [lateral_boundary_level_2, end); edges before that stay 0) --------------------
    e2c = np.asarray(i4_grid.get_connectivity("E2C").asnumpy())
    edge_domain = h_grid.domain(_edge_dim())
    start = int(i4_grid.end_index(edge_domain(h_grid.Zone.LATERAL_BOUNDARY_LEVEL_2)))
    eta_v_e = np.zeros((int(i4_grid.num_edges), nlev), dtype=np.float64)
    eta_v_e[start:, :] = (
        c_lin_e[start:, 0, np.newaxis] * eta_v[e2c[start:, 0], :]
        + c_lin_e[start:, 1, np.newaxis] * eta_v[e2c[start:, 1], :]
    )

    # -- normal wind: delegated to the pinned donor helper (jw_up is an argument) ------
    vn = testcases_utils.zonalwind_2_normalwind_ndarray(
        grid=i4_grid,
        jw_u0=jw_u0,
        jw_up=jw_up,
        lat_perturbation_center=_LAT_PERTURBATION_CENTER,
        lon_perturbation_center=_LON_PERTURBATION_CENTER,
        edge_lat=edge_lat,
        edge_lon=edge_lon,
        primal_normal_x=primal_normal_x,
        eta_v_e=eta_v_e,
    )

    # -- hydrostatic adjustment: delegated to the pinned donor helper ------------------
    rho, exner, theta_v = testcases_utils.hydrostatic_adjustment_ndarray(
        wgtfac_c=wgtfac_c,
        ddqz_z_half=ddqz_z_half,
        exner_ref_mc=exner_ref_mc,
        d_exner_dz_ref_ic=d_exner_dz_ref_ic,
        theta_ref_mc=theta_ref_mc,
        theta_ref_ic=theta_ref_ic,
        rho=rho,
        exner=exner,
        theta_v=theta_v,
        num_levels=nlev,
    )

    pressure_ifc = np.zeros((num_cells, nlev + 1), dtype=np.float64)
    pressure_ifc[:, -1] = p_sfc
    w = np.zeros((num_cells, nlev + 1), dtype=np.float64)

    def field(name: str, values: np.ndarray, dims: tuple[str, str]) -> Any:
        return make_dataarray(
            values,
            name=name,
            dims=dims,
            units=canonical_units(name),
            location="edge" if dims[0] == "edge" else "cell",
        )

    return {
        "time": cfg.time if cfg.time is not None else datetime(2000, 1, 1),
        "icon:normal_wind": field("icon:normal_wind", np.asarray(vn), ("edge", "height")),
        "upward_air_velocity_on_interface_levels": field(
            "upward_air_velocity_on_interface_levels", w, ("cell", "height_interface")
        ),
        "air_density": field("air_density", rho, ("cell", "height")),
        "icon:exner_function": field("icon:exner_function", exner, ("cell", "height")),
        "icon:virtual_potential_temperature": field(
            "icon:virtual_potential_temperature", theta_v, ("cell", "height")
        ),
        "air_temperature": field("air_temperature", temperature, ("cell", "height")),
        "air_pressure": field("air_pressure", pressure, ("cell", "height")),
        "air_pressure_on_interface_levels": field(
            "air_pressure_on_interface_levels", pressure_ifc, ("cell", "height_interface")
        ),
    }


def _edge_dim() -> Any:
    from icon4py.model.common import dimension as i4_dims

    return i4_dims.EdgeDim
