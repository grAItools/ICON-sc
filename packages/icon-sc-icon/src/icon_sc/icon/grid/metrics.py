"""Metrics factory (architecture §3.2, S11).

``metrics(grid, vgrid) -> Mapping[str, DataArray]`` (frozen interface) computes the 3-d
metric terms and reference-state fields of ICON's ``t_nh_metrics`` — heights, functional
determinants, interpolation weight factors, reference atmosphere, pressure-gradient and
Rayleigh/divergence-damping coefficients — as read-only static-state DataArrays under
their registry names (:mod:`icon_sc.icon.names`).

Delegates to pinned icon4py's ``MetricsFieldsFactory`` (wrap-don't-rewrite, PLAN S11
item 1; REFERENCES.lock id ``icon4py-metrics-interp-factories``); the vertical grid
enters through the S06 :class:`~icon_sc.icon.grid.vertical.VerticalGrid` via its
``icon4py_grid`` accessor. The field list is exactly the S12/S13 consumption set:
icon4py ``dycore_states.MetricStateNonHydro`` plus the ``DiffusionMetricState`` extras
(``zd_*``) and the S06 height/thickness registry rows — REFERENCES.lock id
``icon4py-dycore-diffusion-static-state``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import numpy.typing as npt

from icon_sc.icon.grid.interpolation import (
    FieldSpec,
    build_interpolation_factory,
    select_specs,
    wrap_static_field,
)

if TYPE_CHECKING:
    import xarray as xr

    from icon_sc.icon.grid.grid import IconGrid
    from icon_sc.icon.grid.vertical import VerticalGrid

__all__ = ["METRICS_FIELDS", "metrics"]


def _specs(*rows: tuple[str, str, tuple[str, ...], str]) -> Mapping[str, FieldSpec]:
    return MappingProxyType({row[0]: FieldSpec(*row) for row in rows})


#: The metric fields S12 (solve_nonhydro) + S13 (diffusion) consume, keyed by registry
#: name. icon4py names from metrics_attributes.py (pinned v0.2.0). K-profile fields
#: (``height``/``height_interface`` only) carry ``location="scalar"`` — they live on
#: no horizontal mesh location; ``icon:nflat_gradp`` is a 0-d int level index.
METRICS_FIELDS: Final[Mapping[str, FieldSpec]] = _specs(
    ("altitude", "height", ("cell", "height"), "cell"),
    (
        "altitude_on_interface_levels",
        "vertical_coordinates_on_half_levels",
        ("cell", "height_interface"),
        "cell",
    ),
    (
        "icon:ddqz_z_full",
        "functional_determinant_of_metrics_on_full_levels",
        ("cell", "height"),
        "cell",
    ),
    (
        "icon:inv_ddqz_z_full",
        "inverse_of_functional_determinant_of_metrics_on_full_levels",
        ("cell", "height"),
        "cell",
    ),
    (
        "icon:ddqz_z_half",
        "functional_determinant_of_metrics_on_interface_levels",
        ("cell", "height_interface"),
        "cell",
    ),
    (
        "icon:ddqz_z_full_e",
        "functional_determinant_of_metrics_on_full_levels_on_edges",
        ("edge", "height"),
        "edge",
    ),
    ("icon:scalfac_dd3d", "scaling_factor_for_3d_divergence_damping", ("height",), "scalar"),
    ("icon:rayleigh_w", "rayleigh_w", ("height_interface",), "scalar"),
    ("icon:coeff1_dwdz", "coeff1_dwdz", ("cell", "height"), "cell"),
    ("icon:coeff2_dwdz", "coeff2_dwdz", ("cell", "height"), "cell"),
    ("icon:exner_ref_mc", "exner_ref_mc", ("cell", "height"), "cell"),
    ("icon:theta_ref_mc", "theta_ref_mc", ("cell", "height"), "cell"),
    ("icon:rho_ref_mc", "rho_ref_mc", ("cell", "height"), "cell"),
    ("icon:theta_ref_ic", "theta_ref_ic", ("cell", "height_interface"), "cell"),
    ("icon:d_exner_dz_ref_ic", "d_exner_dz_ref_ic", ("cell", "height_interface"), "cell"),
    ("icon:theta_ref_me", "theta_ref_me", ("edge", "height"), "edge"),
    ("icon:rho_ref_me", "rho_ref_me", ("edge", "height"), "edge"),
    ("icon:d2dexdz2_fac1_mc", "d2dexdz2_fac1_mc", ("cell", "height"), "cell"),
    ("icon:d2dexdz2_fac2_mc", "d2dexdz2_fac2_mc", ("cell", "height"), "cell"),
    ("icon:ddxn_z_full", "ddxn_z_full", ("edge", "height"), "edge"),
    # NOTE: the factory key is the attrs *constant* DDXT_Z_FULL ("ddxt_z_full"); its
    # metadata standard_name ("tangential_direction_of_slope") is not the lookup key.
    ("icon:ddxt_z_full", "ddxt_z_full", ("edge", "height"), "edge"),
    (
        "icon:vwind_impl_wgt",
        "implicitness_weight_for_exner_and_w_in_vertical_dycore_solver",
        ("cell",),
        "cell",
    ),
    (
        "icon:vwind_expl_wgt",
        "explicitness_weight_for_exner_and_w_in_vertical_dycore_solver",
        ("cell",),
        "cell",
    ),
    ("icon:exner_exfac", "exner_exfac", ("cell", "height"), "cell"),
    ("icon:wgtfac_c", "wgtfac_c", ("cell", "height_interface"), "cell"),
    ("icon:wgtfac_e", "wgtfac_e", ("edge", "height_interface"), "edge"),
    (
        "icon:wgtfacq_c",
        "weighting_factor_for_quadratic_interpolation_to_cell_surface",
        ("cell", "height"),
        "cell",
    ),
    (
        "icon:wgtfacq_e",
        "weighting_factor_for_quadratic_interpolation_to_edge_center",
        ("edge", "height"),
        "edge",
    ),
    ("icon:pg_exdist", "distance_for_pressure_gradient_extrapolation", ("edge", "height"), "edge"),
    ("icon:mask_prog_halo_c", "mask_prog_halo_c", ("cell",), "cell"),
    ("icon:hmask_dd3d", "horizontal_mask_for_3d_divdamp", ("edge",), "edge"),
    ("icon:zdiff_gradp", "zdiff_gradp", ("edge", "e2c", "height"), "edge"),
    ("icon:vertoffset_gradp", "vertoffset_gradp", ("edge", "e2c", "height"), "edge"),
    ("icon:nflat_gradp", "nflat_gradp", (), "scalar"),
    ("icon:coeff_gradekin", "coeff_gradekin", ("edge", "e2c"), "edge"),
    ("icon:zd_diffcoef", "zd_diffcoef", ("cell", "height"), "cell"),
    ("icon:zd_intcoef", "zd_intcoef", ("cell", "c2e2c", "height"), "cell"),
    ("icon:zd_vertoffset", "zd_vertoffset", ("cell", "c2e2c", "height"), "cell"),
)


def _topography_field(grid: IconGrid, topography: npt.ArrayLike | None) -> Any:
    """``topography`` as an icon4py cell field [m] (``None`` → flat terrain)."""
    import gt4py.next as gtx
    from icon4py.model.common import dimension as dims
    from icon4py.model.common import model_backends

    if topography is None:
        values = np.zeros(grid.n_cells, dtype=np.float64)
    else:
        values = np.asarray(topography, dtype=np.float64)
        if values.shape != (grid.n_cells,):
            raise ValueError(
                f"topography must be a cell field of shape ({grid.n_cells},), got {values.shape}."
            )
    allocator = model_backends.get_allocator(grid.gt4py_backend)
    return gtx.as_field((dims.CellDim,), values, allocator=allocator)


def metrics(
    grid: IconGrid,
    vgrid: VerticalGrid,
    *,
    topography: npt.ArrayLike | None = None,
    config: Any | None = None,
    interpolation_config: Any | None = None,
    fields: Iterable[str] | None = None,
) -> Mapping[str, xr.DataArray]:
    """Compute the static metric fields (frozen interface, SPEC S11).

    ``grid`` must have been built with ``num_levels == vgrid.nlev`` (the wrapped
    icon4py grid bundles the vertical size with the horizontal topology). Keyword
    extensions (declared, SPEC allows additive defaults): ``topography`` — cell field
    of surface heights [m], ``None`` → flat terrain; ``config`` /
    ``interpolation_config`` — icon4py ``MetricsConfig`` / ``InterpolationConfig``
    (``None`` → ICON namelist defaults); ``fields`` — registry-name subset of
    :data:`METRICS_FIELDS` (default: all).

    Returns a read-only mapping registry-name → read-only DataArray with ``grid_uuid``
    provenance; being static, the fields are exempt from halo tracking (§3.2).
    """
    from icon4py.model.common.decomposition import definitions as decomposition
    from icon4py.model.common.metrics import metrics_attributes, metrics_factory

    i4_grid = grid.icon4py_grid
    if int(i4_grid.num_levels) != vgrid.nlev:
        raise ValueError(
            f"grid was built for num_levels={int(i4_grid.num_levels)} but vgrid has "
            f"nlev={vgrid.nlev}; rebuild the grid with "
            f"from_file(path, ctx, num_levels={vgrid.nlev})."
        )
    if config is None:
        config = metrics_factory.MetricsConfig()

    factory = metrics_factory.MetricsFieldsFactory(
        grid=i4_grid,
        vertical_grid=vgrid.icon4py_grid,
        decomposition_info=grid.decomposition_info,
        geometry_source=grid.icon4py_geometry,
        topography=_topography_field(grid, topography),
        interpolation_source=build_interpolation_factory(grid, interpolation_config),
        backend=grid.gt4py_backend,
        metadata=dict(metrics_attributes.attrs),
        config=config,
        exchange=decomposition.single_node_exchange,
    )
    specs = select_specs(METRICS_FIELDS, fields)
    return MappingProxyType(
        {spec.name: wrap_static_field(factory.get(spec.i4_name), spec, grid.uuid) for spec in specs}
    )
