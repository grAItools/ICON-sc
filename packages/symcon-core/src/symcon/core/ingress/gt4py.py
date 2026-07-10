"""gt4py backend object + zero-copy field ingress (architecture §2.3, §5.2; SPEC S07).

S07 extends the ``ComputeContext`` backend from an opaque string to a small
**backend object**: :class:`Backend` bundles the gt4py program processor, the
buffer allocator, the zero-copy ``as_field`` ingress and the offset-provider
hook. ``make_backend(name) -> Backend`` (frozen interface) is used by every
later gt4py component; :class:`~symcon.core.context.ComputeContext` accepts
either the S03 opaque string or a :class:`Backend` directly.

Zero-copy note (REFERENCES.lock id ``gt4py-field-ctor``): public
``gtx.as_field`` *always* allocates by design, so :meth:`Backend.as_field`
wraps buffers through the ``gt4py.next.common._field`` constructor, which
aliases the buffer (``field.ndarray is buffer``) — the §2.3 ingress contract.

gt4py is an *optional* dependency of symcon-core (``symcon-core[gt4py]``); it
is imported lazily so the core package keeps working without it, and every
import failure names the missing extra.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from symcon.core.typing import FieldBuffer

if TYPE_CHECKING:
    from symcon.core.context import Allocator

__all__ = ["Backend", "make_backend"]

#: Names accepted by :func:`make_backend` (the S03 backend strings).
BACKEND_NAMES: Final[tuple[str, ...]] = ("embedded", "gtfn_cpu", "gtfn_gpu")

#: Empty offset-provider mapping: the column has no horizontal connectivity (§3);
#: grids contribute their own providers from S11 on.
_NO_OFFSETS: Final[Mapping[str, Any]] = MappingProxyType({})


def _import_gt4py() -> Any:
    try:
        import gt4py.next as gtx
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ImportError(
            "symcon.core.ingress.gt4py requires gt4py; install the "
            "symcon-core[gt4py] extra (pinned pair in constraints/)."
        ) from exc
    return gtx


@dataclasses.dataclass(frozen=True)
class Backend:
    """The small backend object of §5.2 (frozen interface, SPEC S07).

    - ``name`` — the S03 backend string this object was made from;
    - ``gt4py_backend`` — the gt4py program processor
      (``gt4py.next.backend.Backend``), or ``None`` for embedded execution
      (the gt4py/icon4py convention: ``program.with_backend(None)`` runs the
      field-operator reference semantics);
    - ``allocator`` — the :class:`~symcon.core.context.Allocator` for buffers
      on this backend's device;
    - ``offset_provider`` — the offset-provider hook. Defaults to the empty
      mapping: correct for column components; horizontal grids override it.
    """

    name: str
    gt4py_backend: Any | None
    allocator: Allocator
    offset_provider: Mapping[str, Any] = _NO_OFFSETS

    def as_field(self, dims: tuple[str, ...], buffer: FieldBuffer) -> Any:
        """Wrap ``buffer`` as a gt4py field over ``dims`` — zero-copy (§2.3).

        ``dims`` are gt4py dimension *values* (``gt4py.next.Dimension``) or
        plain names; names are promoted to horizontal dimensions of kind
        ``horizontal`` except the conventional vertical names (``height``/
        ``height_interface``/``K``), which become vertical dimensions. The
        returned field aliases ``buffer`` (``field.ndarray is buffer``);
        writes through the field mutate the vault buffer.
        """
        gtx = _import_gt4py()
        from gt4py.next import common as gtx_common

        gtx_dims = tuple(self._as_dimension(gtx, d) for d in dims)
        domain = gtx_common.domain(
            {dim: size for dim, size in zip(gtx_dims, buffer.shape, strict=True)}
        )
        # Public gtx.as_field always copies (by design); the singledispatch
        # _field constructor is the aliasing wrap (REFERENCES.lock gt4py-field-ctor).
        return gtx_common._field(buffer, domain=domain)

    @staticmethod
    def _as_dimension(gtx: Any, dim: Any) -> Any:
        if isinstance(dim, gtx.Dimension):
            return dim
        if not isinstance(dim, str):
            raise TypeError(f"dims entries must be str or gt4py Dimension, got {dim!r}.")
        vertical = {"height", "height_interface", "K", "KHalf"}
        kind = gtx.DimensionKind.VERTICAL if dim in vertical else gtx.DimensionKind.HORIZONTAL
        return gtx.Dimension(dim, kind=kind)


def make_backend(name: str) -> Backend:
    """Resolve an S03 backend string to a :class:`Backend` (frozen interface).

    ``embedded`` → no program processor (gt4py embedded execution) + numpy
    buffers; ``gtfn_cpu`` → ``gtx.gtfn_cpu`` + numpy; ``gtfn_gpu`` →
    ``gtx.gtfn_gpu`` + cupy (constructing it requires cupy).
    """
    from symcon.core.context import _CupyAllocator, _NumpyAllocator

    gtx = _import_gt4py()
    if name == "embedded":
        return Backend(name=name, gt4py_backend=None, allocator=_NumpyAllocator())
    if name == "gtfn_cpu":
        return Backend(name=name, gt4py_backend=gtx.gtfn_cpu, allocator=_NumpyAllocator())
    if name == "gtfn_gpu":
        return Backend(name=name, gt4py_backend=gtx.gtfn_gpu, allocator=_CupyAllocator())
    raise ValueError(f"unknown backend name {name!r}; known: {BACKEND_NAMES!r}.")


def resolve_backend(backend: str | Backend) -> Backend:
    """`backend` itself if already a :class:`Backend`, else :func:`make_backend`.

    The convenience for components reading ``ctx.backend``, which is
    ``str | Backend`` since S07.
    """
    if isinstance(backend, Backend):
        return backend
    return make_backend(backend)
