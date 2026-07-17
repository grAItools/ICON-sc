"""ICON variable-registry seed (architecture §2.5, S06).

One literal table maps each canonical name to canonical units, CF standard name (where
CF has one), ICON Fortran short name, and (later, for ingestion only) the GRIB2
triplet. Naming follows §2.5 as enforced by :mod:`symcon.core.state.names`: CF
standard names are canonical and unprefixed; solver-internal quantities live in the
``icon:`` namespace.

Provenance (REFERENCES.lock, S06):

- prognostics/tracers/diagnostics: icon4py v0.2.0 ``states/data.py`` short names
  (``rho``/``w``/``theta_v``/``exner``/``vn``/…) — the first 18 rows were seeded by
  S02 in :mod:`symcon.core.state.names` and are re-asserted (not re-registered) here;
- interface-level fields ``pres_ifc``/``temp_ifc`` and the tendency-bus slots
  ``ddt_exner_phy`` (ICON ``t_nh_diag``, ``mo_nonhydro_types.f90``) and the
  ``ddt_temp*``/``ddt_q*`` family (ICON ``prm_nwp_tend`` naming,
  ``mo_nwp_phy_types.f90``);
- metric/reference-state fields ``z_mc``/``z_ifc``/``ddqz_z_full``/``ddqz_z_half``/
  ``*_ref_mc`` (ICON ``t_nh_metrics``; icon4py ``metric_fields``/
  ``reference_atmosphere``).

Unit-string discipline: Exner is ``"1"`` (PLAN pitfall — never "dimensionless");
tracer mass fractions are ``"1"``, their tendencies ``"s-1"``.

Importing this module seeds the registry (idempotently: rows already registered by
symcon.core are verified for consistency instead). ``QUANTITIES`` (frozen interface)
is the full table, insertion-ordered.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from symcon.core.state.names import (
    NamesRegistryError,
    QuantityDef,
    known_quantities,
    lookup_quantity,
    register_quantity,
)

__all__ = ["QUANTITIES"]

#: Literal seed table: (name, units, cf_name, icon_name).
#: ``cf_name`` is ``None`` for unprefixed rows whose canonical name *is* the CF
#: standard name (registry default) and must be ``None`` for ``icon:`` rows.
_ROWS: Final[tuple[tuple[str, str, str | None, str | None], ...]] = (
    # --- prognostics (icon4py states/data.py; ICON t_nh_prog) ----------------------
    ("air_density", "kg m-3", None, "rho"),
    ("upward_air_velocity", "m s-1", None, "w"),
    ("icon:virtual_potential_temperature", "K", None, "theta_v"),
    ("icon:exner_function", "1", None, "exner"),
    ("icon:normal_wind", "m s-1", None, "vn"),  # placeholder until lane B (S11+)
    ("icon:tangential_wind", "m s-1", None, "vt"),
    # --- tracers (mass fractions, unit "1") -----------------------------------------
    ("specific_humidity", "1", None, "qv"),
    ("specific_cloud_content", "1", None, "qc"),
    ("specific_ice_content", "1", None, "qi"),
    ("specific_rain_content", "1", None, "qr"),
    ("specific_snow_content", "1", None, "qs"),
    ("specific_graupel_content", "1", None, "qg"),
    # --- diagnostics (ICON t_nh_diag) ------------------------------------------------
    ("eastward_wind", "m s-1", None, "u"),
    ("northward_wind", "m s-1", None, "v"),
    ("air_temperature", "K", None, "temp"),
    ("air_virtual_temperature", "K", None, "tempv"),
    ("air_pressure", "Pa", None, "pres"),
    ("air_pressure_at_ground_level", "Pa", None, "pres_sfc"),
    ("air_pressure_on_interface_levels", "Pa", None, "pres_ifc"),
    ("air_temperature_on_interface_levels", "K", None, "temp_ifc"),
    # --- vertical grid / metrics (ICON t_nh_metrics; icon4py metric fields) ---------
    # CF: "altitude" is height above the geoid — ICON's z_mc/z_ifc.
    ("altitude", "m", None, "z_mc"),
    ("altitude_on_interface_levels", "m", None, "z_ifc"),
    ("icon:ddqz_z_full", "m", None, "ddqz_z_full"),
    ("icon:ddqz_z_half", "m", None, "ddqz_z_half"),
    # --- reference state (mo_vertical_grid.f90; icon4py reference_atmosphere.py) ----
    ("icon:exner_ref_mc", "1", None, "exner_ref_mc"),
    ("icon:theta_ref_mc", "K", None, "theta_ref_mc"),
    ("icon:rho_ref_mc", "kg m-3", None, "rho_ref_mc"),
    # --- tendency-bus slots (§4.3; ICON prm_nwp_tend/t_nh_diag naming) --------------
    ("icon:ddt_temp", "K s-1", None, "ddt_temp"),
    ("icon:ddt_qv", "s-1", None, "ddt_qv"),
    ("icon:ddt_qc", "s-1", None, "ddt_qc"),
    ("icon:ddt_qi", "s-1", None, "ddt_qi"),
    ("icon:ddt_qr", "s-1", None, "ddt_qr"),
    ("icon:ddt_qs", "s-1", None, "ddt_qs"),
    ("icon:ddt_qg", "s-1", None, "ddt_qg"),
    ("icon:ddt_exner_phy", "s-1", None, "ddt_exner_phy"),
    # normal-wind slow-tendency slot consumed by the S12 dycore (ICON t_nh_diag,
    # mo_nonhydro_types.f90; icon4py DiagnosticStateNonHydro
    # normal_wind_tendency_due_to_slow_physics_process — REFERENCES.lock
    # icon4py-solve-nonhydro).
    ("icon:ddt_vn_phy", "m s-2", None, "ddt_vn_phy"),
    # slow-forcing temperature slot consumed by the S09 SCM bus demo (symcon-only
    # slot: no ICON Fortran symbol, hence no short name).
    ("icon:ddt_temperature_slow", "K s-1", None, None),
    # --- microphysics (S08; gscp granule + ICON prm_nwp_diag naming) -----------------
    # cloud droplet number concentration consumed by the one-moment graupel scheme
    # (icon4py granule input ``qnc`` [1/m3]; ICON ``qnc_s``/``cloud_num``,
    # mo_nwp_gscp_interface.f90 — REFERENCES.lock icon-fortran-graupel).
    ("icon:qnc", "m-3", None, "qnc"),
    # grid-scale surface precipitation rates [kg/m2/s] (ICON prm_nwp_diag,
    # mo_nwp_phy_types.f90:277-280; icon4py exit-savepoint fields *_gsp_rate).
    ("icon:rain_gsp_rate", "kg m-2 s-1", None, "rain_gsp_rate"),
    ("icon:snow_gsp_rate", "kg m-2 s-1", None, "snow_gsp_rate"),
    ("icon:ice_gsp_rate", "kg m-2 s-1", None, "ice_gsp_rate"),
    ("icon:graupel_gsp_rate", "kg m-2 s-1", None, "graupel_gsp_rate"),
    # --- S11 static state: metrics factory outputs (ICON t_nh_metrics; icon4py --------
    # metrics_attributes.py — REFERENCES.lock icon4py-metrics-interp-factories).
    # Unit policy: icon4py/ICON declare no units for these solver-internal
    # coefficients; symcon records "1" for weight/mask-like fields, "m"/"m-1"/"m-2"
    # where the defining formula fixes a length dimension (documented per row).
    ("icon:inv_ddqz_z_full", "m-1", None, "inv_ddqz_z_full"),  # 1/ddqz_z_full [m]
    ("icon:ddqz_z_full_e", "m", None, "ddqz_z_full_e"),  # layer thickness at edges
    ("icon:scalfac_dd3d", "1", None, "scalfac_dd3d"),  # 3d-divdamp vertical scaling
    ("icon:rayleigh_w", "1", None, "rayleigh_w"),  # Klemp-damping profile (x 1/tau0)
    ("icon:coeff1_dwdz", "m-1", None, "coeff1_dwdz"),  # 2nd-order dw/dz weights
    ("icon:coeff2_dwdz", "m-1", None, "coeff2_dwdz"),
    ("icon:theta_ref_ic", "K", None, "theta_ref_ic"),
    ("icon:theta_ref_me", "K", None, "theta_ref_me"),
    ("icon:rho_ref_me", "kg m-3", None, "rho_ref_me"),
    ("icon:d_exner_dz_ref_ic", "m-1", None, "d_exner_dz_ref_ic"),  # d(exner[1])/dz
    ("icon:d2dexdz2_fac1_mc", "m-1", None, "d2dexdz2_fac1_mc"),  # d/dz factors of
    ("icon:d2dexdz2_fac2_mc", "m-2", None, "d2dexdz2_fac2_mc"),  # d(exner)/dz/theta
    ("icon:ddxn_z_full", "1", None, "ddxn_z_full"),  # terrain slope (normal) dz/dn
    ("icon:ddxt_z_full", "1", None, "ddxt_z_full"),  # terrain slope (tangential)
    ("icon:vwind_impl_wgt", "1", None, "vwind_impl_wgt"),
    ("icon:vwind_expl_wgt", "1", None, "vwind_expl_wgt"),
    ("icon:exner_exfac", "1", None, "exner_exfac"),
    ("icon:wgtfac_c", "1", None, "wgtfac_c"),  # full->half interpolation weights
    ("icon:wgtfac_e", "1", None, "wgtfac_e"),
    ("icon:wgtfacq_c", "1", None, "wgtfacq_c"),  # quadratic surface extrapolation
    ("icon:wgtfacq_e", "1", None, "wgtfacq_e"),
    ("icon:pg_exdist", "m", None, "pg_exdist"),  # pressure-gradient extrap. distance
    ("icon:mask_prog_halo_c", "1", None, "mask_prog_halo_c"),  # bool mask
    ("icon:hmask_dd3d", "1", None, "hmask_dd3d"),
    ("icon:zdiff_gradp", "m", None, "zdiff_gradp"),  # height distance to neighbor
    ("icon:vertoffset_gradp", "1", None, "vertoffset_gradp"),  # int level offsets
    ("icon:nflat_gradp", "1", None, "nflat_gradp"),  # scalar level index
    ("icon:coeff_gradekin", "m-1", None, "coeff_gradekin"),  # 1/dual_edge_length x ±1
    ("icon:zd_diffcoef", "1", None, "zd_diffcoef"),  # terrain-diffusion coefficient
    ("icon:zd_intcoef", "1", None, "zd_intcoef"),
    ("icon:zd_vertoffset", "1", None, "zd_vertoffset"),  # int level offsets
    # geopotential at full-level cell centers (ICON t_nh_metrics%geopot; consumed by
    # the S13 JW initializer's Newton fit — REFERENCES.lock icon4py-driver-jw).
    ("icon:geopot", "m2 s-2", None, "geopot"),
    # --- S11 static state: interpolation factory outputs (ICON t_int_state; icon4py --
    # interpolation_attributes.py). geofac_* carry the 1/length(s) of their stencils.
    ("icon:c_lin_e", "1", None, "c_lin_e"),
    ("icon:e_bln_c_s", "1", None, "e_bln_c_s"),
    ("icon:geofac_div", "m-1", None, "geofac_div"),  # edge_length/cell_area
    ("icon:geofac_rot", "m-1", None, "geofac_rot"),  # dual_edge_length/dual_area
    ("icon:geofac_n2s", "m-2", None, "geofac_n2s"),  # nabla2-scalar stencil
    ("icon:geofac_grdiv", "m-2", None, "geofac_grdiv"),  # gradient-of-divergence
    # Green-Gauss gradient factors: ICON stores one array geofac_grg(:,:,:,1:2);
    # the registry needs unique short names, hence the _x/_y suffixes (icon4py's
    # savepoint/factory split them the same way).
    ("icon:geofac_grg_x", "m-1", None, "geofac_grg_x"),
    ("icon:geofac_grg_y", "m-1", None, "geofac_grg_y"),
    ("icon:nudgecoeff_e", "1", None, "nudgecoeff_e"),
    ("icon:rbf_vec_coeff_v1", "1", None, "rbf_vec_coeff_v1"),
    ("icon:rbf_vec_coeff_v2", "1", None, "rbf_vec_coeff_v2"),
    ("icon:rbf_vec_coeff_e", "1", None, "rbf_vec_coeff_e"),
    ("icon:c_intp", "1", None, "c_intp"),
    # Tangent-plane neighbor-cell positions: ICON pos_on_tplane_e(:,:,:,1:2), split
    # into _x/_y slabs like icon4py's savepoints (unique short names required).
    ("icon:pos_on_tplane_e_x", "m", None, "pos_on_tplane_e_x"),
    ("icon:pos_on_tplane_e_y", "m", None, "pos_on_tplane_e_y"),
    ("icon:e_flx_avg", "1", None, "e_flx_avg"),
)


def _seed() -> dict[str, QuantityDef]:
    """Register every row not already present; verify consistency of the rest."""
    table: dict[str, QuantityDef] = {}
    already = set(known_quantities())
    for name, units, cf_name, icon_name in _ROWS:
        if name in already:
            quantity = lookup_quantity(name)
            if quantity.units != units or quantity.icon_name != icon_name:
                raise NamesRegistryError(
                    f"registry seed conflict for {name!r}: core registered "
                    f"(units={quantity.units!r}, icon={quantity.icon_name!r}), the ICON "
                    f"table says (units={units!r}, icon={icon_name!r})."
                )
        else:
            quantity = register_quantity(name, units, cf_name=cf_name, icon_name=icon_name)
        table[name] = quantity
    return table


#: The ICON registry-seed table (frozen interface, SPEC S06): canonical name →
#: :class:`~symcon.core.state.names.QuantityDef`, in table order.
QUANTITIES: Final[Mapping[str, QuantityDef]] = MappingProxyType(_seed())
