"""Wrapper tests: CallingFrequency (SPEC S03 acceptance 3), Subcycle (acceptance 5),
ScalingWrapper."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from symcon.core import CallingFrequency, ScalingWrapper, Subcycle, make_dataarray
from symcon.core.testing.toys import Damping, Relaxation, column_state
from symcon.core.time import datetime

DT = timedelta(minutes=1)
TAU = timedelta(minutes=30)
EQUILIBRIUM = 250.0


def _euler_apply(state: dict[str, Any], tendencies: Mapping[str, Any], dt: timedelta) -> None:
    for name, tendency in tendencies.items():
        state[name].data[...] += dt.total_seconds() * tendency.data


def _run_wrapped(
    wrapper: CallingFrequency, state: dict[str, Any], n_steps: int
) -> list[np.ndarray]:
    """Drive the LFC pattern: tendencies held piecewise-constant between fires."""
    trajectory: list[np.ndarray] = []
    for _ in range(n_steps):
        tendencies, _ = wrapper(state, DT)
        _euler_apply(state, tendencies, DT)
        state["time"] = state["time"] + DT
        trajectory.append(state["air_temperature"].data.copy())
    return trajectory


def _hand_computation(initial: np.ndarray, n_steps: int) -> list[np.ndarray]:
    """The same 20 steps by hand: recompute the tendency every 3rd step only."""
    tau_s = TAU.total_seconds()
    dt_s = DT.total_seconds()
    temperature = initial.copy()
    cached: np.ndarray | None = None
    trajectory: list[np.ndarray] = []
    for step in range(n_steps):
        if step % 3 == 0:  # dt_proc = 3 dt: fires at steps 0, 3, 6, ...
            # identical op order to Relaxation.array_call
            cached = (temperature - EQUILIBRIUM) * (-1.0 / tau_s)
        assert cached is not None
        temperature = temperature + dt_s * cached
        trajectory.append(temperature.copy())
    return trajectory


class TestCallingFrequency:
    """Acceptance 3: piecewise-constant output over 20 steps with dt_proc = 3 dt."""

    def test_piecewise_constant_against_hand_computation(self) -> None:
        state = column_state()
        initial = state["air_temperature"].data.copy()
        wrapper = CallingFrequency(Relaxation(tau=TAU, equilibrium=EQUILIBRIUM), 3 * DT)
        trajectory = _run_wrapped(wrapper, state, 20)
        expected = _hand_computation(initial, 20)
        for step, (actual, desired) in enumerate(zip(trajectory, expected, strict=True)):
            np.testing.assert_array_equal(actual, desired, err_msg=f"step {step}")

    def test_component_fires_only_when_due(self) -> None:
        calls: list[Any] = []

        class Spy(Relaxation):
            def array_call(
                self,
                inputs: dict[str, Any],
                outputs: dict[str, Any],
                timestep: timedelta | None,
            ) -> None:
                calls.append(timestep)
                super().array_call(inputs, outputs, timestep)

        state = column_state()
        wrapper = CallingFrequency(Spy(tau=TAU), 3 * DT)
        _run_wrapped(wrapper, state, 20)
        assert len(calls) == 7  # steps 0, 3, 6, 9, 12, 15, 18

    def test_rounding_to_multiple_rule(self) -> None:
        wrapper = CallingFrequency(Relaxation(tau=TAU), timedelta(minutes=3, seconds=10))
        assert wrapper.period_for(DT) == timedelta(minutes=3)  # 190 s -> 3 x 60 s
        assert wrapper.period_for(None) == timedelta(minutes=3, seconds=10)
        # Below one multiple, clamp to one; halfway rounds up.
        assert CallingFrequency(Relaxation(tau=TAU), timedelta(seconds=10)).period_for(
            DT
        ) == timedelta(minutes=1)
        assert CallingFrequency(Relaxation(tau=TAU), timedelta(seconds=90)).period_for(
            DT
        ) == timedelta(minutes=2)

    def test_phase_survives_restart_round_trip_bit_exactly(self) -> None:
        state = column_state()
        wrapper = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        _run_wrapped(wrapper, state, 10)

        restart = wrapper.restart_state()
        twin = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        twin.load_restart_state(restart)
        round_trip = twin.restart_state()

        assert set(round_trip) == set(restart)
        phase_key = "calling_frequency/last_update_time"
        assert round_trip[phase_key].attrs["value"] == restart[phase_key].attrs["value"]
        assert round_trip[phase_key].attrs["value"] == datetime(2000, 1, 1, 0, 9)  # last fire
        for key, value in restart.items():
            if key == phase_key:
                continue
            np.testing.assert_array_equal(round_trip[key].data, value.data, err_msg=key)
            assert np.asarray(round_trip[key].data).dtype == np.asarray(value.data).dtype

        # ... and the continued trajectories are bit-identical.
        state_a = column_state()
        state_b = column_state()
        state_a["air_temperature"].data[...] = state["air_temperature"].data
        state_b["air_temperature"].data[...] = state["air_temperature"].data
        state_a["time"] = state_b["time"] = state["time"]
        continued_a = _run_wrapped(wrapper, state_a, 10)
        continued_b = _run_wrapped(twin, state_b, 10)
        for step, (a, b) in enumerate(zip(continued_a, continued_b, strict=True)):
            np.testing.assert_array_equal(a, b, err_msg=f"step {step}")

    def test_functional_state_declares_phase_and_cache(self) -> None:
        wrapper = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        schema = wrapper.functional_state()
        assert "calling_frequency/last_update_time" in schema
        assert "calling_frequency/cache/0/air_temperature" in schema
        assert "calling_frequency/cache/1/departure_from_equilibrium" in schema
        assert schema["calling_frequency/cache/0/air_temperature"].units == "K s-1"

    def test_cache_is_a_snapshot_not_a_reference(self) -> None:
        state = column_state()
        wrapper = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        tendencies, _ = wrapper(state, DT)
        first = tendencies["air_temperature"].data.copy()
        tendencies["air_temperature"].data[...] = 1e9  # caller mutates the fire output
        state["time"] = state["time"] + DT
        replayed, _ = wrapper(state, DT)  # not due: replay from cache
        np.testing.assert_array_equal(replayed["air_temperature"].data, first)

    def test_replay_fills_caller_out_buffers(self) -> None:
        state = column_state()
        wrapper = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        tendencies, _ = wrapper(state, DT)
        cached = tendencies["air_temperature"].data.copy()
        out = {
            "air_temperature": make_dataarray(
                np.zeros((1, 10)),
                name="air_temperature",
                dims=("cell", "height"),
                units="K s-1",
                location="cell",
            )
        }
        state["time"] = state["time"] + DT
        replayed, _ = wrapper(state, DT, out=out)
        assert replayed["air_temperature"] is out["air_temperature"]
        np.testing.assert_array_equal(out["air_temperature"].data, cached)

    def test_rejects_non_positive_dt(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            CallingFrequency(Relaxation(tau=TAU), timedelta(0))

    def test_delegates_properties_to_component(self) -> None:
        wrapper = CallingFrequency(Relaxation(tau=TAU), 3 * DT)
        assert "air_temperature" in wrapper.input_properties
        assert wrapper.output_dict_names == ("tendency_properties", "diagnostic_properties")


class TestSubcycle:
    """Acceptance 5: ratio_provider called once per outer step; integer honored."""

    def test_ratio_provider_called_once_per_outer_step_with_state(self) -> None:
        provided_states: list[Any] = []
        sub_calls: list[timedelta] = []

        class Spy(Damping):
            def array_call(
                self,
                inputs: dict[str, Any],
                outputs: dict[str, Any],
                timestep: timedelta | None,
            ) -> None:
                assert timestep is not None
                sub_calls.append(timestep)
                super().array_call(inputs, outputs, timestep)

        def provider(state: Mapping[str, Any]) -> int:
            provided_states.append(state["time"])
            return 4

        subcycle = Subcycle(Spy(tau=timedelta(minutes=10)), ratio_provider=provider)
        state = column_state()
        for _ in range(3):
            _, new_state = subcycle(state, DT)
            state.update(new_state)
            state["time"] = state["time"] + DT

        assert len(provided_states) == 3  # once per outer step
        assert provided_states == [
            datetime(2000, 1, 1),
            datetime(2000, 1, 1, 0, 1),
            datetime(2000, 1, 1, 0, 2),
        ]
        assert sub_calls == [DT / 4] * 12  # the integer is honored

    def test_result_matches_single_step_for_exact_stepper(self) -> None:
        # Exponential damping is exact: n substeps of dt/n == one step of dt.
        state = column_state()
        damping = Damping(tau=timedelta(minutes=10))
        subcycle = Subcycle(Damping(tau=timedelta(minutes=10)), n=5)
        _, direct = damping(state, DT)
        _, cycled = subcycle(state, DT)
        np.testing.assert_allclose(
            cycled["upward_air_velocity"].data,
            direct["upward_air_velocity"].data,
            rtol=1e-12,
        )

    def test_out_forwarded_to_final_substep_only(self) -> None:
        state = column_state(n_cell=2, n_height=5)
        subcycle = Subcycle(Damping(tau=timedelta(minutes=10)), n=3)
        out = {
            "upward_air_velocity": make_dataarray(
                np.zeros((2, 5)),
                name="upward_air_velocity",
                dims=("cell", "height"),
                units="m s-1",
                location="cell",
            ),
            "damping_rate": make_dataarray(
                np.zeros((2, 5)),
                name="damping_rate",
                dims=("cell", "height"),
                units="m s-2",
                location="cell",
            ),
        }
        _, new_state = subcycle(state, DT, out=out)
        assert new_state["upward_air_velocity"] is out["upward_air_velocity"]

    def test_exactly_one_of_n_and_ratio_provider(self) -> None:
        stepper = Damping(tau=timedelta(minutes=10))
        with pytest.raises(ValueError, match="exactly one"):
            Subcycle(stepper)
        with pytest.raises(ValueError, match="exactly one"):
            Subcycle(stepper, n=2, ratio_provider=lambda state: 2)
        with pytest.raises(ValueError, match=">= 1"):
            Subcycle(stepper, n=0)

    def test_bad_provider_value_is_rejected(self) -> None:
        subcycle = Subcycle(Damping(tau=timedelta(minutes=10)), ratio_provider=lambda state: 0)
        with pytest.raises(ValueError, match="ratio_provider returned 0"):
            subcycle(column_state(), DT)


class TestScalingWrapper:
    def test_input_scaling_uses_scaled_copies(self) -> None:
        state = column_state()
        wrapped = ScalingWrapper(
            Relaxation(tau=TAU, equilibrium=EQUILIBRIUM),
            input_scale_factors={"air_temperature": 2.0},
        )
        _, diagnostics = wrapped(state)
        expected = 2.0 * state["air_temperature"].data - EQUILIBRIUM
        np.testing.assert_allclose(
            diagnostics["departure_from_equilibrium"].data, expected, rtol=1e-12
        )
        # the state itself is untouched
        assert float(state["air_temperature"].data[0, 0]) == 250.0

    def test_tendency_scaling_in_place_preserves_out_identity(self) -> None:
        state = column_state()
        wrapped = ScalingWrapper(
            Relaxation(tau=TAU, equilibrium=EQUILIBRIUM),
            tendency_scale_factors={"air_temperature": 0.5},
        )
        out = {
            "air_temperature": make_dataarray(
                np.zeros((1, 10)),
                name="air_temperature",
                dims=("cell", "height"),
                units="K s-1",
                location="cell",
            )
        }
        unscaled, _ = Relaxation(tau=TAU, equilibrium=EQUILIBRIUM)(state)
        tendencies, _ = wrapped(state, out=out)
        assert tendencies["air_temperature"] is out["air_temperature"]
        np.testing.assert_allclose(
            tendencies["air_temperature"].data,
            0.5 * unscaled["air_temperature"].data,
            rtol=1e-12,
        )

    def test_output_scaling_on_stepper(self) -> None:
        state = column_state()
        wrapped = ScalingWrapper(
            Damping(tau=timedelta(minutes=10)),
            output_scale_factors={"upward_air_velocity": 3.0},
        )
        _, plain = Damping(tau=timedelta(minutes=10))(state, DT)
        _, scaled = wrapped(state, DT)
        np.testing.assert_allclose(
            scaled["upward_air_velocity"].data,
            3.0 * plain["upward_air_velocity"].data,
            rtol=1e-12,
        )

    def test_unknown_factor_names_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="not_a_field"):
            ScalingWrapper(Relaxation(tau=TAU), input_scale_factors={"not_a_field": 2.0})
        with pytest.raises(ValueError, match="output_scale_factors"):
            ScalingWrapper(Relaxation(tau=TAU), output_scale_factors={"air_temperature": 2.0})
