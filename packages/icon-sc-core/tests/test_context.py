"""ComputeContext tests (SPEC S03: backend name, allocator, strict flag)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from icon_sc.core import Allocator, ComputeContext, FieldBuffer


def test_default_is_strict_numpy_on_host() -> None:
    ctx = ComputeContext(backend="embedded")
    assert ctx.strict is True
    assert ctx.device == (1, 0)  # kDLCPU
    buffer = ctx.require_allocator.empty((2, 3), np.float64)
    assert isinstance(buffer, np.ndarray)
    assert buffer.shape == (2, 3)
    assert buffer.dtype == np.float64


def test_cpu_backend_names_use_numpy() -> None:
    for backend in ("embedded", "gtfn_cpu"):
        ctx = ComputeContext(backend=backend)
        assert isinstance(ctx.require_allocator.empty((1,), np.float64), np.ndarray)


def test_custom_allocator_wins_over_backend_name() -> None:
    class Recording:
        def __init__(self) -> None:
            self.requests: list[tuple[tuple[int, ...], Any]] = []

        def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer:
            self.requests.append((shape, dtype))
            return np.empty(shape, dtype=dtype)

    allocator = Recording()
    assert isinstance(allocator, Allocator)
    ctx = ComputeContext(backend="gtfn_gpu", allocator=allocator)
    ctx.require_allocator.empty((4,), np.float32)
    # the device probe at construction plus our request
    assert allocator.requests == [((0,), np.float64), ((4,), np.float32)]


def test_strict_flag_is_carried() -> None:
    assert ComputeContext(backend="embedded", strict=False).strict is False


@pytest.mark.gpu
def test_gpu_backend_uses_cupy() -> None:
    cupy = pytest.importorskip("cupy")
    ctx = ComputeContext(backend="gtfn_gpu")
    buffer = ctx.require_allocator.empty((2,), np.float64)
    assert isinstance(buffer, cupy.ndarray)
    assert ctx.device[0] == 2  # kDLCUDA
