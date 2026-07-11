"""Interpolation-coefficient factory (architecture §3.2, S11).

``interpolation(grid) -> Mapping[str, DataArray]`` (frozen interface) computes the
horizontal interpolation coefficients the dycore and diffusion consume — RBF vector
coefficients, cell/edge/vertex weights, geometric factors, nudging coefficients — as
read-only static-state DataArrays under their registry names (:mod:`symcon.icon.names`).

Delegates to pinned icon4py's ``InterpolationFieldsFactory`` (wrap-don't-rewrite,
PLAN S11 item 1; REFERENCES.lock id ``icon4py-metrics-interp-factories``). The field
list is exactly the S12/S13 consumption set: icon4py ``dycore_states.InterpolationState``
plus ``diffusion_states.DiffusionInterpolationState`` (a subset) — REFERENCES.lock id
``icon4py-dycore-diffusion-static-state``.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

import numpy as np

from symcon.core.state import canonical_units, make_dataarray

if TYPE_CHECKING:
    import xarray as xr

    from symcon.icon.grid.grid import IconGrid

__all__ = ["INTERPOLATION_FIELDS", "interpolation"]


@dataclasses.dataclass(frozen=True)
class FieldSpec:
    """One static-state field: registry name, donor name, symcon dims/location."""

    name: str  #: registry name (icon: namespace, symcon.icon.names)
    i4_name: str  #: icon4py attribute standard name (the factory key)
    dims: tuple[str, ...]
    location: str


def _specs(*rows: tuple[str, str, tuple[str, ...], str]) -> Mapping[str, FieldSpec]:
    return MappingProxyType({row[0]: FieldSpec(*row) for row in rows})


#: The interpolation fields S12 (solve_nonhydro) + S13 (diffusion) consume, keyed by
#: registry name. icon4py names from interpolation_attributes.py (pinned v0.2.0).
INTERPOLATION_FIELDS: Final[Mapping[str, FieldSpec]] = _specs(
    ("icon:c_lin_e", "interpolation_coefficient_from_cell_to_edge", ("edge", "e2c"), "edge"),
    ("icon:e_bln_c_s", "bilinear_edge_cell_weight", ("cell", "c2e"), "cell"),
    ("icon:geofac_div", "geometrical_factor_for_divergence", ("cell", "c2e"), "cell"),
    ("icon:geofac_rot", "geometrical_factor_for_curl", ("vertex", "v2e"), "vertex"),
    ("icon:geofac_n2s", "geometrical_factor_for_nabla_2_scalar", ("cell", "c2e2co"), "cell"),
    (
        "icon:geofac_grdiv",
        "geometrical_factor_for_gradient_of_divergence",
        ("edge", "e2c2eo"),
        "edge",
    ),
    (
        "icon:geofac_grg_x",
        "geometrical_factor_for_green_gauss_gradient_x",
        ("cell", "c2e2co"),
        "cell",
    ),
    (
        "icon:geofac_grg_y",
        "geometrical_factor_for_green_gauss_gradient_y",
        ("cell", "c2e2co"),
        "cell",
    ),
    ("icon:nudgecoeff_e", "nudging_coefficients_for_edges", ("edge",), "edge"),
    (
        "icon:rbf_vec_coeff_v1",
        "rbf_interpolation_coefficient_vertex_1",
        ("vertex", "v2e"),
        "vertex",
    ),
    (
        "icon:rbf_vec_coeff_v2",
        "rbf_interpolation_coefficient_vertex_2",
        ("vertex", "v2e"),
        "vertex",
    ),
    ("icon:rbf_vec_coeff_e", "rbf_interpolation_coefficient_edge", ("edge", "e2c2e"), "edge"),
    (
        "icon:c_intp",
        "cell_to_vertex_interpolation_factor_by_area_weighting",
        ("vertex", "v2c"),
        "vertex",
    ),
    ("icon:pos_on_tplane_e_x", "pos_on_tplane_e_x", ("edge", "e2c"), "edge"),
    ("icon:pos_on_tplane_e_y", "pos_on_tplane_e_y", ("edge", "e2c"), "edge"),
    ("icon:e_flx_avg", "e_flux_average", ("edge", "e2c2eo"), "edge"),
)


def wrap_static_field(value: Any, spec: FieldSpec, grid_uuid: str) -> xr.DataArray:
    """Package a factory output as a read-only static-state DataArray."""
    array = np.asarray(value.asnumpy() if hasattr(value, "asnumpy") else value)
    array = array.copy()
    array.setflags(write=False)
    return make_dataarray(
        array,
        name=spec.name,
        dims=spec.dims,
        units=canonical_units(spec.name),
        location=spec.location,
        grid_uuid=grid_uuid,
    )


def select_specs(
    table: Mapping[str, FieldSpec], fields: Iterable[str] | None
) -> tuple[FieldSpec, ...]:
    """Resolve a registry-name selection against a spec table (default: all)."""
    if fields is None:
        return tuple(table.values())
    selected = []
    for name in fields:
        if name not in table:
            raise KeyError(f"unknown static field {name!r}; known fields: {', '.join(table)}.")
        selected.append(table[name])
    return tuple(selected)


def build_interpolation_factory(grid: IconGrid, config: Any | None = None) -> Any:
    """The pinned icon4py ``InterpolationFieldsFactory`` for ``grid``.

    ``config`` is an icon4py ``InterpolationConfig`` (``None`` → its defaults = the
    ICON namelist defaults). Shared by :func:`interpolation` and the metrics factory
    (which depends on interpolation coefficients).
    """
    from icon4py.model.common.decomposition import definitions as decomposition
    from icon4py.model.common.interpolation import (
        interpolation_attributes,
        interpolation_factory,
    )

    if config is None:
        config = interpolation_factory.InterpolationConfig()
    return interpolation_factory.InterpolationFieldsFactory(
        grid=grid.icon4py_grid,
        decomposition_info=grid.decomposition_info,
        geometry_source=grid.icon4py_geometry,
        backend=grid.gt4py_backend,
        metadata=dict(interpolation_attributes.attrs),
        config=config,
        exchange=decomposition.single_node_exchange,
    )


def interpolation(
    grid: IconGrid,
    *,
    config: Any | None = None,
    fields: Iterable[str] | None = None,
) -> Mapping[str, xr.DataArray]:
    """Compute the static interpolation coefficients (frozen interface, SPEC S11).

    Returns a read-only mapping registry-name → read-only DataArray (dims/location
    stamped, ``grid_uuid`` provenance). ``config`` is an icon4py
    ``InterpolationConfig`` (``None`` → ICON namelist defaults); ``fields`` selects a
    subset of :data:`INTERPOLATION_FIELDS` by registry name (default: all).
    """
    factory = build_interpolation_factory(grid, config)
    specs = select_specs(INTERPOLATION_FIELDS, fields)
    return MappingProxyType(
        {spec.name: wrap_static_field(factory.get(spec.i4_name), spec, grid.uuid) for spec in specs}
    )
