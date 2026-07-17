"""Property-dict schema validation (SPEC S02: validation of the dicts themselves)."""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.contracts.properties import (
    Differentiable,
    HaloPolicy,
    PropertyDictError,
    parse_properties,
)
from icon_sc.core.typing import Location

GOOD = {
    "air_temperature": {
        "dims": ["cell", "height"],
        "units": "K",
        "halo": "owned",
        "differentiable": "native",
        "params": ("autoconversion_threshold",),
    },
    "icon:normal_wind": {
        "dims": ["edge", "height"],
        "units": "m s-1",
        "halo": "required",
        "dtype": np.float64,
        "alias": "vn",
    },
    "scalar_knob": {"dims": [], "units": "1"},
}


def test_parse_normalizes_the_icon_sc_schema() -> None:
    specs = parse_properties(GOOD)
    assert tuple(specs) == tuple(GOOD)  # insertion order kept: it is argument order
    temp = specs["air_temperature"]
    assert temp.dims == ("cell", "height")
    assert temp.units == "K"
    assert temp.location is Location.CELL  # inferred from the horizontal dim
    assert temp.halo is HaloPolicy.OWNED
    assert temp.differentiable is Differentiable.NATIVE
    assert temp.params == ("autoconversion_threshold",)
    wind = specs["icon:normal_wind"]
    assert wind.location is Location.EDGE
    assert wind.dtype == np.dtype(np.float64)
    assert wind.alias == "vn"
    assert wind.differentiable is Differentiable.NONE  # default (§8.6)
    assert specs["scalar_knob"].location is Location.SCALAR


@pytest.mark.parametrize(
    ("entry", "match"),
    [
        ({"dims": ["cell"]}, "units"),
        ({"units": "K"}, "dims"),
        ({"dims": ["cell"], "units": 42}, "units must be a string"),
        ({"dims": "cell", "units": "K"}, "sequence of strings"),
        ({"dims": ["cell", "cell"], "units": "K"}, "repeated"),
        ({"dims": ["cell", "*"], "units": "K"}, "wildcard"),
        ({"dims": ["cell"], "units": "K", "halo": "sideways"}, "halo"),
        ({"dims": ["cell"], "units": "K", "location": "face"}, "location"),
        ({"dims": ["edge"], "units": "K", "location": "cell"}, "contradicts"),
        ({"dims": ["cell", "edge"], "units": "K"}, "horizontal"),
        ({"dims": ["cell"], "units": "K", "differentiable": "maybe"}, "differentiable"),
        ({"dims": ["cell"], "units": "K", "colour": "red"}, "unknown property keys"),
        ({"dims": ["cell"], "units": "K", "params": 3.0}, "params"),
        ("not-a-mapping", "expected a mapping"),
    ],
)
def test_malformed_entries_rejected(entry: object, match: str) -> None:
    with pytest.raises(PropertyDictError, match=match):
        parse_properties({"field_x": entry})


def test_alias_collision_rejected() -> None:
    with pytest.raises(PropertyDictError, match="alias"):
        parse_properties(
            {
                "a": {"dims": ["cell"], "units": "K", "alias": "t"},
                "b": {"dims": ["cell"], "units": "K", "alias": "t"},
            }
        )


def test_non_mapping_property_dict_rejected() -> None:
    with pytest.raises(PropertyDictError, match="mapping"):
        parse_properties(["air_temperature"])  # type: ignore[arg-type]
