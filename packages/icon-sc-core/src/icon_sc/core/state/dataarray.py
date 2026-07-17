"""Boundary DataArray construction (architecture §2.2).

State values are ``xarray.DataArray`` s over :class:`~symcon.core.typing.FieldBuffer`
buffers; construction here is the only sanctioned way to stamp the attrs schema
(``units`` / ``location`` / ``halo`` / ``grid_uuid``). The buffer is wrapped, never
copied and never coerced (no ``.values`` anywhere on core paths — the duck-array
lesson of §4.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import xarray as xr

from symcon.core.typing import HORIZONTAL_DIMS, FieldBuffer, HaloState, Location

__all__ = ["make_dataarray"]


def make_dataarray(
    buffer: FieldBuffer,
    *,
    name: str,
    dims: Sequence[str],
    units: str,
    location: Location | str,
    grid_uuid: str | None = None,
) -> xr.DataArray:
    """Wrap ``buffer`` in a boundary DataArray (frozen interface, SPEC S02).

    Stamps ``attrs['units']``, ``attrs['location']``, ``attrs['halo']``
    (:attr:`HaloState.VALID` — a freshly constructed field has no stale ghost points
    by definition; the halo validator pass flips it) and, when given,
    ``attrs['grid_uuid']`` (provenance: refuse to mix grids, §2.2).

    Raises ``TypeError``/``ValueError`` on non-conforming buffers, rank mismatch, or
    a horizontal dim contradicting ``location``.
    """
    if not isinstance(buffer, FieldBuffer):
        raise TypeError(
            f"buffer for {name!r} ({type(buffer).__name__}) does not satisfy the "
            f"FieldBuffer protocol (__dlpack__/__dlpack_device__/shape/dtype)."
        )
    loc = Location(location)
    dims = tuple(dims)
    if len(dims) != len(buffer.shape):
        raise ValueError(
            f"{name!r}: {len(dims)} dims {dims!r} for a rank-{len(buffer.shape)} "
            f"buffer of shape {buffer.shape!r}."
        )
    horizontal = [d for d in dims if d in HORIZONTAL_DIMS]
    if len(horizontal) > 1:
        raise ValueError(f"{name!r}: multiple horizontal dims {horizontal!r}.")
    if horizontal and horizontal[0] != loc.value:
        raise ValueError(
            f"{name!r}: horizontal dim {horizontal[0]!r} contradicts location={loc.value!r}."
        )
    if loc is not Location.SCALAR and not horizontal and dims:
        raise ValueError(
            f"{name!r}: location={loc.value!r} but no horizontal dim in {dims!r} "
            f"(use Location.SCALAR for fields on no mesh location)."
        )
    attrs: dict[str, Any] = {
        "units": units,
        "location": loc,
        "halo": HaloState.VALID,
    }
    if grid_uuid is not None:
        attrs["grid_uuid"] = grid_uuid
    return xr.DataArray(buffer, dims=dims, name=name, attrs=attrs)
