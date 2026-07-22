"""Numpy-level dict arithmetic for the coupling algebra (SPEC S04, PLAN item 3).

The T0 recombinations — :class:`~icon_sc.core.coupling.federations.ParallelSplitting`'s
``ψⁿ⁺¹ = Σψₗ - L·ψⁿ`` and the stage updates of the tendency steppers — reduce to a
handful of axpy-shaped operations over ``name -> DataArray`` dicts. They are kept
deliberately dumb (numpy expressions on ``.data`` buffers); the S05 plan compiler
turns them into fused vault ops (architecture §8.2).

Semantics donor: tasmania's ``DataArrayDictOperator`` (``fma``/``iaddsub``, see
REFERENCES.lock) minus its gt4py stencil dispatch and unit-conversion paths —
canonical units + strict mode make the payloads directly combinable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

__all__ = ["dict_axpy", "dict_fma"]


def _shared_fields(
    y: Mapping[str, Any], x: Mapping[str, Any], fields: Iterable[str] | None
) -> tuple[str, ...]:
    if fields is not None:
        return tuple(fields)
    return tuple(name for name in y if name != "time" and name in x)


def dict_axpy(
    y: Mapping[str, Any],
    a: float,
    x: Mapping[str, Any],
    fields: Iterable[str] | None = None,
) -> None:
    """In place ``y[f].data += a * x[f].data`` over ``fields`` (frozen helper, SPEC S04).

    ``fields`` defaults to the keys shared by both dicts (``time`` excluded). Values
    are boundary DataArrays; the arithmetic happens on their ``.data`` buffers, so
    buffer identity in ``y`` is preserved (the property the S05 vault relies on).
    """
    factor = float(a)
    for name in _shared_fields(y, x, fields):
        y[name].data[...] += factor * x[name].data


def dict_fma(
    base: Mapping[str, Any],
    increment: Mapping[str, Any],
    factor: float,
    fields: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Out-of-place ``base[f].data + factor * increment[f].data`` per field.

    Returns:
        Plain buffers (not DataArrays), keyed by field — the stage-state payloads
        the tendency steppers thread between evaluations (tasmania ``fma``).
    """
    scale = float(factor)
    return {
        name: base[name].data + scale * increment[name].data
        for name in _shared_fields(base, increment, fields)
    }
