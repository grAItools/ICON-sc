"""S11 acceptance 3 (marker ``data``): metrics/interpolation parity.

Every static field produced by ``icon_sc.icon.grid.metrics``/``.interpolation`` matches
the corresponding icon4py serialized savepoint at icon4py's own test tolerances
(tolerance contracts, SPEC S11). Provenance (REFERENCES.lock ids
``icon4py-grid-metrics-tests`` + ``icon4py-refatm-metric-field-tests``): most
per-field rtol/atol come from icon4py v0.2.0 test_metrics_factory.py /
test_interpolation_factory.py / test_rbf_interpolation.py; six fields have no factory
test upstream (rho_ref_mc, theta_ref_ic, d_exner_dz_ref_ic, theta_ref_me, rho_ref_me,
wgtfac_e) — their tolerances come from icon4py's test_reference_atmosphere.py /
test_metric_fields.py, which use the strict dallclose default rtol=1e-12, atol=0
(rho_ref_me: rtol=1e-10).

Experiment: EXCLAIM_APE (``exclaim_ape_R02B04``) — icon4py's own factory-parity
experiment on the R02B04 global grid, i.e. the same horizontal grid as the JW/driver
datatest that S12/S13 target. The field list enumerated here (METRICS_FIELDS /
INTERPOLATION_FIELDS) is exactly the S12/S13 consumption set (dycore
MetricStateNonHydro + InterpolationState, diffusion states).

The factories run on gtfn_cpu: icon4py marks several fields (wgtfac_c, pg_exdist,
zdiff_gradp, zd_*) ``embedded_remap_error`` — the embedded backend cannot produce
them. First run compiles the gt4py programs (persistent cache under
``~/.cache/icon-sc/gt4py``); the serialized archive is ~4.0 GB compressed / 8.7 GB
extracted (download cached under ``~/.cache/icon-sc/icon4py-testdata``).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from icon_sc.core.testing import assert_allclose
from icon_sc.icon.testing import DATATEST_AVAILABLE, download_grid_file

if DATATEST_AVAILABLE:
    from icon4py.model.testing import definitions as icon4py_definitions

    # Re-exported icon4py fixtures (fixture *names* are what pytest resolves; the
    # icon4py `backend` fixture intentionally shadows ICON-sc's string-valued one in
    # this module — it only steers savepoint ingestion, not the factories).
    from icon_sc.icon.testing import (  # noqa: F401
        backend,
        data_provider,
        download_ser_data,
        experiment,
        grid_savepoint,
        interpolation_savepoint,
        metrics_savepoint,
        process_props,
        topography_savepoint,
    )

    @pytest.fixture(params=[icon4py_definitions.Experiments.EXCLAIM_APE], ids=lambda e: e.name)
    def experiment_description(request: Any) -> Any:
        """Override the bridge default (GAUSS3D): parity runs on EXCLAIM_APE."""
        return request.param


pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

#: metrics parity cases: registry name -> (savepoint accessor, kwargs).
#: Tolerances are icon4py's own (contracts); ``start`` names the horizontal domain
#: whose boundary zone the Fortran reference leaves uninitialized (upstream slices
#: identically); ``exact`` compares integer/bool fields bitwise.
METRICS_CASES: dict[str, dict[str, Any]] = {
    "altitude": dict(accessor="z_mc", rtol=1e-10),
    "altitude_on_interface_levels": dict(accessor="z_ifc", rtol=1e-9),
    "icon:ddqz_z_full": dict(accessor="ddqz_z_full", rtol=1e-7),
    "icon:inv_ddqz_z_full": dict(accessor="inv_ddqz_z_full", atol=1e-10),
    "icon:ddqz_z_half": dict(accessor="ddqz_z_half", rtol=1e-9),
    "icon:ddqz_z_full_e": dict(accessor="ddqz_z_full_e", rtol=1e-8),
    "icon:scalfac_dd3d": dict(accessor="scalfac_dd3d"),
    "icon:rayleigh_w": dict(accessor="rayleigh_w"),
    "icon:coeff1_dwdz": dict(accessor="coeff1_dwdz", atol=1e-11),
    "icon:coeff2_dwdz": dict(accessor="coeff2_dwdz", atol=1e-11),
    "icon:exner_ref_mc": dict(accessor="exner_ref_mc", atol=1e-10),
    "icon:theta_ref_mc": dict(accessor="theta_ref_mc", atol=1e-9),
    # The five reference-state fields below + wgtfac_e are not covered by upstream
    # *factory* tests; their upstream verification lives in
    # test_reference_atmosphere.py / test_metric_fields.py at the strict dallclose
    # default (rtol=1e-12, atol=0; rho_ref_me rtol=1e-10) — used verbatim here.
    "icon:rho_ref_mc": dict(accessor="rho_ref_mc"),
    "icon:theta_ref_ic": dict(accessor="theta_ref_ic"),
    "icon:d_exner_dz_ref_ic": dict(accessor="d_exner_dz_ref_ic"),
    "icon:theta_ref_me": dict(accessor="theta_ref_me"),
    "icon:rho_ref_me": dict(accessor="rho_ref_me", rtol=1e-10),
    "icon:d2dexdz2_fac1_mc": dict(accessor="d2dexdz2_fac1_mc", atol=1e-12),
    "icon:d2dexdz2_fac2_mc": dict(accessor="d2dexdz2_fac2_mc", atol=1e-12),
    "icon:ddxn_z_full": dict(accessor="ddxn_z_full", atol=1e-8),
    "icon:ddxt_z_full": dict(accessor="ddxt_z_full", rtol=1e-5, atol=1e-8),
    "icon:vwind_impl_wgt": dict(accessor="vwind_impl_wgt", rtol=1e-9),
    "icon:vwind_expl_wgt": dict(accessor="vwind_expl_wgt", rtol=1e-8),
    "icon:exner_exfac": dict(accessor="exner_exfac", atol=1e-8),
    "icon:wgtfac_c": dict(accessor="wgtfac_c", rtol=1e-9),
    "icon:wgtfac_e": dict(accessor="wgtfac_e"),  # test_metric_fields.py: strict default
    "icon:wgtfacq_c": dict(accessor="wgtfacq_c"),
    "icon:wgtfacq_e": dict(accessor="wgtfacq_e"),
    "icon:pg_exdist": dict(accessor="pg_exdist_dsl", atol=1e-5),
    "icon:mask_prog_halo_c": dict(accessor="mask_prog_halo_c", exact=True),
    "icon:hmask_dd3d": dict(accessor="hmask_dd3d"),
    "icon:zdiff_gradp": dict(accessor="zdiff_gradp", atol=1e-10, rtol=1e-9, start="edge_lb2"),
    "icon:vertoffset_gradp": dict(accessor="vertoffset_gradp", exact=True, start="edge_lb2"),
    "icon:coeff_gradekin": dict(accessor="coeff_gradekin", rtol=1e-8),
    "icon:zd_diffcoef": dict(accessor="zd_diffcoef", atol=1e-10),
    "icon:zd_intcoef": dict(accessor="zd_intcoef", atol=1e-8),
    "icon:zd_vertoffset": dict(accessor="zd_vertoffset", exact=True),
}

#: RBF coefficient tolerances for EXCLAIM_APE (icon4py RBF_TOLERANCES table; the
#: cell coefficients are not consumed by S12/S13 and are not produced here).
_RBF_ATOL_EDGE, _RBF_ATOL_VERTEX = 8e-14, 3e-10

INTERPOLATION_CASES: dict[str, dict[str, Any]] = {
    "icon:c_lin_e": dict(accessor="c_lin_e"),
    "icon:e_bln_c_s": dict(accessor="e_bln_c_s", rtol=1e-11),
    "icon:geofac_div": dict(accessor="geofac_div"),
    "icon:geofac_rot": dict(accessor="geofac_rot", start="vertex_lb2"),
    "icon:geofac_n2s": dict(accessor="geofac_n2s"),
    "icon:geofac_grdiv": dict(accessor="geofac_grdiv"),
    "icon:geofac_grg_x": dict(accessor="geofac_grg", index=0, rtol=1e-11, atol=1.1e-16),
    "icon:geofac_grg_y": dict(accessor="geofac_grg", index=1, rtol=1e-11, atol=1e-16),
    "icon:nudgecoeff_e": dict(accessor="nudgecoeff_e"),
    "icon:rbf_vec_coeff_v1": dict(
        accessor="rbf_vec_coeff_v1", atol=_RBF_ATOL_VERTEX, start="vertex_lb2"
    ),
    "icon:rbf_vec_coeff_v2": dict(
        accessor="rbf_vec_coeff_v2", atol=_RBF_ATOL_VERTEX, start="vertex_lb2"
    ),
    "icon:rbf_vec_coeff_e": dict(accessor="rbf_vec_coeff_e", atol=_RBF_ATOL_EDGE, start="edge_lb2"),
    "icon:c_intp": dict(accessor="c_intp"),
    "icon:pos_on_tplane_e_x": dict(accessor="pos_on_tplane_e_x", atol=1e-8, rtol=1e-9),
    "icon:pos_on_tplane_e_y": dict(accessor="pos_on_tplane_e_y", atol=1e-8, rtol=1e-9),
    "icon:e_flx_avg": dict(accessor="e_flx_avg", atol=1e-12),
}

#: icon4py's dallclose default (numpy.allclose with rtol=1e-12) for unmarked cases.
_DEFAULT_RTOL = 1e-12

_static_cache: dict[str, dict[str, Any]] = {}


def _sleve_config(vertical_config: Any) -> Any:
    from icon_sc.icon.grid import SLEVEConfig

    return SLEVEConfig(
        num_levels=vertical_config.num_levels,
        lowest_layer_thickness=vertical_config.lowest_layer_thickness,
        maximal_layer_thickness=vertical_config.maximal_layer_thickness,
        top_height_limit_for_maximal_layer_thickness=(
            vertical_config.top_height_limit_for_maximal_layer_thickness
        ),
        model_top_height=vertical_config.model_top_height,
        flat_height=vertical_config.flat_height,
        stretch_factor=vertical_config.stretch_factor,
        rayleigh_damping_height=vertical_config.rayleigh_damping_height,
        htop_moist_proc=vertical_config.htop_moist_proc,
        decay_scale_1=vertical_config.SLEVE_decay_scale_1,
        decay_scale_2=vertical_config.SLEVE_decay_scale_2,
        decay_exponent=vertical_config.SLEVE_decay_exponent,
    )


def _get_static(experiment: Any, grid_savepoint: Any, topography_savepoint: Any) -> dict[str, Any]:
    """Build grid + vgrid + both static-field mappings once per experiment.

    Mirrors icon4py's own parity setup: grid from the grid *file*, vct_a/vct_b from
    the grid savepoint, configs from the archive's namelist json
    (``experiment.config``), topography from the topography savepoint.
    """
    if experiment.name in _static_cache:
        return _static_cache[experiment.name]

    from icon_sc.core.context import ComputeContext
    from icon_sc.core.ingress.gt4py import make_backend
    from icon_sc.icon.grid import VerticalGrid, from_file, interpolation, metrics

    vertical_config = experiment.config.vertical_grid
    grid_file = download_grid_file(experiment.grid)
    ctx = ComputeContext(backend=make_backend("gtfn_cpu"))
    grid = from_file(grid_file, ctx, num_levels=vertical_config.num_levels)
    vgrid = VerticalGrid(
        np.asarray(grid_savepoint.vct_a().asnumpy(), dtype=np.float64),
        np.asarray(grid_savepoint.vct_b().asnumpy(), dtype=np.float64),
        vertical_config.num_levels,
        config=_sleve_config(vertical_config),
    )
    entry = {
        "grid": grid,
        "nflat_gradp_ref": int(grid_savepoint.nflat_gradp()),
        "metrics": metrics(
            grid,
            vgrid,
            topography=np.asarray(topography_savepoint.topo_c().asnumpy(), dtype=np.float64),
            config=experiment.config.metrics,
            interpolation_config=experiment.config.interpolation,
        ),
        "interpolation": interpolation(grid, config=experiment.config.interpolation),
    }
    _static_cache[experiment.name] = entry
    return entry


def _start_index(grid: Any, which: str | None) -> int:
    if which is None:
        return 0
    from icon4py.model.common import dimension as dims
    from icon4py.model.common.grid import horizontal as h_grid

    dim = {"edge_lb2": dims.EdgeDim, "vertex_lb2": dims.VertexDim}[which]
    domain = h_grid.domain(dim)(h_grid.Zone.LATERAL_BOUNDARY_LEVEL_2)
    return int(grid.icon4py_grid.start_index(domain))


def _check(name: str, produced: Any, reference: Any, grid: Any, case: dict[str, Any]) -> None:
    actual = np.asarray(produced.data)
    desired = np.asarray(reference.asnumpy() if hasattr(reference, "asnumpy") else reference)
    if desired.size == 1 and actual.size > 1:
        # ICON serializes a (1,1) dummy when a field was never allocated (the zd_*
        # terrain-diffusion fields on the flat aquaplanet). icon4py's dallclose
        # broadcasts silently; ICON-sc broadcasts *explicitly* — the parity statement
        # becomes "the factory reproduces the constant the dummy stands for" (zeros).
        desired = np.broadcast_to(desired.reshape(()), actual.shape)
    start = _start_index(grid, case.get("start"))
    actual, desired = actual[start:], desired[start:]
    assert actual.shape == desired.shape, f"{name}: {actual.shape} != {desired.shape}"
    if case.get("exact"):
        np.testing.assert_array_equal(actual, desired, err_msg=name)
    else:
        # icon4py test_utils.dallclose defaults: rtol=1e-12, atol=0, equal_nan=False
        # — per-field overrides keep the *other* defaults (no tolerance creep), and
        # co-located NaNs fail exactly like upstream.
        assert_allclose(
            actual,
            desired,
            rtol=case.get("rtol", _DEFAULT_RTOL),
            atol=case.get("atol", 0.0),
            names=name,
            equal_nan=False,
        )


@pytest.mark.parametrize("name", sorted(METRICS_CASES), ids=str)
def test_metrics_parity(
    name: str,
    experiment: Any,
    grid_savepoint: Any,
    metrics_savepoint: Any,
    topography_savepoint: Any,
) -> None:
    static = _get_static(experiment, grid_savepoint, topography_savepoint)
    case = METRICS_CASES[name]
    reference = getattr(metrics_savepoint, case["accessor"])()
    _check(name, static["metrics"][name], reference, static["grid"], case)


def test_metrics_nflat_gradp(
    experiment: Any, grid_savepoint: Any, topography_savepoint: Any
) -> None:
    static = _get_static(experiment, grid_savepoint, topography_savepoint)
    produced = static["metrics"]["icon:nflat_gradp"]
    assert produced.shape == ()
    assert int(produced.data) == static["nflat_gradp_ref"]


@pytest.mark.parametrize("name", sorted(INTERPOLATION_CASES), ids=str)
def test_interpolation_parity(
    name: str,
    experiment: Any,
    grid_savepoint: Any,
    interpolation_savepoint: Any,
    topography_savepoint: Any,
) -> None:
    static = _get_static(experiment, grid_savepoint, topography_savepoint)
    case = INTERPOLATION_CASES[name]
    reference = getattr(interpolation_savepoint, case["accessor"])()
    if case.get("index") is not None:
        reference = reference[case["index"]]
    _check(name, static["interpolation"][name], reference, static["grid"], case)


def test_field_lists_cover_the_s12_s13_consumption_set(
    experiment: Any, grid_savepoint: Any, topography_savepoint: Any
) -> None:
    """The parity tables cover every field metrics()/interpolation() produce, and the
    produced mappings are read-only DataArrays with registry metadata."""
    from icon_sc.icon.grid import INTERPOLATION_FIELDS, METRICS_FIELDS

    assert set(METRICS_CASES) | {"icon:nflat_gradp"} == set(METRICS_FIELDS)
    assert set(INTERPOLATION_CASES) == set(INTERPOLATION_FIELDS)

    static = _get_static(experiment, grid_savepoint, topography_savepoint)
    for mapping in (static["metrics"], static["interpolation"]):
        for name, field in mapping.items():
            assert field.name == name
            assert field.attrs["grid_uuid"] == static["grid"].uuid
            assert "units" in field.attrs and "location" in field.attrs
            assert not field.data.flags.writeable
        with pytest.raises(TypeError):
            mapping["nope"] = None  # type: ignore[index]
