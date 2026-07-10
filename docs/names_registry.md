# Variable registry

<!-- GENERATED FILE — do not edit. Regenerate with `uv run python tools/names_audit.py`
     after changing the seed tables in symcon.core.state.names / symcon.icon.names. -->

Canonical quantity names (architecture §2.5): CF standard names are canonical and
unprefixed; solver-internal quantities live in the `icon:` namespace. The GRIB2
column exists for table-driven *ingestion* only (§7.2). The `_on_interface_levels`
suffix marks the `height_interface` dim variant of a quantity and inherits its base
quantity's canonical units.

| canonical name | units | CF standard name | ICON | GRIB2 |
|---|---|---|---|---|
| `air_density` | `kg m-3` | air_density | `rho` | — |
| `upward_air_velocity` | `m s-1` | upward_air_velocity | `w` | — |
| `icon:virtual_potential_temperature` | `K` | — | `theta_v` | — |
| `icon:exner_function` | `1` | — | `exner` | — |
| `icon:normal_wind` | `m s-1` | — | `vn` | — |
| `icon:tangential_wind` | `m s-1` | — | `vt` | — |
| `specific_humidity` | `1` | specific_humidity | `qv` | — |
| `specific_cloud_content` | `1` | specific_cloud_content | `qc` | — |
| `specific_ice_content` | `1` | specific_ice_content | `qi` | — |
| `specific_rain_content` | `1` | specific_rain_content | `qr` | — |
| `specific_snow_content` | `1` | specific_snow_content | `qs` | — |
| `specific_graupel_content` | `1` | specific_graupel_content | `qg` | — |
| `eastward_wind` | `m s-1` | eastward_wind | `u` | — |
| `northward_wind` | `m s-1` | northward_wind | `v` | — |
| `air_temperature` | `K` | air_temperature | `temp` | — |
| `air_virtual_temperature` | `K` | air_virtual_temperature | `tempv` | — |
| `air_pressure` | `Pa` | air_pressure | `pres` | — |
| `air_pressure_at_ground_level` | `Pa` | air_pressure_at_ground_level | `pres_sfc` | — |
| `air_pressure_on_interface_levels` | `Pa` | air_pressure_on_interface_levels | `pres_ifc` | — |
| `air_temperature_on_interface_levels` | `K` | air_temperature_on_interface_levels | `temp_ifc` | — |
| `altitude` | `m` | altitude | `z_mc` | — |
| `altitude_on_interface_levels` | `m` | altitude_on_interface_levels | `z_ifc` | — |
| `icon:ddqz_z_full` | `m` | — | `ddqz_z_full` | — |
| `icon:ddqz_z_half` | `m` | — | `ddqz_z_half` | — |
| `icon:exner_ref_mc` | `1` | — | `exner_ref_mc` | — |
| `icon:theta_ref_mc` | `K` | — | `theta_ref_mc` | — |
| `icon:rho_ref_mc` | `kg m-3` | — | `rho_ref_mc` | — |
| `icon:ddt_temp` | `K s-1` | — | `ddt_temp` | — |
| `icon:ddt_qv` | `s-1` | — | `ddt_qv` | — |
| `icon:ddt_qc` | `s-1` | — | `ddt_qc` | — |
| `icon:ddt_qi` | `s-1` | — | `ddt_qi` | — |
| `icon:ddt_qr` | `s-1` | — | `ddt_qr` | — |
| `icon:ddt_qs` | `s-1` | — | `ddt_qs` | — |
| `icon:ddt_qg` | `s-1` | — | `ddt_qg` | — |
| `icon:ddt_exner_phy` | `s-1` | — | `ddt_exner_phy` | — |
| `icon:ddt_temperature_slow` | `K s-1` | — | — | — |
| `icon:qnc` | `m-3` | — | `qnc` | — |
| `icon:rain_gsp_rate` | `kg m-2 s-1` | — | `rain_gsp_rate` | — |
| `icon:snow_gsp_rate` | `kg m-2 s-1` | — | `snow_gsp_rate` | — |
| `icon:ice_gsp_rate` | `kg m-2 s-1` | — | `ice_gsp_rate` | — |
| `icon:graupel_gsp_rate` | `kg m-2 s-1` | — | `graupel_gsp_rate` | — |
