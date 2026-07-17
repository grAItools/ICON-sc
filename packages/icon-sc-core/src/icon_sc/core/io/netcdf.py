"""Synchronous single-rank NetCDF monitor (§7.4, SPEC S03).

xarray-based, one file, record appended on every ``store`` — semantics from
upstream sympl's ``NetCDFMonitor`` (see REFERENCES.lock), reimplemented over
xarray. The T0 implementation keeps all stored records in memory and rewrites
the whole file per ``store`` (synchronous, deliberately dumb — enough for the
SCM example); async writers and zarr are post-slice.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import xarray as xr

from symcon.core.components.base import Monitor
from symcon.core.config import provenance_stamp

__all__ = ["NetCDFMonitor"]


def _sanitized_attrs(attrs: Mapping[str, Any]) -> dict[str, Any]:
    """NetCDF attributes must be strings/numbers; enums become their values."""
    return {
        key: str(value) if isinstance(value, enum.Enum) else value for key, value in attrs.items()
    }


class NetCDFMonitor(Monitor):
    """Write stored states to one NetCDF file, appending a time record per store.

    ``variables`` restricts the stored set (default: every DataArray in the
    state). The provenance stamp (§5.3) is written into the global attributes as
    JSON under ``symcon_provenance``.
    """

    def __init__(
        self,
        filename: str | Path,
        *,
        variables: Iterable[str] | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._path = Path(filename)
        self._variables = None if variables is None else tuple(variables)
        self._records: list[xr.Dataset] = []
        self._provenance = json.dumps(provenance_stamp(), sort_keys=True, default=str)

    @property
    def path(self) -> Path:
        """The output file."""
        return self._path

    def store(self, state: Mapping[str, Any]) -> None:
        """Append the state as one time record and (re)write the file."""
        if "time" not in state:
            raise KeyError(f"monitor {self.name!r}: state has no 'time' entry.")
        arrays: dict[str, xr.DataArray] = {}
        for field_name, value in state.items():
            if field_name == "time" or not isinstance(value, xr.DataArray):
                continue
            if self._variables is not None and field_name not in self._variables:
                continue
            array = value.copy(deep=True)
            array.attrs = _sanitized_attrs(value.attrs)
            arrays[field_name] = array.expand_dims(time=[state["time"]])
        if not arrays:
            raise ValueError(
                f"monitor {self.name!r}: nothing to store "
                f"(variables={self._variables!r}, state keys={sorted(state)})."
            )
        self._records.append(xr.Dataset(arrays))
        dataset = (
            xr.concat(self._records, dim="time") if len(self._records) > 1 else self._records[0]
        )
        dataset.attrs["symcon_provenance"] = self._provenance
        dataset.to_netcdf(self._path, mode="w")
