"""ConversionPlan executor tests (SPEC S03: non-strict ingress, negotiation-time only)."""

from __future__ import annotations

import numpy as np
import pytest

from symcon.core import (
    ConversionError,
    ConversionPlan,
    ConversionStep,
    DynamicChecker,
    apply_conversion_plan,
    convert_array,
    make_dataarray,
    parse_properties,
)
from symcon.core.testing import assert_allclose


def _state_with(units: str, dims: tuple[str, str] = ("cell", "height")) -> dict[str, object]:
    values = np.linspace(0.0, 9.0, 10, dtype=np.float64).reshape(2, 5)
    if dims == ("height", "cell"):
        values = values.T.copy()
    return {
        "air_temperature": make_dataarray(
            values, name="air_temperature", dims=dims, units=units, location="cell"
        )
    }


SPEC = parse_properties({"air_temperature": {"dims": ["cell", "height"], "units": "K"}})


def _plan_for(state: dict[str, object]) -> ConversionPlan:
    checker = DynamicChecker(SPEC, state, component="Toy", strict=False)
    return checker.plan


def test_units_conversion_with_offset() -> None:
    state = _state_with("degC")
    plan = _plan_for(state)
    converted = apply_conversion_plan(plan, state, component="Toy")
    original = state["air_temperature"]
    result = converted["air_temperature"]
    assert result.attrs["units"] == "K"  # type: ignore[union-attr]
    assert_allclose(
        result.data,  # type: ignore[union-attr]
        original.data + 273.15,  # type: ignore[union-attr]
        rtol=1e-12,
        names="air_temperature",
    )
    # the input state is untouched
    assert original.attrs["units"] == "degC"  # type: ignore[union-attr]


def test_transpose_conversion() -> None:
    state = _state_with("K", dims=("height", "cell"))
    plan = _plan_for(state)
    converted = apply_conversion_plan(plan, state, component="Toy")
    result = converted["air_temperature"]
    assert result.dims == ("cell", "height")  # type: ignore[union-attr]
    np.testing.assert_array_equal(
        result.data,  # type: ignore[union-attr]
        state["air_temperature"].data.T,  # type: ignore[union-attr]
    )


def test_cast_conversion() -> None:
    spec = parse_properties(
        {"air_temperature": {"dims": ["cell", "height"], "units": "K", "dtype": "float32"}}
    )
    state = _state_with("K")
    plan = DynamicChecker(spec, state, component="Toy", strict=False).plan
    converted = apply_conversion_plan(plan, state, component="Toy")
    assert converted["air_temperature"].data.dtype == np.float32  # type: ignore[union-attr]


def test_transfer_step_is_not_executed_at_t0() -> None:
    plan = ConversionPlan(
        steps=(
            ConversionStep(
                field="air_temperature", kind="transfer", source="(1, 0)", target="(2, 0)"
            ),
        )
    )
    with pytest.raises(ConversionError, match="transfer"):
        apply_conversion_plan(plan, _state_with("K"), component="Toy")


def test_plan_referencing_missing_field_raises() -> None:
    plan = ConversionPlan(
        steps=(ConversionStep(field="missing", kind="transpose", source="a,b", target="b,a"),)
    )
    with pytest.raises(ConversionError, match="missing"):
        apply_conversion_plan(plan, _state_with("K"), component="Toy")


def test_convert_array_identity_is_a_noop() -> None:
    values = np.ones(3)
    assert convert_array(values, "m s-1", "m s-1") is values


def test_convert_array_incompatible_units_raise() -> None:
    from symcon.core import UnitsError

    with pytest.raises(UnitsError, match="cannot convert"):
        convert_array(np.ones(3), "K", "m")
