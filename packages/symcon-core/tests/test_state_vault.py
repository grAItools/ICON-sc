"""StateVault + façade unit behavior (SPEC S05: vault, lazy views, epoch/generation)."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from symcon.core import StateVault
from symcon.core.state.dataarray import make_dataarray
from symcon.core.testing.toys import column_state


def test_from_state_adopts_buffers_zero_copy() -> None:
    state = column_state()
    vault = StateVault.from_state(state)
    for name, value in state.items():
        if name == "time":
            assert vault.time == value
            continue
        index = vault.names[name]
        assert vault.buffers[index] is value.data  # adopted, never copied


def test_from_state_rejects_non_dataarray_fields() -> None:
    state = column_state()
    state["bogus"] = [1, 2, 3]
    with pytest.raises(TypeError, match="bogus"):
        StateVault.from_state(state)


def test_facade_exposes_boundary_dataarrays_lazily() -> None:
    state = column_state()
    vault = StateVault.from_state(state)
    facade = vault.facade()
    assert vault.facade() is facade  # one façade per vault
    array = facade["air_temperature"]
    assert isinstance(array, xr.DataArray)
    assert array.data is vault.buffers[vault.names["air_temperature"]]
    assert array.attrs["units"] == "K"
    assert facade["air_temperature"] is array  # cached wrapper
    assert facade["time"] == state["time"]
    assert set(facade) == set(state)
    assert len(facade) == len(state)


def test_facade_cache_invalidates_on_generation_bump() -> None:
    vault = StateVault.from_state(column_state())
    facade = vault.facade()
    before = facade["air_temperature"]
    vault.note_swap()
    after = facade["air_temperature"]
    assert after is not before
    assert after.data is before.data  # same buffer, fresh wrapper


def test_facade_setitem_bumps_epoch_and_rebinds() -> None:
    vault = StateVault.from_state(column_state())
    facade = vault.facade()
    epoch = vault.epoch
    replacement = make_dataarray(
        np.zeros((1, 10)),
        name="air_temperature",
        dims=["cell", "height"],
        units="K",
        location="cell",
    )
    facade["air_temperature"] = replacement
    assert vault.epoch == epoch + 1
    assert facade["air_temperature"].data is replacement.data


def test_facade_setitem_rejects_non_dataarrays() -> None:
    vault = StateVault.from_state(column_state())
    facade = vault.facade()
    with pytest.raises(TypeError, match="boundary"):
        facade["air_temperature"] = np.zeros((1, 10))


def test_facade_delete_bumps_epoch_and_unresolves() -> None:
    vault = StateVault.from_state(column_state())
    facade = vault.facade()
    epoch = vault.epoch
    del facade["eastward_wind"]
    assert vault.epoch == epoch + 1
    with pytest.raises(KeyError):
        facade["eastward_wind"]


def test_schema_hash_tracks_slots() -> None:
    state = column_state()
    vault = StateVault.from_state(state)
    twin = StateVault.from_state(column_state())
    assert vault.schema_hash == twin.schema_hash  # content hash, not identity

    smaller = column_state()
    del smaller["eastward_wind"]
    assert StateVault.from_state(smaller).schema_hash != vault.schema_hash


def test_dim_sizes_consistency_checked() -> None:
    state = column_state()
    state["odd_field"] = make_dataarray(
        np.zeros((1, 7)),
        name="odd_field",
        dims=["cell", "height"],
        units="1",
        location="cell",
    )
    vault = StateVault.from_state(state)
    with pytest.raises(ValueError, match="height"):
        vault.dim_sizes()
