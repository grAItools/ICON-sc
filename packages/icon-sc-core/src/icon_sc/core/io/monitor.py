"""In-memory monitor and shared monitor helpers (§7.4, SPEC S03).

:class:`MemoryMonitor` snapshots states for tests and interactive work (the
RCE-style acceptance loop verifies trajectories against closed forms through
it). Snapshots are **deep copies** of the selected DataArrays: T0 loops with
``out=`` mutate buffers in place, so a monitor holding references would watch
its history being rewritten.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import xarray as xr

from symcon.core.components.base import Monitor

__all__ = ["MemoryMonitor", "snapshot_state"]


def snapshot_state(
    state: Mapping[str, Any], *, variables: Iterable[str] | None = None
) -> dict[str, Any]:
    """A deep-copied snapshot of ``state`` (optionally restricted to ``variables``).

    The ``time`` entry is always kept; DataArray values are deep-copied, anything
    else (``time``) is carried as-is.
    """
    selected = None if variables is None else set(variables)
    snapshot: dict[str, Any] = {}
    for name, value in state.items():
        if selected is not None and name != "time" and name not in selected:
            continue
        snapshot[name] = value.copy(deep=True) if isinstance(value, xr.DataArray) else value
    return snapshot


class MemoryMonitor(Monitor):
    """Store deep-copied state snapshots in memory (frozen interface, SPEC S03)."""

    def __init__(self, *, variables: Iterable[str] | None = None, name: str | None = None) -> None:
        super().__init__(name=name)
        self._variables = None if variables is None else tuple(variables)
        self._snapshots: list[dict[str, Any]] = []

    @property
    def snapshots(self) -> tuple[dict[str, Any], ...]:
        """The stored snapshots, oldest first."""
        return tuple(self._snapshots)

    def store(self, state: Mapping[str, Any]) -> None:
        self._snapshots.append(snapshot_state(state, variables=self._variables))
