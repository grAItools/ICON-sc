"""Trivial pointwise icon4py host grid for column physics (S07 → shared in S08).

The fast-physics granules symcon hosts on columns (satad, graupel) consume no
horizontal connectivities — satad's stencils are pointwise on (Cell, K) and the
graupel scheme is one forward K-scan per column — so the horizontal grid
degenerates to sizes plus the zone index functions (the ``simple_grid``
precedent, REFERENCES.lock ``icon4py-satad``/``icon4py-graupel``:
``start_index`` is 0 except for halo zones, ``end_index`` is the dim size).

Hoisted out of ``satad.py`` when the second consumer (graupel, S08) landed —
the S07 STATUS.md follow-up.
"""

from __future__ import annotations

from typing import Any

__all__ = ["column_icon4py_grid"]


def column_icon4py_grid(n_cell: int, num_levels: int) -> Any:
    """A trivial pointwise icon4py grid hosting ``n_cell`` columns."""
    import gt4py.next as gtx
    from icon4py.model.common import dimension as i4_dims
    from icon4py.model.common.grid import base as i4_base

    sizes = {i4_dims.CellDim: n_cell, i4_dims.EdgeDim: 0, i4_dims.VertexDim: 0}

    def start_index(domain: Any) -> Any:
        return gtx.int32(sizes[domain.dim]) if domain.zone.is_halo() else gtx.int32(0)

    def end_index(domain: Any) -> Any:
        return gtx.int32(sizes[domain.dim])

    config = i4_base.GridConfig(
        horizontal_config=i4_base.HorizontalGridSize(num_vertices=0, num_edges=0, num_cells=n_cell),
        vertical_size=num_levels,
        limited_area=False,
    )
    return i4_base.Grid(
        id="symcon_column",
        config=config,
        connectivities={},
        start_index=start_index,
        end_index=end_index,
    )
