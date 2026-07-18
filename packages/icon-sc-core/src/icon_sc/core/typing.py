"""Boundary types of the state layer (architecture §2.2).

- :class:`FieldBuffer` — the minimal buffer protocol every state value's ``.data``
  must satisfy (``numpy.ndarray`` and ``cupy.ndarray`` in practice).
- :class:`Location` — mesh location typing for fields (``scalar`` for 0-d/parameter
  fields that live on no mesh location).
- :class:`HaloState` — halo validity of a *state* field (``attrs["halo"]``); not to be
  confused with the contract-side halo policy of a *property dict*
  (:class:`icon_sc.core.contracts.properties.HaloPolicy`).
"""

from __future__ import annotations

import enum
from typing import Any, Protocol, runtime_checkable

__all__ = ["FieldBuffer", "HaloState", "Location"]


@runtime_checkable
class FieldBuffer(Protocol):
    """Minimal duck-array boundary protocol (architecture §2.2, frozen interface).

    Runtime checks test attribute *presence* only; the DLpack device tuple is the
    portable device identity used by the dynamic checkers.
    """

    def __dlpack__(self, *, stream: int | None = None) -> object: ...

    def __dlpack_device__(self) -> tuple[int, int]: ...

    @property
    def shape(self) -> tuple[int, ...]: ...

    @property
    def dtype(self) -> Any: ...


class Location(str, enum.Enum):
    """Mesh location of a field (redundant with dims, explicit for scalars/sparse)."""

    CELL = "cell"
    EDGE = "edge"
    VERTEX = "vertex"
    SCALAR = "scalar"

    def __str__(self) -> str:
        return self.value


class HaloState(str, enum.Enum):
    """Halo validity of a state field, consumed by the halo validator pass (§6.3)."""

    VALID = "valid"
    DIRTY = "dirty"

    def __str__(self) -> str:
        return self.value


#: Dimension names that name a horizontal mesh location (used for dims/location checks).
HORIZONTAL_DIMS: frozenset[str] = frozenset({"cell", "edge", "vertex"})
