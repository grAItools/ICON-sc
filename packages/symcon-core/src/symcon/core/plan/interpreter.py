"""The T1 plan interpreter (architecture §8.3, SPEC S05).

A boring, measurable ``for`` loop over pre-bound ops with a ``match`` on the op
type — per-op cost is one Python dispatch plus the op's kernel calls. No dict
lookups on state names, no xarray, no contract logic, no per-step allocation
beyond CPython transients (iterators, boxed scalars) that are freed within the
step (the SPEC's tracemalloc criterion: traced memory is step-invariant after
warmup).

Every arithmetic op executes the exact ufunc sequence its
:mod:`symcon.core.plan.ops` docstring declares (normative; bitwise T0≡T1).

**The host-step seam (S14).** ``run_ops(..., on_segment=...)`` yields to a host
callback at every :class:`~symcon.core.plan.ops.SegmentMarker` — the minimal
seam the T2 graph-replay tier needs: under stream capture each exchange-free
segment becomes one captured graph, and the interpreter's per-marker yield is
exactly where T2 stops replaying and returns control to Python (monitors, time
advancement, MPI, bridge calls — everything excluded from the plan). At T1 the
callback costs one ``is not None`` check per marker; ``ctx.timeloop`` uses it
to run monitors against the vault façade in the ``step_end`` host step (design
note only — no T2 code in the slice).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from symcon.core.plan.ops import (
    Axpy,
    BoundCall,
    CadenceMask,
    DiffScale,
    SegmentMarker,
    Swap,
)

__all__ = ["run_ops"]


def run_ops(
    ops: tuple[Any, ...],
    step_index: int,
    on_segment: Callable[[SegmentMarker], None] | None = None,
) -> None:
    """Interpret one pre-bound op list (one step signature) at ``step_index``.

    ``on_segment`` (S14, additive) is invoked with every
    :class:`~symcon.core.plan.ops.SegmentMarker` reached — the host-step seam
    described in the module docstring.
    """
    for op in ops:
        match op:
            case BoundCall(fn, args, _):
                fn(*args)
            case Axpy(y, init, terms, scratch, divisor, _):
                if init is not None:
                    np.multiply(init[1], init[0], out=y)
                for a, x in terms:
                    np.multiply(x, a, out=scratch)
                    np.add(y, scratch, out=y)
                if divisor != 1.0:
                    np.divide(y, divisor, out=y)
            case DiffScale(y, minuend, subtrahend, divisor, _):
                np.subtract(minuend, subtrahend, out=y)
                np.divide(y, divisor, out=y)
            case Swap(vault, slot, alt_store, alt_index, _):
                buffers = vault.buffers
                buffers[slot], alt_store[alt_index] = alt_store[alt_index], buffers[slot]
                vault.note_swap()
            case CadenceMask(period, phase, masked, _):
                if step_index % period == phase:
                    run_ops(masked, step_index)
            case SegmentMarker():
                if on_segment is not None:
                    on_segment(op)
            case _:
                raise TypeError(f"unknown plan op: {op!r}")
