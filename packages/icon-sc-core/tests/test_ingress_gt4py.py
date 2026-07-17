"""S07: gt4py backend object + zero-copy ingress (architecture §2.3, §5.2).

SPEC S07 acceptance 2 (zero-copy: pointer identity between the boundary buffer
and the gt4py field ``.ndarray``, numpy and cupy paths) and the frozen
``make_backend(name) -> Backend`` interface used by every later gt4py component.
"""

from __future__ import annotations

import numpy as np
import pytest

from symcon.core import Backend, ComputeContext, make_backend
from symcon.core.ingress.gt4py import BACKEND_NAMES, resolve_backend

pytest.importorskip("gt4py", reason="symcon-core[gt4py] extra not installed")


def test_make_backend_names() -> None:
    for name in ("embedded", "gtfn_cpu"):
        backend = make_backend(name)
        assert isinstance(backend, Backend)
        assert backend.name == name
    with pytest.raises(ValueError, match="unknown backend"):
        make_backend("nope")
    assert BACKEND_NAMES == ("embedded", "gtfn_cpu", "gtfn_gpu")


def test_embedded_backend_has_no_program_processor() -> None:
    # gt4py/icon4py convention: embedded execution == backend None.
    assert make_backend("embedded").gt4py_backend is None


def test_gtfn_cpu_backend_is_gt4py_backend_object() -> None:
    import gt4py.next as gtx

    backend = make_backend("gtfn_cpu")
    assert backend.gt4py_backend is gtx.gtfn_cpu


@pytest.mark.gpu
def test_gtfn_gpu_backend_allocates_on_device() -> None:
    import cupy

    backend = make_backend("gtfn_gpu")
    buf = backend.allocator.empty((2, 3), np.float64)
    assert isinstance(buf, cupy.ndarray)


def test_as_field_is_zero_copy_numpy() -> None:
    """SPEC acceptance 2 (numpy path): the field aliases the buffer exactly."""
    backend = make_backend("embedded")
    buf = np.arange(12.0).reshape(3, 4)
    field = backend.as_field(("cell", "height"), buf)
    assert field.ndarray is buf  # pointer identity, not just equality
    field.ndarray[0, 0] = 42.0
    assert buf[0, 0] == 42.0


@pytest.mark.gpu
def test_as_field_is_zero_copy_cupy() -> None:
    """SPEC acceptance 2 (cupy path): device pointer identity."""
    import cupy

    backend = make_backend("gtfn_gpu")
    buf = cupy.arange(12.0).reshape(3, 4)
    field = backend.as_field(("cell", "height"), buf)
    assert field.ndarray is buf
    assert field.ndarray.data.ptr == buf.data.ptr


def test_as_field_accepts_gt4py_dimensions() -> None:
    import gt4py.next as gtx

    cell = gtx.Dimension("cell")
    k = gtx.Dimension("height", kind=gtx.DimensionKind.VERTICAL)
    backend = make_backend("embedded")
    buf = np.zeros((2, 5))
    field = backend.as_field((cell, k), buf)
    assert field.domain.dims == (cell, k)
    assert field.ndarray is buf


def test_as_field_vertical_name_promotion() -> None:
    import gt4py.next as gtx

    backend = make_backend("embedded")
    field = backend.as_field(("cell", "height"), np.zeros((2, 5)))
    kinds = [d.kind for d in field.domain.dims]
    assert kinds == [gtx.DimensionKind.HORIZONTAL, gtx.DimensionKind.VERTICAL]


def test_as_field_shape_dims_mismatch_raises() -> None:
    backend = make_backend("embedded")
    with pytest.raises(ValueError):
        backend.as_field(("cell",), np.zeros((2, 5)))


def test_compute_context_accepts_backend_object() -> None:
    """S07 ComputeContext extension: str | Backend, allocator from the object."""
    backend = make_backend("embedded")
    ctx = ComputeContext(backend=backend)
    assert ctx.backend is backend
    assert ctx.backend_name == "embedded"
    assert ctx.allocator is backend.allocator
    assert ctx.device == (1, 0)  # kDLCPU


def test_compute_context_string_path_unchanged() -> None:
    """The S03 opaque-string path is untouched (frozen interface)."""
    ctx = ComputeContext(backend="embedded")
    assert ctx.backend == "embedded"
    assert ctx.backend_name == "embedded"


def test_resolve_backend_roundtrip() -> None:
    backend = make_backend("gtfn_cpu")
    assert resolve_backend(backend) is backend
    assert resolve_backend("embedded").name == "embedded"


def test_offset_provider_defaults_empty() -> None:
    # The column has no horizontal connectivity; grids override from S11 on.
    backend = make_backend("embedded")
    assert dict(backend.offset_provider) == {}
    with pytest.raises(TypeError):
        backend.offset_provider["Koff"] = None  # type: ignore[index]
