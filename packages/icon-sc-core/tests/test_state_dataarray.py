"""Boundary DataArray construction acceptance (SPEC S02 §1: attrs round-trip)."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.typing import HaloState, Location

_UNITS = ["K", "Pa", "m s-1", "kg m-3", "1"]
_VERTICAL = [(), ("height",), ("height_interface",)]


@st.composite
def dataarray_cases(draw: st.DrawFn) -> dict[str, object]:
    location = draw(st.sampled_from([Location.CELL, Location.EDGE, Location.VERTEX]))
    vertical = draw(st.sampled_from(_VERTICAL))
    dims = (location.value, *vertical)
    shape = tuple(draw(st.integers(min_value=1, max_value=5)) for _ in dims)
    dtype = draw(st.sampled_from([np.float32, np.float64]))
    return {
        "name": draw(st.sampled_from(["air_temperature", "icon:normal_wind", "field_x"])),
        "dims": dims,
        "shape": shape,
        "dtype": dtype,
        "units": draw(st.sampled_from(_UNITS)),
        "location": location,
        "grid_uuid": draw(st.one_of(st.none(), st.uuids().map(str))),
    }


@given(dataarray_cases())
def test_attrs_round_trip(case: dict[str, object]) -> None:
    buffer = np.zeros(case["shape"], dtype=case["dtype"])  # type: ignore[arg-type]
    array = make_dataarray(
        buffer,
        name=case["name"],  # type: ignore[arg-type]
        dims=case["dims"],  # type: ignore[arg-type]
        units=case["units"],  # type: ignore[arg-type]
        location=case["location"],  # type: ignore[arg-type]
        grid_uuid=case["grid_uuid"],  # type: ignore[arg-type]
    )
    # Everything stamped survives, exactly (§2.2 attrs table).
    assert array.name == case["name"]
    assert array.dims == case["dims"]
    assert array.attrs["units"] == case["units"]
    assert array.attrs["location"] is case["location"]
    assert array.attrs["halo"] is HaloState.VALID
    if case["grid_uuid"] is None:
        assert "grid_uuid" not in array.attrs
    else:
        assert array.attrs["grid_uuid"] == case["grid_uuid"]
    # Zero-copy: the DataArray wraps the buffer object itself.
    assert array.data is buffer


def test_location_accepts_plain_strings() -> None:
    array = make_dataarray(
        np.zeros((3, 2)), name="f", dims=("cell", "height"), units="K", location="cell"
    )
    assert array.attrs["location"] is Location.CELL


def test_scalar_location() -> None:
    array = make_dataarray(np.full((), 3.0), name="c", dims=(), units="1", location=Location.SCALAR)
    assert array.shape == ()
    assert array.attrs["location"] is Location.SCALAR


def test_rank_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="rank"):
        make_dataarray(np.zeros((3, 2)), name="f", dims=("cell",), units="K", location="cell")


def test_contradicting_horizontal_dim_rejected() -> None:
    with pytest.raises(ValueError, match="contradicts"):
        make_dataarray(np.zeros((3,)), name="f", dims=("edge",), units="K", location="cell")


def test_mesh_location_without_horizontal_dim_rejected() -> None:
    with pytest.raises(ValueError, match="horizontal"):
        make_dataarray(np.zeros((3,)), name="f", dims=("height",), units="K", location="cell")


def test_non_buffer_rejected() -> None:
    with pytest.raises(TypeError, match="FieldBuffer"):
        make_dataarray(
            [1.0, 2.0],  # type: ignore[arg-type]
            name="f",
            dims=("cell",),
            units="K",
            location="cell",
        )
