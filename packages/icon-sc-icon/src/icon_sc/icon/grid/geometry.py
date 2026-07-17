"""Named grid-geometry fields (architecture §3.1, S11).

``grid.geometry.<named field>`` (frozen interface) exposes the horizontal geometry —
edge lengths, dual lengths, areas, orientation, coriolis — as read-only numpy fp64
arrays. Computation is delegated to pinned icon4py's ``GridGeometry`` field factory
(REFERENCES.lock id ``icon4py-grid-stack``): file-sourced quantities (areas, lengths,
orientations) pass through; derived ones (edge area, coriolis parameter, far-vertex
distance, normals/tangents) are computed lazily on first access with the grid's
backend.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import numpy.typing as npt

__all__ = ["Geometry"]

_F64 = npt.NDArray[np.float64]

#: ICON-sc name -> icon4py geometry_attributes standard name.
_NAMES: Final[dict[str, str]] = {
    "cell_area": "cell_area",
    "dual_area": "dual_area",
    "edge_area": "edge_area",
    "edge_length": "edge_length",
    "dual_edge_length": "length_of_dual_edge",
    "vertex_vertex_length": "vertex_vertex_length",
    "tangent_orientation": "edge_orientation",
    "coriolis_parameter": "coriolis_parameter",
}


class Geometry:
    """Read-only view of the grid's geometry fields (frozen interface, SPEC S11).

    Attribute access returns numpy fp64 arrays (host copies, write-protected, cached);
    :meth:`names` lists the available fields. ``coriolis_parameter`` lives on edges
    (the dycore's consumer location, icon4py convention).
    """

    def __init__(self, i4_geometry: Any) -> None:
        self._i4_geometry = i4_geometry
        self._cache: dict[str, _F64] = {}

    @staticmethod
    def names() -> tuple[str, ...]:
        """The named geometry fields this surface provides."""
        return tuple(_NAMES)

    def get(self, name: str) -> _F64:
        """Fetch a named geometry field as a read-only numpy array."""
        if name not in _NAMES:
            raise AttributeError(
                f"unknown geometry field {name!r}; known fields: {', '.join(_NAMES)}."
            )
        if name not in self._cache:
            field = self._i4_geometry.get(_NAMES[name])
            array = np.asarray(field.asnumpy(), dtype=np.float64).copy()
            array.setflags(write=False)
            self._cache[name] = array
        return self._cache[name]

    def __getattr__(self, name: str) -> _F64:
        # Only called for attributes not found normally -> named geometry fields.
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get(name)

    def __dir__(self) -> list[str]:
        return sorted(set(super().__dir__()) | set(_NAMES))

    def __repr__(self) -> str:
        return f"Geometry(fields={list(_NAMES)})"
