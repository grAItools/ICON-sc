"""Lazy DataArray façade over a :class:`~symcon.core.state.vault.StateVault` (§8.2).

The public dict-of-DataArrays state view of the execution tier: DataArray
wrappers are materialized on access, cached per slot, and invalidated by the
vault's ``generation`` counter (bumped by plan-internal swaps and slot
additions). **Rebinding or deleting** a field through the façade is an
out-of-band mutation: it bumps the vault ``epoch``, and any plan bound to the
vault raises ``StalePlanError`` on its next ``run_step`` (SPEC S05 guard).
In-place writes to a field's buffer (``facade[name].data[...] = ...``) preserve
buffer identity and do **not** stale plans — values are the user's business,
identities are the plan's.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any

import xarray as xr

from symcon.core.state.dataarray import make_dataarray
from symcon.core.state.vault import StateVault, _meta_of
from symcon.core.typing import FieldBuffer, Location

__all__ = ["VaultFacade"]


class VaultFacade(MutableMapping[str, Any]):
    """Mapping view of a vault: slot fields as boundary DataArrays plus ``time``."""

    __slots__ = ("_cache", "_vault")

    def __init__(self, vault: StateVault) -> None:
        self._vault = vault
        #: slot name -> (generation at build, DataArray wrapper)
        self._cache: dict[str, tuple[int, xr.DataArray]] = {}

    def _wrap(self, name: str, index: int) -> xr.DataArray:
        vault = self._vault
        cached = self._cache.get(name)
        if cached is not None and cached[0] == vault.generation:
            return cached[1]
        meta = vault.meta(index)
        array = make_dataarray(
            vault.buffers[index],
            name=name,
            dims=meta.dims,
            units=meta.units,
            location=meta.location if meta.location is not None else Location.SCALAR,
        )
        # Preserve any extra attrs captured at vault construction (grid_uuid, ...).
        for key, value in meta.attrs.items():
            array.attrs.setdefault(key, value)
        self._cache[name] = (vault.generation, array)
        return array

    def __getitem__(self, name: str) -> Any:
        if name == "time":
            if self._vault.time is None:
                raise KeyError("time")
            return self._vault.time
        index = self._vault.names.get(name)
        if index is None:
            raise KeyError(name)
        return self._wrap(name, index)

    def __setitem__(self, name: str, value: Any) -> None:
        vault = self._vault
        if name == "time":
            vault.time = value
            return
        if not isinstance(value, xr.DataArray):
            raise TypeError(
                f"facade[{name!r}] = {type(value).__name__}: the façade holds boundary "
                f"DataArrays only; write buffers in place via facade[name].data[...]."
            )
        buffer = value.data
        if not isinstance(buffer, FieldBuffer):
            raise TypeError(f"facade[{name!r}]: value.data does not satisfy FieldBuffer.")
        index = vault.names.get(name)
        if index is None:
            vault.add_slot(name, buffer, _meta_of(name, value))
            vault.note_out_of_band_mutation()
            return
        # Rebinding a slot to a different buffer: out-of-band mutation (§8.2).
        vault.buffers[index] = buffer
        vault._meta[index] = _meta_of(name, value)  # the façade is a vault friend
        vault.schema_hash = vault._compute_schema_hash()
        vault.note_out_of_band_mutation()
        self._cache.pop(name, None)

    def __delitem__(self, name: str) -> None:
        vault = self._vault
        if name == "time":
            raise KeyError("time cannot be deleted from a vault façade.")
        if name not in vault.names:
            raise KeyError(name)
        # Tombstone removal: the buffer list keeps its indices (plans hold them);
        # the name simply stops resolving. Out-of-band mutation by definition.
        del vault.names[name]
        vault.schema_hash = "deleted:" + vault.schema_hash
        vault.note_out_of_band_mutation()
        self._cache.pop(name, None)

    def __iter__(self) -> Iterator[str]:
        if self._vault.time is not None:
            yield "time"
        yield from self._vault.names

    def __len__(self) -> int:
        return len(self._vault.names) + (1 if self._vault.time is not None else 0)

    def __repr__(self) -> str:
        return f"VaultFacade({sorted(self._vault.names)})"
