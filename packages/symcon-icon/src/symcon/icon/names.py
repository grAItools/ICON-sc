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
    # slow-forcing temperature slot consumed by the S09 SCM bus demo (symcon-only
    # slot: no ICON Fortran symbol, hence no short name).
    ("icon:ddt_temperature_slow", "K s-1", None, None),
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
