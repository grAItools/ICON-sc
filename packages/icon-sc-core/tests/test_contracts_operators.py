"""IngressPlan acceptance (SPEC S02 §3: build once, apply twice, zero copy)."""

from __future__ import annotations

import numpy as np
import pytest

from icon_sc.core.contracts.checkers import ContractViolationError, StateSchema
from icon_sc.core.contracts.operators import EgressPlan, IngressPlan
from icon_sc.core.contracts.properties import parse_properties
from icon_sc.core.state.dataarray import make_dataarray

SPEC = parse_properties(
    {
        "air_temperature": {"dims": ["cell", "height"], "units": "K"},
        "icon:normal_wind": {"dims": ["edge", "height"], "units": "m s-1"},
    }
)


def make_state() -> dict:
    return {
        "air_temperature": make_dataarray(
            np.random.default_rng(0).random((3, 4)),
            name="air_temperature",
            dims=("cell", "height"),
            units="K",
            location="cell",
        ),
        "icon:normal_wind": make_dataarray(
            np.zeros((5, 4)),
            name="icon:normal_wind",
            dims=("edge", "height"),
            units="m s-1",
            location="edge",
        ),
    }


def _pointer(buffer: np.ndarray) -> int:
    return int(buffer.__array_interface__["data"][0])


def test_built_once_applied_twice_identical_buffer_identities() -> None:
    state = make_state()
    plan = IngressPlan.build(SPEC, StateSchema.from_state(state), component="Turbulence")

    first = plan.apply(state)
    second = plan.apply(state)

    assert len(first) == len(second) == 2
    for buffer_a, buffer_b in zip(first, second, strict=True):
        assert buffer_a is buffer_b  # same Python object ...
        assert _pointer(buffer_a) == _pointer(buffer_b)  # ... and same memory
    # and they are the state's buffers, not copies:
    assert first[0] is state["air_temperature"].data
    assert _pointer(first[0]) == _pointer(state["air_temperature"].data)
    assert first[1] is state["icon:normal_wind"].data


def test_apply_order_is_property_dict_order() -> None:
    state = make_state()
    plan = IngressPlan.build(SPEC, state)
    assert plan.fields == ("air_temperature", "icon:normal_wind")
    buffers = plan.apply(state)
    assert buffers[0].shape == (3, 4)
    assert buffers[1].shape == (5, 4)


def test_build_accepts_raw_state_or_schema() -> None:
    state = make_state()
    from_state = IngressPlan.build(SPEC, state)
    from_schema = IngressPlan.build(SPEC, StateSchema.from_state(state))
    assert from_state.names == from_schema.names


def test_build_is_strict() -> None:
    state = make_state()
    state["air_temperature"].attrs["units"] = "degC"
    with pytest.raises(ContractViolationError, match="units"):
        IngressPlan.build(SPEC, state, component="Turbulence")


def test_alias_resolution() -> None:
    spec = parse_properties(
        {"air_temperature": {"dims": ["cell", "height"], "units": "K", "alias": "temp"}}
    )
    array = make_dataarray(
        np.zeros((3, 4)), name="temp", dims=("cell", "height"), units="K", location="cell"
    )
    state = {"temp": array}
    plan = IngressPlan.build(spec, state)
    assert plan.names == ("temp",)
    assert plan.apply(state)[0] is array.data


def test_egress_plan_resolves_output_buffers() -> None:
    output_spec = parse_properties(
        {"icon:normal_wind": {"dims": ["edge", "height"], "units": "m s-1"}}
    )
    state = make_state()
    plan = EgressPlan.build(output_spec, state, component="Turbulence")
    (out,) = plan.apply(state)
    assert out is state["icon:normal_wind"].data  # caller-provided output, zero-copy


def test_egress_build_enforces_device_expectation() -> None:
    """Regression (review round 1, m2): EgressPlan.build honours the device kwarg."""
    from icon_sc.core.contracts.checkers import FieldSchema

    cpu, cuda = (1, 0), (2, 0)
    spec = parse_properties({"air_temperature": {"dims": ["cell", "height"], "units": "K"}})
    schema = StateSchema(
        fields={
            "air_temperature": FieldSchema(
                dims=("cell", "height"), units="K", dtype=np.dtype(np.float64), device=cuda
            )
        }
    )
    with pytest.raises(ContractViolationError, match=r"device.*air_temperature"):
        EgressPlan.build(spec, schema, component="Turbulence", device=cpu)
    plan = EgressPlan.build(spec, schema, component="Turbulence", device=cuda)
    assert plan.fields == ("air_temperature",)
