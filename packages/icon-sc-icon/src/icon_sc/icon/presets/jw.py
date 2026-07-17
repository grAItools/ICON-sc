"""The Jablonowski-Williamson dry-model preset: dycore + diffusion (SPEC S13).

``build_jw(JWConfig(...))`` assembles the composed dry model of architecture §5.1
minus physics/transport — the S12 :class:`~icon_sc.icon.components.NonhydroSolver`
followed by the S13 :class:`~icon_sc.icon.components.HorizontalDiffusion`, exactly the
per-step order of the icon4py driver (``_do_dyn_substepping`` then ``diffusion.run``
then swap; REFERENCES.lock ``icon4py-driver-jw``) — on the icon4py JW datatest
experiment (``exclaim_nh35_tri_jws``, global R02B04, 35 levels).

Data/provenance: everything comes from the pinned icon4py datatest archive —
the serialized grid savepoint (ICON-pre-padded connectivity tables; the savepoint
grid every S12 parity test hosts on), the metrics/interpolation savepoints (static
state, zero conversion), and the archive's own ICON namelist for *all* config values
(the PLAN "config congruence" pitfall: the same provenance feeds the reference
trajectory generator in ``validation/L4_idealized/make_reference.py``, and the L4
test asserts config equality before comparing trajectories). Requires the
``icon-sc-icon[datatest]`` extra; the archive (~14 GB unpacked) downloads once into
the shared cache.

The preset also carries the *checkpoint diagnostics* both the reference run and the
ICON-sc run must compute identically (numpy, deterministic): surface pressure
(icon4py ``diagnose_surface_pressure`` formula — REFERENCES.lock
``icon4py-diagnostics-stencils``), vn norms, and the 850 hPa relative-vorticity
proxy (vertex curl via ``geofac_rot``, the level fixed at build time from the
initial pressure profile).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from datetime import timedelta
from types import MappingProxyType
from typing import Any

import numpy as np

from icon_sc.core import ComputeContext, SequentialUpdateSplitting
from icon_sc.core.ingress.gt4py import make_backend
from icon_sc.core.state import make_dataarray
from icon_sc.icon.components import (
    DiffusionConfig,
    HorizontalDiffusion,
    NonhydroConfig,
    NonhydroSolver,
)
from icon_sc.icon.ingest.idealized import JablonowskiWilliamsonConfig, jablonowski_williamson

__all__ = ["JWConfig", "JWModel", "build_jw"]


@dataclasses.dataclass(frozen=True)
class JWConfig:
    """JW preset knobs. Everything not listed here comes from the archive namelist."""

    #: ICON ``nh_test_nml:jw_up`` [m/s]: 1.0 = the classic baroclinic wave (JW06 §4);
    #: 0.0 = the zonally symmetric steady state (the archive's own configuration).
    perturbation_amplitude: float = 1.0
    backend: str = "gtfn_cpu"


@dataclasses.dataclass(frozen=True)
class JWModel:
    """The composed dry model + initial state + checkpoint diagnostics.

    S14 additive extension (declared in the S14 STATUS): ``composition`` is the
    dycore→diffusion sequence as one bindable ``SequentialUpdateSplitting`` —
    the tree ``ExecutionPlan.bind`` compiles and ``ctx.timeloop`` runs under
    either tier; ``step`` remains the equivalent T0 closure (the L4 runner's
    entry). ``state`` now carries the slow-tendency bus slots explicitly as
    zero fields: under ``tier="plan"`` the ``__call__`` zero-fill convenience
    is bypassed (S12 STATUS follow-up — decision: the plan compiler does *not*
    synthesize default slots; the bound state is explicit), and under T0 the
    dycore sees the same zeros it would have synthesized, bitwise.
    """

    dycore: NonhydroSolver
    diffusion: HorizontalDiffusion
    composition: SequentialUpdateSplitting
    state: dict[str, Any]
    dtime: timedelta
    #: archive-derived run provenance (asserted against the reference's in L4).
    provenance: Mapping[str, Any]
    #: model level used for the 850 hPa vorticity proxy (fixed at build time).
    level_850: int
    #: ``step(state, dt)`` -> new state (dycore then diffusion, driver order).
    step: Callable[[Mapping[str, Any], timedelta], dict[str, Any]]
    #: checkpoint diagnostics on a state dict (numpy; identical for both runs).
    checkpoint: Callable[[Mapping[str, Any]], dict[str, np.ndarray]]


def _host(value: Any) -> np.ndarray:
    array = value.asnumpy() if hasattr(value, "asnumpy") else np.asarray(value)
    return np.asarray(array, dtype=np.float64)


def build_jw(cfg: JWConfig | None = None) -> JWModel:
    """Assemble the JW dry model on the pinned icon4py JW datatest experiment."""
    from icon4py.model.common.decomposition import definitions as decomposition
    from icon4py.model.common.grid import vertical as v_grid
    from icon4py.model.testing import datatest_utils as dtu
    from icon4py.model.testing import definitions as i4_definitions

    cfg = cfg if cfg is not None else JWConfig()
    description = i4_definitions.Experiments.JW
    props = decomposition.get_process_properties(decomposition.get_runtype(with_mpi=False))
    dtu.download_experiment(description, props)  # no-op when cached
    experiment_config = dtu.create_experiment_configuration(description, props)

    ctx = ComputeContext(backend=make_backend(cfg.backend))
    gt4py_backend = ctx.backend.gt4py_backend  # type: ignore[union-attr]
    data_path = dtu.get_datapath_for_experiment(description, props)
    provider = dtu.create_icon_serial_data_provider(data_path, props.rank, gt4py_backend)
    grid_savepoint = provider.from_savepoint_grid(description.name, description.grid.params)
    metrics_savepoint = provider.from_metrics_savepoint()
    interpolation_savepoint = provider.from_interpolation_savepoint()

    # the savepoint-hosted grid (keep_skip_values=False, upstream fixture setting):
    # serialized tables arrive ICON-pre-padded — see the S13 STATUS pentagon notes.
    icon_grid = grid_savepoint.construct_icon_grid(keep_skip_values=False, backend=gt4py_backend)
    edge_geometry = grid_savepoint.construct_edge_geometry()
    cell_geometry = grid_savepoint.construct_cell_geometry()
    vertical_params = v_grid.VerticalGrid(
        config=experiment_config.vertical_grid,
        vct_a=grid_savepoint.vct_a(),
        vct_b=grid_savepoint.vct_b(),
    )

    dtime = experiment_config.driver.dtime
    n_substeps = int(experiment_config.diffusion.ndyn_substeps)
    dycore_config = NonhydroConfig.from_icon4py(
        experiment_config.nonhydrostatic,
        ndyn_substeps=n_substeps,
        # the JW initializer returns second_order_divdamp_factor = 0.0 (donor
        # model_initialization_jabw return value; the driver forwards it).
        second_order_divdamp_factor=0.0,
        prepare_advection=False,  # ltransport=False in the archive namelist
    )
    diffusion_config = DiffusionConfig.from_icon4py(experiment_config.diffusion)

    grg = interpolation_savepoint.geofac_grg()
    dycore_static: dict[str, Any] = {
        "icon:mask_prog_halo_c": metrics_savepoint.mask_prog_halo_c(),
        "icon:rayleigh_w": metrics_savepoint.rayleigh_w(),
        "icon:exner_exfac": metrics_savepoint.exner_exfac(),
        "icon:exner_ref_mc": metrics_savepoint.exner_ref_mc(),
        "icon:wgtfac_c": metrics_savepoint.wgtfac_c(),
        "icon:wgtfacq_c": metrics_savepoint.wgtfacq_c(),
        "icon:inv_ddqz_z_full": metrics_savepoint.inv_ddqz_z_full(),
        "icon:rho_ref_mc": metrics_savepoint.rho_ref_mc(),
        "icon:theta_ref_mc": metrics_savepoint.theta_ref_mc(),
        "icon:vwind_expl_wgt": metrics_savepoint.vwind_expl_wgt(),
        "icon:d_exner_dz_ref_ic": metrics_savepoint.d_exner_dz_ref_ic(),
        "icon:ddqz_z_half": metrics_savepoint.ddqz_z_half(),
        "icon:theta_ref_ic": metrics_savepoint.theta_ref_ic(),
        "icon:d2dexdz2_fac1_mc": metrics_savepoint.d2dexdz2_fac1_mc(),
        "icon:d2dexdz2_fac2_mc": metrics_savepoint.d2dexdz2_fac2_mc(),
        "icon:rho_ref_me": metrics_savepoint.rho_ref_me(),
        "icon:theta_ref_me": metrics_savepoint.theta_ref_me(),
        "icon:ddxn_z_full": metrics_savepoint.ddxn_z_full(),
        "icon:zdiff_gradp": metrics_savepoint.zdiff_gradp(),
        "icon:vertoffset_gradp": metrics_savepoint.vertoffset_gradp(),
        "icon:nflat_gradp": int(grid_savepoint.nflat_gradp()),
        "icon:pg_exdist": metrics_savepoint.pg_exdist_dsl(),
        "icon:ddqz_z_full_e": metrics_savepoint.ddqz_z_full_e(),
        "icon:ddxt_z_full": metrics_savepoint.ddxt_z_full(),
        "icon:wgtfac_e": metrics_savepoint.wgtfac_e(),
        "icon:wgtfacq_e": metrics_savepoint.wgtfacq_e(),
        "icon:vwind_impl_wgt": metrics_savepoint.vwind_impl_wgt(),
        "icon:hmask_dd3d": metrics_savepoint.hmask_dd3d(),
        "icon:scalfac_dd3d": metrics_savepoint.scalfac_dd3d(),
        "icon:coeff1_dwdz": metrics_savepoint.coeff1_dwdz(),
        "icon:coeff2_dwdz": metrics_savepoint.coeff2_dwdz(),
        "icon:coeff_gradekin": metrics_savepoint.coeff_gradekin(),
        "icon:c_lin_e": interpolation_savepoint.c_lin_e(),
        "icon:c_intp": interpolation_savepoint.c_intp(),
        "icon:e_flx_avg": interpolation_savepoint.e_flx_avg(),
        "icon:geofac_grdiv": interpolation_savepoint.geofac_grdiv(),
        "icon:geofac_rot": interpolation_savepoint.geofac_rot(),
        "icon:pos_on_tplane_e_x": interpolation_savepoint.pos_on_tplane_e_x(),
        "icon:pos_on_tplane_e_y": interpolation_savepoint.pos_on_tplane_e_y(),
        "icon:rbf_vec_coeff_e": interpolation_savepoint.rbf_vec_coeff_e(),
        "icon:e_bln_c_s": interpolation_savepoint.e_bln_c_s(),
        "icon:rbf_vec_coeff_v1": interpolation_savepoint.rbf_vec_coeff_v1(),
        "icon:rbf_vec_coeff_v2": interpolation_savepoint.rbf_vec_coeff_v2(),
        "icon:geofac_div": interpolation_savepoint.geofac_div(),
        "icon:geofac_n2s": interpolation_savepoint.geofac_n2s(),
        "icon:geofac_grg_x": grg[0],
        "icon:geofac_grg_y": grg[1],
        "icon:nudgecoeff_e": interpolation_savepoint.nudgecoeff_e(),
    }
    diffusion_static = {
        name: dycore_static[name]
        for name in (
            "icon:theta_ref_mc",
            "icon:wgtfac_c",
            "icon:e_bln_c_s",
            "icon:rbf_vec_coeff_v1",
            "icon:rbf_vec_coeff_v2",
            "icon:geofac_div",
            "icon:geofac_n2s",
            "icon:geofac_grg_x",
            "icon:geofac_grg_y",
            "icon:nudgecoeff_e",
        )
    }
    diffusion_static["icon:zd_intcoef"] = metrics_savepoint.zd_intcoef()
    diffusion_static["icon:zd_vertoffset"] = metrics_savepoint.zd_vertoffset()
    diffusion_static["icon:zd_diffcoef"] = metrics_savepoint.zd_diffcoef()

    dycore = NonhydroSolver(
        icon_grid,
        vertical_params,
        dycore_static,
        dycore_config,
        ctx,
        edge_geometry=edge_geometry,
        cell_geometry=cell_geometry,
        owner_mask=grid_savepoint.c_owner_mask(),
    )
    diffusion = HorizontalDiffusion(
        icon_grid,
        vertical_params,
        diffusion_static,
        diffusion_config,
        ctx,
        edge_geometry=edge_geometry,
        cell_geometry=cell_geometry,
    )

    composition = SequentialUpdateSplitting([dycore, diffusion], name="jw_dry")

    state = jablonowski_williamson(
        icon_grid,
        vertical_params,
        JablonowskiWilliamsonConfig(perturbation_amplitude=cfg.perturbation_amplitude),
        static={
            "icon:wgtfac_c": metrics_savepoint.wgtfac_c(),
            "icon:ddqz_z_half": metrics_savepoint.ddqz_z_half(),
            "icon:theta_ref_mc": metrics_savepoint.theta_ref_mc(),
            "icon:theta_ref_ic": metrics_savepoint.theta_ref_ic(),
            "icon:exner_ref_mc": metrics_savepoint.exner_ref_mc(),
            "icon:d_exner_dz_ref_ic": metrics_savepoint.d_exner_dz_ref_ic(),
            "icon:geopot": metrics_savepoint.geopot(),
            "icon:c_lin_e": interpolation_savepoint.c_lin_e(),
        },
        edge_geometry=edge_geometry,
        cell_geometry=cell_geometry,
    )

    # Explicit zero slow-tendency bus slots (S14): tier="plan" bypasses the
    # __call__ zero-fill convenience, so the bound state carries the slots; under
    # T0 the dycore ingests the same zeros it would have synthesized (bitwise).
    nlev = int(experiment_config.vertical_grid.num_levels)
    for slot, dims, shape in (
        ("icon:ddt_vn_phy", ("edge", "height"), (int(icon_grid.num_edges), nlev)),
        ("icon:ddt_exner_phy", ("cell", "height"), (int(icon_grid.num_cells), nlev)),
    ):
        buffer = ctx.require_allocator.empty(shape, np.dtype(np.float64))
        buffer[...] = 0.0
        spec = dict(NonhydroSolver.input_properties[slot])
        state[slot] = make_dataarray(
            buffer, name=slot, dims=dims, units=str(spec["units"]), location=dims[0]
        )

    # -- checkpoint diagnostics (numpy; shared verbatim by reference + ICON-sc runs) ----
    ddqz_z_full = 1.0 / _host(metrics_savepoint.inv_ddqz_z_full())
    geofac_rot = _host(interpolation_savepoint.geofac_rot())
    v2e = np.asarray(icon_grid.get_connectivity("V2E").asnumpy())
    # level whose initial mean pressure is closest to 850 hPa (fixed per build):
    mean_pressure = np.asarray(state["air_pressure"].data).mean(axis=0)
    level_850 = int(np.argmin(np.abs(mean_pressure - 85000.0)))

    def checkpoint(current: Mapping[str, Any]) -> dict[str, np.ndarray]:
        exner = np.asarray(current["icon:exner_function"].data, dtype=np.float64)
        theta_v = np.asarray(current["icon:virtual_potential_temperature"].data, dtype=np.float64)
        vn = np.asarray(current["icon:normal_wind"].data, dtype=np.float64)
        return {
            "surface_pressure": surface_pressure(exner, theta_v, ddqz_z_full),
            "vn_l2": np.asarray(np.sqrt(np.mean(vn**2))),
            "vn_linf": np.asarray(np.max(np.abs(vn))),
            "vorticity_850": vertex_vorticity(vn[:, level_850], geofac_rot, v2e),
        }

    def step(current: Mapping[str, Any], dt: timedelta) -> dict[str, Any]:
        """One composed Δt: dynamics substepping, then diffusion (driver order)."""
        merged = dict(current)
        _, out = dycore(merged, dt)
        merged.update(out)
        _, out = diffusion(merged, dt)
        merged.update(out)
        return merged

    provenance = MappingProxyType(
        {
            "experiment": description.name,
            "grid": description.grid.name,
            "grid_uuid": str(icon_grid.id),
            "num_levels": int(experiment_config.vertical_grid.num_levels),
            "dtime_seconds": dtime.total_seconds(),
            "ndyn_substeps": n_substeps,
            "second_order_divdamp_factor": 0.0,
            "perturbation_amplitude": cfg.perturbation_amplitude,
            "fourth_order_divdamp_factor": dycore_config.divdamp_fac,
            "divdamp_order": dycore_config.divdamp_order,
            "hdiff_efdt_ratio": diffusion_config.hdiff_efdt_ratio,
            "smagorinski_scaling_factor": diffusion_config.smagorinski_scaling_factor,
            "hdiff_temp": diffusion_config.hdiff_temp,
            "zdiffu_t": diffusion_config.zdiffu_t,
            "backend": cfg.backend,
        }
    )

    return JWModel(
        dycore=dycore,
        diffusion=diffusion,
        composition=composition,
        state=state,
        dtime=dtime,
        provenance=provenance,
        level_850=level_850,
        step=step,
        checkpoint=checkpoint,
    )


def surface_pressure(exner: np.ndarray, theta_v: np.ndarray, ddqz_z_full: np.ndarray) -> np.ndarray:
    """icon4py ``diagnose_surface_pressure`` in numpy (dry: tempv = θv·Π).

    ``pres_sfc = p0ref · exp(cpd/rd · ln Π[nlev-3] + g/rd · (Δz/Tv)[nlev-1] +
    (Δz/Tv)[nlev-2] + ½(Δz/Tv)[nlev-3])`` — REFERENCES.lock
    ``icon4py-diagnostics-stencils`` (matches ICON ``mo_nh_diagnose_pres_temp``).
    """
    from icon4py.model.common import constants as phy_const

    tempv = theta_v * exner
    return np.asarray(
        phy_const.P0REF
        * np.exp(
            phy_const.CPD_O_RD * np.log(exner[:, -3])
            + phy_const.GRAV_O_RD
            * (
                ddqz_z_full[:, -1] / tempv[:, -1]
                + ddqz_z_full[:, -2] / tempv[:, -2]
                + 0.5 * ddqz_z_full[:, -3] / tempv[:, -3]
            )
        )
    )


def vertex_vorticity(vn_level: np.ndarray, geofac_rot: np.ndarray, v2e: np.ndarray) -> np.ndarray:
    """Relative vorticity at vertices: ζ_v = Σ_e geofac_rot·vn (V2E curl stencil).

    ``-1`` entries (pentagon rows on file grids; absent on the pre-padded savepoint
    grid) are guarded — their ``geofac_rot`` slot is exactly 0 in ICON anyway.
    """
    valid = v2e >= 0
    gathered = vn_level[np.where(valid, v2e, 0)]
    return np.asarray(np.sum(np.where(valid, geofac_rot * gathered, 0.0), axis=1))
