# Variable registry

<!-- GENERATED FILE — do not edit. Regenerate with `uv run python tools/names_audit.py`
     after changing the seed tables in icon_sc.core.state.names / icon_sc.icon.names. -->

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
| `icon:ddt_vn_phy` | `m s-2` | — | `ddt_vn_phy` | — |
| `icon:ddt_temperature_slow` | `K s-1` | — | — | — |
| `icon:qnc` | `m-3` | — | `qnc` | — |
| `icon:rain_gsp_rate` | `kg m-2 s-1` | — | `rain_gsp_rate` | — |
| `icon:snow_gsp_rate` | `kg m-2 s-1` | — | `snow_gsp_rate` | — |
| `icon:ice_gsp_rate` | `kg m-2 s-1` | — | `ice_gsp_rate` | — |
| `icon:graupel_gsp_rate` | `kg m-2 s-1` | — | `graupel_gsp_rate` | — |
| `icon:inv_ddqz_z_full` | `m-1` | — | `inv_ddqz_z_full` | — |
| `icon:ddqz_z_full_e` | `m` | — | `ddqz_z_full_e` | — |
| `icon:scalfac_dd3d` | `1` | — | `scalfac_dd3d` | — |
| `icon:rayleigh_w` | `1` | — | `rayleigh_w` | — |
| `icon:coeff1_dwdz` | `m-1` | — | `coeff1_dwdz` | — |
| `icon:coeff2_dwdz` | `m-1` | — | `coeff2_dwdz` | — |
| `icon:theta_ref_ic` | `K` | — | `theta_ref_ic` | — |
| `icon:theta_ref_me` | `K` | — | `theta_ref_me` | — |
| `icon:rho_ref_me` | `kg m-3` | — | `rho_ref_me` | — |
| `icon:d_exner_dz_ref_ic` | `m-1` | — | `d_exner_dz_ref_ic` | — |
| `icon:d2dexdz2_fac1_mc` | `m-1` | — | `d2dexdz2_fac1_mc` | — |
| `icon:d2dexdz2_fac2_mc` | `m-2` | — | `d2dexdz2_fac2_mc` | — |
| `icon:ddxn_z_full` | `1` | — | `ddxn_z_full` | — |
| `icon:ddxt_z_full` | `1` | — | `ddxt_z_full` | — |
| `icon:vwind_impl_wgt` | `1` | — | `vwind_impl_wgt` | — |
| `icon:vwind_expl_wgt` | `1` | — | `vwind_expl_wgt` | — |
| `icon:exner_exfac` | `1` | — | `exner_exfac` | — |
| `icon:wgtfac_c` | `1` | — | `wgtfac_c` | — |
| `icon:wgtfac_e` | `1` | — | `wgtfac_e` | — |
| `icon:wgtfacq_c` | `1` | — | `wgtfacq_c` | — |
| `icon:wgtfacq_e` | `1` | — | `wgtfacq_e` | — |
| `icon:pg_exdist` | `m` | — | `pg_exdist` | — |
| `icon:mask_prog_halo_c` | `1` | — | `mask_prog_halo_c` | — |
| `icon:hmask_dd3d` | `1` | — | `hmask_dd3d` | — |
| `icon:zdiff_gradp` | `m` | — | `zdiff_gradp` | — |
| `icon:vertoffset_gradp` | `1` | — | `vertoffset_gradp` | — |
| `icon:nflat_gradp` | `1` | — | `nflat_gradp` | — |
| `icon:coeff_gradekin` | `m-1` | — | `coeff_gradekin` | — |
| `icon:zd_diffcoef` | `1` | — | `zd_diffcoef` | — |
| `icon:zd_intcoef` | `1` | — | `zd_intcoef` | — |
| `icon:zd_vertoffset` | `1` | — | `zd_vertoffset` | — |
| `icon:geopot` | `m2 s-2` | — | `geopot` | — |
| `icon:c_lin_e` | `1` | — | `c_lin_e` | — |
| `icon:e_bln_c_s` | `1` | — | `e_bln_c_s` | — |
| `icon:geofac_div` | `m-1` | — | `geofac_div` | — |
| `icon:geofac_rot` | `m-1` | — | `geofac_rot` | — |
| `icon:geofac_n2s` | `m-2` | — | `geofac_n2s` | — |
| `icon:geofac_grdiv` | `m-2` | — | `geofac_grdiv` | — |
| `icon:geofac_grg_x` | `m-1` | — | `geofac_grg_x` | — |
| `icon:geofac_grg_y` | `m-1` | — | `geofac_grg_y` | — |
| `icon:nudgecoeff_e` | `1` | — | `nudgecoeff_e` | — |
| `icon:rbf_vec_coeff_v1` | `1` | — | `rbf_vec_coeff_v1` | — |
| `icon:rbf_vec_coeff_v2` | `1` | — | `rbf_vec_coeff_v2` | — |
| `icon:rbf_vec_coeff_e` | `1` | — | `rbf_vec_coeff_e` | — |
| `icon:c_intp` | `1` | — | `c_intp` | — |
| `icon:pos_on_tplane_e_x` | `m` | — | `pos_on_tplane_e_x` | — |
| `icon:pos_on_tplane_e_y` | `m` | — | `pos_on_tplane_e_y` | — |
| `icon:e_flx_avg` | `1` | — | `e_flx_avg` | — |
