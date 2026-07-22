"""``IconGrid`` — the ICON horizontal grid (architecture §3.1, S11).

One immutable object per horizontal domain, constructed from an ICON grid NetCDF file
and keyed by ``uuidOfHGrid``. Connectivities are exposed in two forms from one storage:
raw numpy index arrays (JAX segment-sum patterns, numpy reference components) and the
gt4py offset-provider mapping consumed by :mod:`icon_sc.core.ingress.gt4py` programs and
icon4py granules. The grid — not the state — owns topology; components receive it at
construction time.

Implementation policy (PLAN S11 item 1): construction *delegates* to pinned icon4py's
``GridManager`` (file parsing, 0-based normalization, derived diamond/butterfly
connectivities, start/end domain indices, single-node decomposition) and
``GridGeometry`` (geometry fields) — REFERENCES.lock id ``icon4py-grid-stack``. The
pure-numpy reader in :mod:`icon_sc.icon.grid.reader` is the independent ingestion path;
their equivalence is a datatest (SPEC acceptance 2).
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np
import numpy.typing as npt

from icon_sc.core.context import ComputeContext
from icon_sc.core.ingress.gt4py import Backend
from icon_sc.icon.grid.geometry import Geometry

__all__ = ["IconGrid", "from_file"]

_I32 = npt.NDArray[np.int32]


def _gt4py_backend(ctx: ComputeContext | None) -> Any | None:
    """The gt4py program processor for ``ctx`` (``None`` = embedded/CPU)."""
    if ctx is None:
        return None
    if isinstance(ctx.backend, Backend):
        return ctx.backend.gt4py_backend
    from icon_sc.core.ingress.gt4py import make_backend

    return make_backend(ctx.backend).gt4py_backend


class IconGrid:
    """The ICON horizontal grid (frozen interface, SPEC S11).

    Built via :func:`from_file`; wraps the icon4py grid object (public accessor
    :attr:`icon4py_grid` for lane-B components), the decomposition info and the lazy
    geometry factory. All numpy views are read-only copies; the offset-provider
    mapping aliases the wrapped grid's connectivities (zero-copy into gt4py).
    """

    def __init__(
        self,
        *,
        i4_grid: Any,
        decomposition_info: Any,
        coordinates: Any,
        geometry_fields: Any,
        gt4py_backend: Any | None,
    ) -> None:
        self._i4_grid = i4_grid
        self._decomposition_info = decomposition_info
        self._coordinates = coordinates
        self._geometry_fields = geometry_fields
        self._gt4py_backend = gt4py_backend
        self._geometry: Geometry | None = None
        self._connectivities: Mapping[str, _I32] | None = None
        self._refin_ctrl: Mapping[str, _I32] | None = None

    # --- identity and sizes -----------------------------------------------------------

    @property
    def uuid(self) -> str:
        """``uuidOfHGrid`` of the source grid file."""
        return str(self._i4_grid.id)

    @property
    def n_cells(self) -> int:
        return int(self._i4_grid.num_cells)

    @property
    def n_edges(self) -> int:
        return int(self._i4_grid.num_edges)

    @property
    def n_vertices(self) -> int:
        return int(self._i4_grid.num_vertices)

    @property
    def limited_area(self) -> bool:
        """True for regional (limited-area) grids — boundary refin_ctrl points exist."""
        return bool(self._i4_grid.limited_area)

    @property
    def geometry_type(self) -> str:
        """``"icosahedron"`` (sphere) or ``"torus"`` (planar doubly-periodic)."""
        return str(self._i4_grid.geometry_type.name.lower())

    # --- topology: one storage, two views (§3.1) ---------------------------------------

    @property
    def connectivities(self) -> Mapping[str, _I32]:
        """Raw index arrays: offset name -> ``(horizontal, sparse)`` int32 table.

        0-based, ``-1`` marks missing neighbors (pentagon points; LAM boundaries).
        Includes the file-sourced tables (C2E, E2C, E2V, C2V, C2E2C, V2E, V2C, V2E2V)
        and icon4py's derived ones (E2C2V, E2C2E, E2C2EO, C2E2CO, C2E2C2E, C2E2C2E2C).
        """
        if self._connectivities is None:
            from gt4py.next import common as gtx_common

            tables: dict[str, _I32] = {}
            for name, connectivity in self._i4_grid.connectivities.items():
                if not gtx_common.is_neighbor_table(connectivity):
                    continue  # Koff -> KDim dimension entry
                table = np.asarray(connectivity.asnumpy(), dtype=np.int32).copy()
                table.setflags(write=False)
                tables[str(name)] = table
            self._connectivities = MappingProxyType(tables)
        return self._connectivities

    @property
    def offset_providers(self) -> Mapping[str, Any]:
        """The gt4py offset-provider mapping (frozen interface, SPEC S11).

        Exactly what ``gt4py.next`` programs take as ``offset_provider=``; includes
        the vertical ``Koff`` dimension mapping. Aliases the wrapped icon4py grid's
        connectivity storage — do not mutate.
        """
        return MappingProxyType(self._i4_grid.connectivities)

    @property
    def refin_ctrl(self) -> Mapping[str, _I32]:
        """Grid-refinement control per location (retained for future LAM/nesting §10)."""
        if self._refin_ctrl is None:
            from icon4py.model.common import dimension as dims

            fields = self._i4_grid.refinement_control
            table = {}
            for location, dim in (
                ("cell", dims.CellDim),
                ("edge", dims.EdgeDim),
                ("vertex", dims.VertexDim),
            ):
                array = np.asarray(fields[dim].asnumpy(), dtype=np.int32).copy()
                array.setflags(write=False)
                table[location] = array
            self._refin_ctrl = MappingProxyType(table)
        return self._refin_ctrl

    # --- geometry -----------------------------------------------------------------------

    @property
    def geometry(self) -> Geometry:
        """Named geometry fields (lazy icon4py ``GridGeometry`` behind :class:`Geometry`)."""
        if self._geometry is None:
            self._geometry = Geometry(self.icon4py_geometry)
        return self._geometry

    # --- donor-object accessors (lane-B wrappers; declared public, S11) -----------------

    @property
    def icon4py_grid(self) -> Any:
        """The wrapped icon4py ``IconGrid`` (start/end indices, gt4py connectivities)."""
        return self._i4_grid

    @property
    def icon4py_geometry(self) -> Any:
        """The icon4py ``GridGeometry`` field source (built lazily, then cached)."""
        if not hasattr(self, "_i4_geometry"):
            from icon4py.model.common.decomposition import definitions as decomposition
            from icon4py.model.common.grid import geometry as i4_geometry
            from icon4py.model.common.grid import geometry_attributes as geometry_attrs

            self._i4_geometry = i4_geometry.GridGeometry(
                grid=self._i4_grid,
                decomposition_info=self._decomposition_info,
                backend=self._gt4py_backend,
                coordinates=self._coordinates,
                extra_fields=self._geometry_fields,
                # GridGeometry registers inverse-field metadata into this dict: copy.
                metadata=dict(geometry_attrs.attrs),
                exchange=decomposition.single_node_exchange,
            )
        return self._i4_geometry

    @property
    def decomposition_info(self) -> Any:
        """icon4py ``DecompositionInfo`` (single-node here; distributed arrives in P5)."""
        return self._decomposition_info

    @property
    def gt4py_backend(self) -> Any | None:
        """The gt4py program processor the grid was built for (``None`` = embedded)."""
        return self._gt4py_backend

    def __repr__(self) -> str:
        return (
            f"IconGrid(uuid={self.uuid!r}, cells={self.n_cells}, edges={self.n_edges}, "
            f"vertices={self.n_vertices}, {self.geometry_type}, "
            f"limited_area={self.limited_area})"
        )


def from_file(
    path: str | pathlib.Path,
    ctx: ComputeContext | None,
    *,
    num_levels: int = 1,
    keep_skip_values: bool = True,
) -> IconGrid:
    """Read an ICON grid NetCDF file into an :class:`IconGrid` (frozen interface).

    ``ctx`` selects backend/allocator for the grid buffers and the lazily computed
    geometry fields (``None`` → embedded/CPU). ``num_levels`` sizes the vertical axis
    the wrapped icon4py grid carries (icon4py bundles it with the horizontal topology;
    a grid *file* knows nothing vertical — pass the model's level count when the grid
    hosts K-dependent factories, cf. :func:`icon_sc.icon.grid.metrics.metrics`).
    ``keep_skip_values=True`` preserves ``-1`` invalid neighbors in the raw index
    arrays (icon4py's geometry/factory convention).

    Malformed files surface icon4py's reader errors annotated with the file path.

    Raises:
        FileNotFoundError: If the file is missing.
    """
    file_path = pathlib.Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"ICON grid file not found: {file_path}")
    if num_levels < 1:
        raise ValueError(f"num_levels must be >= 1, got {num_levels}.")

    from icon4py.model.common import exceptions as i4_exceptions
    from icon4py.model.common import model_backends
    from icon4py.model.common.grid import grid_manager as gm
    from icon4py.model.common.grid import gridfile
    from icon4py.model.common.grid import vertical as i4_vertical

    from icon_sc.icon.grid.reader import GridFileError

    gt4py_backend = _gt4py_backend(ctx)
    allocator = model_backends.get_allocator(gt4py_backend)
    manager = gm.GridManager(
        grid_file=str(file_path),
        config=i4_vertical.VerticalGridConfig(num_levels=num_levels),
        offset_transformation=gridfile.ToZeroBasedIndexTransformation(),
    )
    try:
        manager(allocator=allocator, keep_skip_values=keep_skip_values)
    except (gm.IconGridError, i4_exceptions.IconGridError, KeyError) as exc:
        raise GridFileError(
            f"{file_path}: not a valid ICON grid file — the icon4py grid reader "
            f"failed with: {exc!r}"
        ) from exc

    return IconGrid(
        i4_grid=manager.grid,
        decomposition_info=manager.decomposition_info,
        coordinates=manager.coordinates,
        geometry_fields=manager.geometry_fields,
        gt4py_backend=gt4py_backend,
    )
