"""Minimal ``ComputeContext`` for the T0 slice (architecture §5.2, SPEC S03).

The one object threaded through component construction. In this step it carries
only what T0 dispatch needs: an **opaque backend name** (real backend objects
arrive with the first gt4py component, S07), the **strict-mode flag** (§2.4) and
an **allocator** choosing numpy or cupy. ``ctx.timeloop()`` is deliberately absent
(S05); the T0 loop helper lives in :mod:`symcon.core.driver.timeloop`.

Components allocate their private and output fields through the context; nothing
else in symcon touches devices directly (§5.2).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Protocol, runtime_checkable

import numpy as np

from symcon.core.typing import FieldBuffer

__all__ = ["Allocator", "ComputeContext"]

#: Backend-name substrings that select the cupy allocator (T0 rule: the backend is
#: an opaque string; S07 replaces this with real backend objects).
_GPU_MARKERS: tuple[str, ...] = ("gpu", "cuda")


@runtime_checkable
class Allocator(Protocol):
    """Minimal allocator protocol: uninitialized device buffers by shape/dtype."""

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer: ...


class _NumpyAllocator:
    """Host allocator (numpy)."""

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer:
        return np.empty(shape, dtype=dtype)


class _CupyAllocator:
    """CUDA device allocator (cupy); constructing it requires cupy."""

    def __init__(self) -> None:
        import cupy

        self._cupy = cupy

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer:
        buffer: FieldBuffer = self._cupy.empty(shape, dtype=dtype)
        return buffer


@dataclasses.dataclass(frozen=True)
class ComputeContext:
    """Compute context of the T0 slice (frozen interface, SPEC S03).

    ``ComputeContext(backend, strict=True, allocator=...)`` — ``backend`` is an
    opaque string in this step (``embedded``/``gtfn_cpu``/``gtfn_gpu``); when
    ``allocator`` is not given it is derived from the backend name (cupy for
    GPU-flavoured backends, numpy otherwise). ``strict`` is the §2.4 strict-mode
    flag consumed by the dynamic checkers on every component call.

    ``device`` is the DLPack device tuple of the allocator's buffers, probed once
    at construction; it is the device expectation handed to the
    :class:`~symcon.core.contracts.checkers.DynamicChecker`.
    """

    backend: str
    strict: bool = True
    allocator: Allocator | None = None
    device: tuple[int, int] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        if self.allocator is None:
            gpu = any(marker in self.backend.lower() for marker in _GPU_MARKERS)
            allocator: Allocator = _CupyAllocator() if gpu else _NumpyAllocator()
            object.__setattr__(self, "allocator", allocator)
        probe = self.require_allocator.empty((0,), np.float64)
        raw_device = probe.__dlpack_device__()
        object.__setattr__(self, "device", (int(raw_device[0]), int(raw_device[1])))

    @property
    def require_allocator(self) -> Allocator:
        """The resolved allocator (never ``None`` after construction)."""
        assert self.allocator is not None  # resolved in __post_init__
        return self.allocator
