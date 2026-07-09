"""Component ABI tests (SPEC S03 acceptance 2 + base machinery)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest
import xarray as xr

from symcon.core import (
    ComputeContext,
    DiagnosticComponent,
    IngressPlan,
    OutputSchema,
    PropertyDictError,
    make_dataarray,
)
from symcon.core.testing.toys import Damping, ImplicitDamping, Relaxation, WindSpeed, column_state

DT = timedelta(minutes=1)


def _out_field(name: str, units: str, shape: tuple[int, int]) -> xr.DataArray:
    return make_dataarray(
        np.zeros(shape), name=name, dims=("cell", "height"), units=units, location="cell"
    )


class TestOutPath:
    """Acceptance 2: out= writes in place; without out=, allocate_output once per field."""

    def test_out_pointer_identity_no_hidden_allocation(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        damping = Damping(tau=timedelta(minutes=10))
        out = {
            "upward_air_velocity": _out_field("upward_air_velocity", "m s-1", (2, 5)),
            "damping_rate": _out_field("damping_rate", "m s-2", (2, 5)),
        }
        out_buffers = {name: array.data for name, array in out.items()}

        diagnostics, new_state = damping(state, DT, out=out)

        # Pointer identity: the returned DataArrays *are* the caller's, over the
        # caller's buffers — no hidden allocation anywhere on the out= path.
        assert new_state["upward_air_velocity"] is out["upward_air_velocity"]
        assert diagnostics["damping_rate"] is out["damping_rate"]
        for name, array in (*diagnostics.items(), *new_state.items()):
            assert array.data is out_buffers[name]
        # ... and array_call wrote through them.
        expected = state["upward_air_velocity"].data * np.exp(-60.0 / 600.0)
        np.testing.assert_array_equal(new_state["upward_air_velocity"].data, expected)

    def test_out_path_never_calls_allocate_output(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        damping = Damping(tau=timedelta(minutes=10))

        def forbid(name: str, schema: OutputSchema, ctx: ComputeContext) -> Any:
            raise AssertionError(f"hidden allocation of {name!r}")

        damping.allocate_output = forbid  # type: ignore[method-assign]
        out = {
            "upward_air_velocity": _out_field("upward_air_velocity", "m s-1", (2, 5)),
            "damping_rate": _out_field("damping_rate", "m s-2", (2, 5)),
        }
        damping(state, DT, out=out)  # would raise if anything allocated

    def test_without_out_allocate_output_exactly_once_per_field(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        counts: dict[str, int] = {}

        class CountingDamping(Damping):
            def allocate_output(self, name: str, schema: OutputSchema, ctx: ComputeContext) -> Any:
                counts[name] = counts.get(name, 0) + 1
                return super().allocate_output(name, schema, ctx)

        damping = CountingDamping(tau=timedelta(minutes=10))
        damping(state, DT)
        assert counts == {"upward_air_velocity": 1, "damping_rate": 1}

    def test_partial_out_allocates_only_the_missing_field(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        counts: dict[str, int] = {}

        class CountingDamping(Damping):
            def allocate_output(self, name: str, schema: OutputSchema, ctx: ComputeContext) -> Any:
                counts[name] = counts.get(name, 0) + 1
                return super().allocate_output(name, schema, ctx)

        damping = CountingDamping(tau=timedelta(minutes=10))
        out = {"upward_air_velocity": _out_field("upward_air_velocity", "m s-1", (2, 5))}
        diagnostics, new_state = damping(state, DT, out=out)
        assert counts == {"damping_rate": 1}
        assert new_state["upward_air_velocity"] is out["upward_air_velocity"]
        assert diagnostics["damping_rate"] is not None

    def test_allocated_outputs_carry_the_contract_schema(self) -> None:
        state = column_state()
        damping = Damping(tau=timedelta(minutes=10))
        diagnostics, new_state = damping(state, DT)
        assert new_state["upward_air_velocity"].attrs["units"] == "m s-1"
        assert diagnostics["damping_rate"].attrs["units"] == "m s-2"
        assert new_state["upward_air_velocity"].dims == ("cell", "height")

    def test_unknown_out_names_are_rejected(self) -> None:
        state = column_state()
        damping = Damping(tau=timedelta(minutes=10))
        out = {"not_an_output": _out_field("not_an_output", "1", (1, 10))}
        with pytest.raises(ValueError, match="not_an_output"):
            damping(state, DT, out=out)

    def test_out_with_wrong_units_is_rejected_strictly(self) -> None:
        from symcon.core import ContractViolationError

        state = column_state()
        damping = Damping(tau=timedelta(minutes=10))
        out = {"upward_air_velocity": _out_field("upward_air_velocity", "km h-1", (1, 10))}
        with pytest.raises(ContractViolationError, match="upward_air_velocity"):
            damping(state, DT, out=out)


class TestKindContracts:
    def test_timestep_required_for_stepper_kind(self) -> None:
        damping = Damping(tau=timedelta(minutes=10))
        with pytest.raises(TypeError, match="requires a timestep"):
            damping(column_state(), None)  # type: ignore[arg-type]

    def test_timestep_required_for_implicit_tendency_kind(self) -> None:
        implicit = ImplicitDamping(tau=timedelta(minutes=10))
        with pytest.raises(TypeError, match="requires a timestep"):
            implicit(column_state(), None)  # type: ignore[arg-type]

    def test_diagnostic_kind_rejects_output_properties(self) -> None:
        with pytest.raises(PropertyDictError, match="output_properties"):

            class BadKind(DiagnosticComponent):
                output_properties: ClassVar[Mapping[str, Any]] = {
                    "air_temperature": {"dims": ["cell", "height"], "units": "K"}
                }

                def array_call(
                    self,
                    inputs: dict[str, Any],
                    outputs: dict[str, Any],
                    timestep: timedelta | None,
                ) -> None: ...

    def test_flat_out_namespace_rejects_cross_dict_collisions(self) -> None:
        from symcon.core import Stepper

        with pytest.raises(PropertyDictError, match="cannot disambiguate"):

            class Colliding(Stepper):
                diagnostic_properties: ClassVar[Mapping[str, Any]] = {
                    "upward_air_velocity": {"dims": ["cell", "height"], "units": "m s-1"}
                }
                output_properties: ClassVar[Mapping[str, Any]] = {
                    "upward_air_velocity": {"dims": ["cell", "height"], "units": "m s-1"}
                }

                def array_call(
                    self,
                    inputs: dict[str, Any],
                    outputs: dict[str, Any],
                    timestep: timedelta | None,
                ) -> None: ...

    def test_missing_input_field_names_field_and_component(self) -> None:
        state = column_state()
        del state["eastward_wind"]
        speed = WindSpeed()
        with pytest.raises(KeyError, match=r"eastward_wind.*WindSpeed"):
            speed(state)

    def test_restart_protocol_defaults(self) -> None:
        relax = Relaxation(tau=timedelta(minutes=30))
        assert relax.restart_state() == {}
        relax.load_restart_state({})  # no-op
        with pytest.raises(ValueError, match="Relaxation"):
            relax.load_restart_state({"stray": xr.DataArray(np.zeros(1))})
        assert dict(relax.functional_state()) == {}

    def test_str_lists_the_property_dicts(self) -> None:
        text = str(Relaxation(tau=timedelta(minutes=30)))
        assert "Relaxation" in text
        assert "air_temperature" in text


class TestNegotiationCache:
    """PLAN item 2: one negotiation per (instance, schema); renegotiate on change."""

    def test_ingress_plan_built_once_per_schema(self, monkeypatch: pytest.MonkeyPatch) -> None:
        state = column_state()
        speed = WindSpeed()
        calls: list[str] = []
        original = IngressPlan.build

        def counting(
            spec: Mapping[str, Any],
            schema: Any,
            *,
            component: str = "<component>",
        ) -> IngressPlan:
            calls.append(component)
            return original(spec, schema, component=component)

        monkeypatch.setattr(IngressPlan, "build", counting)
        speed(state)
        speed(state)
        speed(state)
        assert calls == ["WindSpeed"]

        # A schema change (extra field) is renegotiated, not served stale.
        state["extra"] = make_dataarray(
            np.zeros((1, 10)), name="extra", dims=("cell", "height"), units="1", location="cell"
        )
        speed(state)
        assert calls == ["WindSpeed", "WindSpeed"]

    def test_buffer_identity_is_stable_across_calls(self) -> None:
        state = column_state()
        captured: list[Any] = []

        class Capturing(WindSpeed):
            def array_call(
                self,
                inputs: dict[str, Any],
                outputs: dict[str, Any],
                timestep: timedelta | None,
            ) -> None:
                captured.append(inputs["eastward_wind"])
                super().array_call(inputs, outputs, timestep)

        speed = Capturing()
        speed(state)
        speed(state)
        assert captured[0] is captured[1] is state["eastward_wind"].data
