"""Static/dynamic checker acceptance (SPEC S02 §2: strict-mode semantics)."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest

from symcon.core.contracts.checkers import (
    ContractViolationError,
    DynamicChecker,
    FieldSchema,
    StateSchema,
    StaticChecker,
)
from symcon.core.contracts.properties import PropertyDictError, parse_properties
from symcon.core.state.dataarray import make_dataarray
from symcon.core.typing import Location

CPU = (1, 0)  # kDLCPU per the DLPack device enum
CUDA = (2, 0)  # kDLCUDA


def make_state(dtype: Any = np.float64, dims: tuple[str, ...] = ("cell", "height")) -> dict:
    shape = tuple(3 if d in ("cell", "edge", "vertex") else 4 for d in dims)
    return {
        "air_temperature": make_dataarray(
            np.zeros(shape, dtype=dtype),
            name="air_temperature",
            dims=dims,
            units="K",
            location=dims[0] if dims and dims[0] in ("cell", "edge", "vertex") else "scalar",
        )
    }


SPEC = parse_properties({"air_temperature": {"dims": ["cell", "height"], "units": "K"}})


# --- StaticChecker: definition-only ---------------------------------------------------


def test_static_checker_accepts_a_valid_component_class() -> None:
    class Turbulence:
        input_properties: ClassVar[dict] = {
            "air_temperature": {"dims": ["cell", "height"], "units": "K", "halo": "owned"},
            "icon:normal_wind": {"dims": ["edge", "height"], "units": "m s-1"},
        }
        output_properties: ClassVar[dict] = {
            "icon:normal_wind": {
                "dims": ["edge", "height"],
                "units": "m s-1",
                "halo": "invalidated",
            },
        }

    checker = StaticChecker(Turbulence)
    assert set(checker.specs) == {"input_properties", "output_properties"}


def test_static_checker_names_component_and_field() -> None:
    class Broken:
        input_properties: ClassVar[dict] = {"air_temperature": {"dims": ["cell"]}}  # no units

    with pytest.raises(PropertyDictError, match=r"Broken.*air_temperature.*units"):
        StaticChecker(Broken)


def test_static_checker_rejects_non_canonical_units_for_registered_names() -> None:
    class Fahrenheit:
        input_properties: ClassVar[dict] = {
            "air_temperature": {"dims": ["cell", "height"], "units": "degC"}
        }

    with pytest.raises(PropertyDictError, match=r"Fahrenheit.*air_temperature.*no-op"):
        StaticChecker(Fahrenheit)


def test_static_checker_rejects_cross_dict_units_disagreement() -> None:
    class Inconsistent:
        input_properties: ClassVar[dict] = {"field_x": {"dims": ["cell"], "units": "kg"}}
        output_properties: ClassVar[dict] = {"field_x": {"dims": ["cell"], "units": "g"}}

    with pytest.raises(PropertyDictError, match=r"Inconsistent.*field_x.*units"):
        StaticChecker(Inconsistent)


def test_static_checker_rejects_cross_dict_dims_disagreement() -> None:
    class Reshaped:
        input_properties: ClassVar[dict] = {"field_x": {"dims": ["cell", "height"], "units": "1"}}
        diagnostic_properties: ClassVar[dict] = {"field_x": {"dims": ["cell"], "units": "1"}}

    with pytest.raises(PropertyDictError, match=r"Reshaped.*field_x.*dims"):
        StaticChecker(Reshaped)


def test_static_checker_allows_tendency_units() -> None:
    class Tendency:
        input_properties: ClassVar[dict] = {
            "air_temperature": {"dims": ["cell", "height"], "units": "K"}
        }
        tendency_properties: ClassVar[dict] = {
            "air_temperature": {"dims": ["cell", "height"], "units": "K s-1"},
        }

    StaticChecker(Tendency)  # tendency dicts are excluded from same-units cross-check


# --- DynamicChecker: definition x data, strict mode -----------------------------------


def test_strict_passes_on_matching_state() -> None:
    checker = DynamicChecker(SPEC, make_state(), component="Turbulence")
    assert not checker.violations
    assert not checker.plan


def test_strict_raises_on_unit_mismatch_naming_field_and_component() -> None:
    state = make_state()
    state["air_temperature"].attrs["units"] = "degC"
    with pytest.raises(ContractViolationError, match=r"units.*air_temperature.*Turbulence"):
        DynamicChecker(SPEC, state, component="Turbulence")


def test_strict_raises_on_dim_order_mismatch() -> None:
    state = {
        "air_temperature": make_dataarray(
            np.zeros((4, 3)),
            name="air_temperature",
            dims=("height", "cell"),
            units="K",
            location="cell",
        )
    }
    with pytest.raises(ContractViolationError, match=r"dim_order.*air_temperature.*Turbulence"):
        DynamicChecker(SPEC, state, component="Turbulence")


def test_strict_raises_on_dtype_mismatch() -> None:
    spec = parse_properties(
        {"air_temperature": {"dims": ["cell", "height"], "units": "K", "dtype": "float64"}}
    )
    with pytest.raises(ContractViolationError, match=r"dtype.*air_temperature.*Turbulence"):
        DynamicChecker(spec, make_state(dtype=np.float32), component="Turbulence")


def test_strict_raises_on_device_mismatch() -> None:
    # cupy-vs-numpy expressed through the portable DLPack device tuple: no GPU needed.
    schema = StateSchema(
        fields={
            "air_temperature": FieldSchema(
                dims=("cell", "height"),
                units="K",
                dtype=np.dtype(np.float64),
                device=CUDA,
            )
        }
    )
    with pytest.raises(ContractViolationError, match=r"device.*air_temperature.*Turbulence"):
        DynamicChecker(spec=SPEC, state=schema, component="Turbulence", device=CPU)


def test_device_mismatch_between_fields_of_one_state() -> None:
    spec = parse_properties(
        {
            "a": {"dims": ["cell"], "units": "1"},
            "b": {"dims": ["cell"], "units": "1"},
        }
    )
    schema = StateSchema(
        fields={
            "a": FieldSchema(("cell",), "1", np.dtype(np.float64), device=CPU),
            "b": FieldSchema(("cell",), "1", np.dtype(np.float64), device=CUDA),
        }
    )
    with pytest.raises(ContractViolationError, match=r"device.*'b'"):
        DynamicChecker(spec, schema, component="Mixed")


def test_missing_field_raises_even_non_strict() -> None:
    with pytest.raises(KeyError, match=r"air_temperature.*Turbulence"):
        DynamicChecker(SPEC, {}, component="Turbulence", strict=False)


def test_incompatible_dim_set_raises_even_non_strict() -> None:
    state = make_state(dims=("cell",))
    with pytest.raises(ContractViolationError, match="dims"):
        DynamicChecker(SPEC, state, component="Turbulence", strict=False)


def test_location_mismatch_raises_even_non_strict() -> None:
    schema = StateSchema(
        fields={
            "air_temperature": FieldSchema(
                dims=("cell", "height"),
                units="K",
                dtype=np.dtype(np.float64),
                device=CPU,
                location=Location.EDGE,
            )
        }
    )
    with pytest.raises(ContractViolationError, match="location"):
        DynamicChecker(SPEC, schema, component="Turbulence", strict=False)


# --- strict=False: conversion plan instead of exception --------------------------------


def test_non_strict_returns_conversion_plan() -> None:
    spec = parse_properties(
        {"air_temperature": {"dims": ["cell", "height"], "units": "K", "dtype": "float64"}}
    )
    state = {
        "air_temperature": make_dataarray(
            np.zeros((4, 3), dtype=np.float32),
            name="air_temperature",
            dims=("height", "cell"),
            units="degC",
            location="cell",
        )
    }
    checker = DynamicChecker(spec, state, component="Turbulence", strict=False)
    kinds = {(s.field, s.kind) for s in checker.plan.steps}
    assert kinds == {
        ("air_temperature", "convert_units"),
        ("air_temperature", "transpose"),
        ("air_temperature", "cast"),
    }
    units_step = next(s for s in checker.plan.steps if s.kind == "convert_units")
    assert (units_step.source, units_step.target) == ("degC", "K")


def test_non_strict_plan_is_empty_for_matching_state() -> None:
    checker = DynamicChecker(SPEC, make_state(), component="Turbulence", strict=False)
    assert not checker.plan
    assert checker.plan.steps == ()
