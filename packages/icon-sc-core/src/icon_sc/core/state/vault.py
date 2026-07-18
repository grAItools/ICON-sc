"""``StateVault`` — the state's execution-phase form (architecture §8.2, SPEC S05).

A dense, slotted container: a flat ``list`` of raw buffers plus an interned
``name → index`` map that is consulted only at bind time. The public
dict-of-DataArrays view survives as a lazily materialized façade
(:mod:`icon_sc.core.state.facade`), so monitors, interactive inspection and the
interpreted tier keep unmodified sympl semantics while nothing xarray-shaped
executes on the step path.

Two counters govern coherence:

- ``epoch`` — bumped by any **out-of-band** state mutation through the façade
  (rebinding or deleting a field). A plan materialized against the vault records
  the epoch and raises :class:`~icon_sc.core.plan.guards.StalePlanError` on the
  next ``run_step`` after a bump (§8.2 staleness guard).
- ``generation`` — bumped by plan-internal buffer swaps (:class:`~icon_sc.core.plan.ops.Swap`).
  It invalidates the façade's cached DataArray wrappers only; the plan stays
  valid (swaps are its own doing).
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import numpy as np
import xarray as xr

from icon_sc.core.typing import FieldBuffer, Location

if TYPE_CHECKING:
    from icon_sc.core.state.facade import VaultFacade

__all__ = ["SlotMeta", "StateVault"]


@dataclasses.dataclass(frozen=True, slots=True)
class SlotMeta:
    """Boundary metadata of one vault slot (what the façade needs to rewrap it)."""

    name: str
    dims: tuple[str, ...]
    units: str
    location: Location | None
    dtype: np.dtype[Any]
    attrs: Mapping[str, Any]


def _meta_of(name: str, array: xr.DataArray) -> SlotMeta:
    raw_location = array.attrs.get("location")
    return SlotMeta(
        name=name,
        dims=tuple(str(d) for d in array.dims),
        units=str(array.attrs.get("units", "")),
        location=Location(raw_location) if raw_location is not None else None,
        dtype=np.dtype(array.data.dtype),
        attrs=dict(array.attrs),
    )


class StateVault:
    """Slotted execution-phase state (frozen interface, SPEC S05).

    ``StateVault.from_state(state)`` adopts the state's raw buffers (zero-copy:
    ``.data`` of every boundary DataArray, never ``.values``); ``vault.facade()``
    returns the lazy dict-of-DataArrays view. ``buffers``/``names``/
    ``schema_hash``/``epoch`` are the public §8.2 surface; the compiler may
    append slots for published outputs at materialization (``add_slot``), which
    refreshes ``schema_hash``.
    """

    __slots__ = (
        "_facade",
        "_meta",
        "buffers",
        "epoch",
        "generation",
        "names",
        "schema_hash",
        "time",
    )

    def __init__(self) -> None:
        self.buffers: list[FieldBuffer] = []
        self.names: dict[str, int] = {}
        self.schema_hash: str = ""
        self.epoch: int = 0
        self.generation: int = 0
        self.time: Any = None
        self._meta: list[SlotMeta] = []
        self._facade: VaultFacade | None = None

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> StateVault:
        """Build a vault over a dict-of-DataArrays state (frozen interface).

        Buffers are adopted, not copied; the ``time`` entry is carried alongside
        the slots (it is not a field). Non-DataArray entries other than ``time``
        are rejected — the vault is the execution form of a *boundary* state.
        """
        vault = cls()
        for name, value in state.items():
            if name == "time":
                vault.time = value
                continue
            if not isinstance(value, xr.DataArray):
                raise TypeError(
                    f"StateVault.from_state: state[{name!r}] is {type(value).__name__}, "
                    f"not a boundary DataArray."
                )
            buffer = value.data  # never .values: no duck-array coercion (§4.2)
            if not isinstance(buffer, FieldBuffer):
                raise TypeError(
                    f"StateVault.from_state: state[{name!r}].data does not satisfy "
                    f"the FieldBuffer protocol."
                )
            vault._append(name, buffer, _meta_of(name, value))
        vault.schema_hash = vault._compute_schema_hash()
        return vault

    # -- slot surface (bind-time only) -------------------------------------------------

    def _append(self, name: str, buffer: FieldBuffer, meta: SlotMeta) -> int:
        if name in self.names:
            raise ValueError(f"StateVault: slot {name!r} already exists.")
        index = len(self.buffers)
        self.buffers.append(buffer)
        self._meta.append(meta)
        self.names[name] = index
        return index

    def add_slot(self, name: str, buffer: FieldBuffer, meta: SlotMeta) -> int:
        """Append a published-output slot (compiler use, bind/materialize time).

        Refreshes ``schema_hash`` (the slot set is part of the schema) and bumps
        ``generation`` so a live façade picks the new field up.
        """
        index = self._append(name, buffer, meta)
        self.schema_hash = self._compute_schema_hash()
        self.generation += 1
        return index

    def meta(self, index: int) -> SlotMeta:
        """The boundary metadata of slot ``index``."""
        return self._meta[index]

    def dim_sizes(self) -> dict[str, int]:
        """Dimension-name → length map over all slots (consistency-checked)."""
        sizes: dict[str, int] = {}
        for meta, buffer in zip(self._meta, self.buffers, strict=True):
            for dim, size in zip(meta.dims, buffer.shape, strict=True):
                if sizes.setdefault(dim, int(size)) != int(size):
                    raise ValueError(
                        f"StateVault: dim {dim!r} has inconsistent lengths "
                        f"({sizes[dim]} vs {int(size)}, found at {meta.name!r})."
                    )
        return sizes

    def _compute_schema_hash(self) -> str:
        """Stable hash of the slot schema (names, dims, units, dtype, location)."""
        parts = []
        for meta in sorted(self._meta, key=lambda m: m.name):
            parts.append(
                f"{meta.name}|{','.join(meta.dims)}|{meta.units}"
                f"|{meta.dtype.str}|{meta.location.value if meta.location else ''}"
            )
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    # -- coherence counters -------------------------------------------------------------

    def note_out_of_band_mutation(self) -> None:
        """Record an out-of-band mutation (façade rebind/delete): plans go stale."""
        self.epoch += 1
        self.generation += 1

    def note_swap(self) -> None:
        """Record a plan-internal buffer swap: façade caches invalidate, plans stay valid."""
        self.generation += 1

    # -- the public view ----------------------------------------------------------------

    def facade(self) -> Mapping[str, xr.DataArray]:
        """The lazy dict-of-DataArrays view (frozen interface, SPEC S05).

        DataArray wrappers are cached per slot and reconstructed only when the
        vault ``generation`` moved (slot swaps, added slots) — sympl semantics
        for monitors and inspection, zero cost for the step path. The same
        façade object is returned on every call. Rebinding or deleting a field
        *through the façade* bumps ``epoch`` and stales any bound plan.
        """
        from icon_sc.core.state.facade import VaultFacade

        if self._facade is None:
            self._facade = VaultFacade(self)
        return self._facade

    def __repr__(self) -> str:
        return (
            f"StateVault({len(self.buffers)} slots, epoch={self.epoch}, "
            f"generation={self.generation})"
        )
