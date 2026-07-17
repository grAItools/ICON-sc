"""ConversionPlan executor: allocating non-strict ingress (SPEC S03, §2.4).

Strict mode turns any ingress that would allocate into an error; with
``strict=False`` the :class:`~symcon.core.contracts.checkers.DynamicChecker`
collects the needed conversions into a
:class:`~symcon.core.contracts.operators.ConversionPlan` instead, and this module
executes that plan — the debugging/education path of T0 (never the production
path, never the step path).

``apply_conversion_plan`` returns a **new** shallow-copied state whose offending
fields are replaced by converted copies; the input state is never mutated.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import xarray as xr

from symcon.core.contracts.operators import ConversionPlan, ConversionStep
from symcon.core.state.units import convert_array
from symcon.core.typing import HaloState, Location

__all__ = ["ConversionError", "apply_conversion_plan"]


class ConversionError(ValueError):
    """A conversion step cannot be executed (unsupported kind or bad data)."""


def _converted(array: xr.DataArray, step: ConversionStep) -> xr.DataArray:
    if step.kind == "convert_units":
        data = convert_array(array.data, step.source, step.target)
        out = array.copy(data=data)
        out.attrs = dict(array.attrs)
        out.attrs["units"] = step.target
        return out
    if step.kind == "transpose":
        return array.transpose(*step.target.split(","))
    if step.kind == "cast":
        out = array.copy(data=array.data.astype(step.target))
        out.attrs = dict(array.attrs)
        return out
    if step.kind == "transfer":
        raise ConversionError(
            f"field {step.field!r}: host<->device transfer ({step.source} -> "
            f"{step.target}) is not executed by the T0 conversion path; allocate the "
            f"state on the backend's device (or run strict mode to catch this early)."
        )
    raise ConversionError(f"field {step.field!r}: unknown conversion kind {step.kind!r}.")


def apply_conversion_plan(
    plan: ConversionPlan,
    state: Mapping[str, Any],
    *,
    component: str = "<component>",
) -> dict[str, Any]:
    """Execute ``plan`` against ``state`` (allocating; negotiation-time only).

    Steps are applied in plan order, several per field composing left to right.
    The returned dict shares every untouched entry with ``state``; converted
    fields are copies with their attrs schema (``units``/``location``/``halo``)
    preserved and updated. Errors name field and component.
    """
    converted: dict[str, Any] = dict(state)
    for step in plan.steps:
        if step.field not in converted:
            raise ConversionError(
                f"field {step.field!r} of component {component!r}: plan references a "
                f"field missing from the state."
            )
        array = converted[step.field]
        if not isinstance(array, xr.DataArray):
            raise ConversionError(
                f"field {step.field!r} of component {component!r}: expected a "
                f"DataArray, got {type(array).__name__}."
            )
        try:
            result = _converted(array, step)
        except ConversionError as exc:
            raise ConversionError(f"component {component!r}: {exc}") from None
        # xarray copies/transposes drop nothing, but be explicit about the schema.
        result.attrs.setdefault("location", array.attrs.get("location", Location.SCALAR))
        result.attrs.setdefault("halo", array.attrs.get("halo", HaloState.VALID))
        converted[step.field] = result
    return converted
