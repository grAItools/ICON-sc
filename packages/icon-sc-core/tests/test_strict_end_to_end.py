"""Strict mode end-to-end (SPEC S03 acceptance 4) + non-strict conversion path."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest

from icon_sc.core import (
    ComputeContext,
    ContractViolationError,
    DiagnosticComponent,
    PropertyDictError,
    make_dataarray,
)
from icon_sc.core.testing import assert_allclose
from icon_sc.core.testing.toys import Relaxation, WindSpeed, column_state


class TestStaticStrictness:
    def test_non_canonical_units_raise_at_class_creation(self) -> None:
        """A component declaring degC for air_temperature never constructs."""
        with pytest.raises(PropertyDictError) as excinfo:

            class BadUnits(DiagnosticComponent):
                input_properties: ClassVar[Mapping[str, Any]] = {
                    "air_temperature": {"dims": ["cell", "height"], "units": "degC"}
                }

                def array_call(
                    self,
                    inputs: dict[str, Any],
                    outputs: dict[str, Any],
                    timestep: timedelta | None,
                ) -> None: ...

        message = str(excinfo.value)
        assert "air_temperature" in message  # names the field
        assert "BadUnits" in message  # names the component
        assert "degC" in message

    def test_non_canonical_diagnostic_units_also_raise(self) -> None:
        with pytest.raises(PropertyDictError, match="air_pressure"):

            class BadDiagnostic(DiagnosticComponent):
                diagnostic_properties: ClassVar[Mapping[str, Any]] = {
                    "air_pressure": {"dims": ["cell", "height"], "units": "hPa"}
                }

                def array_call(
                    self,
                    inputs: dict[str, Any],
                    outputs: dict[str, Any],
                    timestep: timedelta | None,
                ) -> None: ...


class TestDynamicStrictness:
    def test_transposed_dims_raise_at_call_naming_field_and_component(self) -> None:
        state = column_state()
        transposed = state["eastward_wind"].data.T.copy()
        state["eastward_wind"] = make_dataarray(
            transposed,
            name="eastward_wind",
            dims=("height", "cell"),
            units="m s-1",
            location="cell",
        )
        speed = WindSpeed()  # default ctx: strict=True
        with pytest.raises(ContractViolationError) as excinfo:
            speed(state)
        message = str(excinfo.value)
        assert "eastward_wind" in message  # names the field
        assert "WindSpeed" in message  # names the component
        assert "dim_order" in message

    def test_wrong_units_raise_at_call(self) -> None:
        state = column_state()
        state["eastward_wind"].attrs["units"] = "km h-1"
        speed = WindSpeed()
        with pytest.raises(ContractViolationError, match=r"eastward_wind.*WindSpeed"):
            speed(state)


class TestNonStrictConversion:
    """strict=False executes the ConversionPlan instead of raising (T0 debug path)."""

    def test_transposed_dims_are_reconciled(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        expected = np.hypot(state["eastward_wind"].data, state["northward_wind"].data)
        state["eastward_wind"] = make_dataarray(
            state["eastward_wind"].data.T.copy(),
            name="eastward_wind",
            dims=("height", "cell"),
            units="m s-1",
            location="cell",
        )
        ctx = ComputeContext(backend="embedded", strict=False)
        speed = WindSpeed(ctx=ctx)
        diagnostics = speed(state)
        assert_allclose(diagnostics["wind_speed"].data, expected, rtol=0.0, names="wind_speed")
        # The input state itself is never mutated by the conversion.
        assert state["eastward_wind"].dims == ("height", "cell")

    def test_offset_units_are_converted(self) -> None:
        state = column_state()
        kelvin = state["air_temperature"].data.copy()
        state["air_temperature"] = make_dataarray(
            kelvin - 273.15,
            name="air_temperature",
            dims=("cell", "height"),
            units="degC",
            location="cell",
        )
        ctx = ComputeContext(backend="embedded", strict=False)
        relax = Relaxation(tau=timedelta(minutes=30), equilibrium=250.0, ctx=ctx)
        _, diagnostics = relax(state)
        assert_allclose(
            diagnostics["departure_from_equilibrium"].data,
            kelvin - 250.0,
            rtol=1e-12,
            names="departure_from_equilibrium",
        )

    def test_strict_default_still_raises_for_the_same_state(self) -> None:
        state = column_state()
        state["air_temperature"].attrs["units"] = "degC"
        relax = Relaxation(tau=timedelta(minutes=30))
        with pytest.raises(ContractViolationError, match=r"air_temperature.*Relaxation"):
            relax(state)
