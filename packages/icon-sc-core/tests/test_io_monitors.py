"""Monitor tests: MemoryMonitor snapshots, synchronous NetCDFMonitor (SPEC S03)."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from icon_sc.core import MemoryMonitor, NetCDFMonitor
from icon_sc.core.testing.toys import column_state


class TestMemoryMonitor:
    def test_snapshots_are_deep_copies(self) -> None:
        state = column_state()
        monitor = MemoryMonitor()
        monitor.store(state)
        before = state["air_temperature"].data.copy()
        state["air_temperature"].data[...] = -1.0  # in-place mutation after store
        np.testing.assert_array_equal(monitor.snapshots[0]["air_temperature"].data, before)

    def test_variable_selection_keeps_time(self) -> None:
        state = column_state()
        monitor = MemoryMonitor(variables=("air_temperature",))
        monitor.store(state)
        assert set(monitor.snapshots[0]) == {"time", "air_temperature"}


class TestNetCDFMonitor:
    def test_store_appends_time_records_to_one_file(self, tmp_path: Path) -> None:
        path = tmp_path / "toy.nc"
        monitor = NetCDFMonitor(path, variables=("air_temperature",))
        state = column_state()
        first = state["air_temperature"].data.copy()

        monitor.store(state)
        assert path.exists()  # synchronous: written on store

        state["air_temperature"].data[...] += 5.0
        state["time"] = state["time"] + timedelta(minutes=1)
        monitor.store(state)

        with xr.open_dataset(path) as dataset:
            assert dataset.sizes["time"] == 2
            assert set(dataset.data_vars) == {"air_temperature"}
            np.testing.assert_array_equal(dataset["air_temperature"].isel(time=0), first)
            np.testing.assert_array_equal(dataset["air_temperature"].isel(time=1), first + 5.0)
            assert dataset["air_temperature"].attrs["units"] == "K"
            assert dataset["air_temperature"].attrs["location"] == "cell"

    def test_provenance_stamp_in_global_attrs(self, tmp_path: Path) -> None:
        path = tmp_path / "prov.nc"
        monitor = NetCDFMonitor(path)
        monitor.store(column_state())
        with xr.open_dataset(path) as dataset:
            stamp = json.loads(dataset.attrs["icon_sc_provenance"])
        assert "packages" in stamp
        assert "icon-sc-core" in stamp["packages"]

    def test_missing_time_and_empty_selection_raise(self, tmp_path: Path) -> None:
        state = column_state()
        monitor = NetCDFMonitor(tmp_path / "bad.nc", variables=("nonexistent",))
        with pytest.raises(ValueError, match="nothing to store"):
            monitor.store(state)
        with pytest.raises(KeyError, match="time"):
            NetCDFMonitor(tmp_path / "bad2.nc").store({"air_temperature": state["air_temperature"]})
