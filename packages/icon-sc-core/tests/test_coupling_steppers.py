"""Tendency-stepper registries (SPEC S04): factory, scheme orders, STS forcing.

PLAN item 2: each stepper's own measured order on ψ' = λψ (forward_euler → 1,
rk2 → 2, rk3ws → 3 and ssprk3 → 3 on a linear autonomous problem). PLAN pitfall
regression: the sequential-tendency stepper integrates from the step-initial ψⁿ
with the provisional forcing entering every evaluation — asserted against a
hand-computed Heun step, including the exact states the wrapped physics sees.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest

from symcon.core.components.base import TendencyComponent
from symcon.core.coupling import (
    ConcurrentCoupling,
    SequentialTendencyStepper,
    TendencyStepper,
)
from symcon.core.testing import assert_allclose, measure_order
from symcon.core.testing.toys import Relaxation, WindSpeed, column_state

_DIMS = ["cell", "height"]
T_FINAL = 1.024
DTS = [T_FINAL / 64, T_FINAL / 128, T_FINAL / 256, T_FINAL / 512, T_FINAL / 1024]
TAU = 0.4  # ψ' = -ψ/τ

SCHEME_ORDER = {"forward_euler": 1.0, "rk2": 2.0, "rk3ws": 3.0, "ssprk3": 3.0}


class RecordingRelaxation(Relaxation):
    """Relaxation recording the temperature values each evaluation sees."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.seen: list[np.ndarray] = []

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        self.seen.append(np.array(inputs["air_temperature"], copy=True))
        super().array_call(inputs, outputs, timestep)


def test_registries_hold_the_four_schemes() -> None:
    assert sorted(TendencyStepper.registry) == ["forward_euler", "rk2", "rk3ws", "ssprk3"]
    assert sorted(SequentialTendencyStepper.registry) == [
        "forward_euler",
        "rk2",
        "rk3ws",
        "ssprk3",
    ]


def test_factory_unknown_name_lists_known_names() -> None:
    with pytest.raises(KeyError, match="forward_euler"):
        TendencyStepper.factory("rk99", Relaxation(tau=timedelta(seconds=1)))


def test_non_tendency_coupling_rejects() -> None:
    with pytest.raises(TypeError, match="not a tendency provider"):
        TendencyStepper.factory("rk2", WindSpeed())


def test_forward_euler_hand_check() -> None:
    relaxation = Relaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    stepper = TendencyStepper.factory("forward_euler", relaxation)
    state = column_state()
    dt = timedelta(seconds=10)
    diagnostics, new_state = stepper(state, dt)
    t0 = state["air_temperature"].data
    assert_allclose(
        new_state["air_temperature"].data,
        t0 + 10.0 * (250.0 - t0) / 100.0,
        rtol=1e-14,
        names="forward_euler step",
    )
    # Diagnostics are those of the first (ψⁿ) evaluation.
    assert_allclose(
        diagnostics["departure_from_equilibrium"].data,
        t0 - 250.0,
        rtol=1e-14,
        names="ψⁿ diagnostics",
    )
    # The input state is untouched (out-of-place semantics).
    assert_allclose(state["air_temperature"].data, t0, rtol=0.0, names="input state")


@pytest.mark.parametrize("scheme", sorted(SCHEME_ORDER))
def test_stepper_order_on_linear_decay(scheme: str) -> None:
    """PLAN item 2: measured order of every registered scheme on ψ' = -ψ/τ."""

    def build(dt_seconds: float) -> np.ndarray:
        stepper = TendencyStepper.factory(
            scheme, Relaxation(tau=timedelta(seconds=TAU), equilibrium=0.0)
        )
        state = column_state()
        dt = timedelta(seconds=dt_seconds)
        for _ in range(round(T_FINAL / dt_seconds)):
            _, new_state = stepper(state, dt)
            state.update(new_state)
        return np.asarray(state["air_temperature"].data)

    exact = column_state()["air_temperature"].data * np.exp(-T_FINAL / TAU)
    fit = measure_order(build, DTS, exact)
    assert abs(fit.slope - SCHEME_ORDER[scheme]) <= 0.15, f"{scheme}: {fit}"


def test_bare_component_and_singleton_coupling_agree() -> None:
    state = column_state()
    dt = timedelta(seconds=30)
    _, direct = TendencyStepper.factory("rk2", Relaxation(tau=timedelta(seconds=100)))(state, dt)
    _, via_coupling = TendencyStepper.factory(
        "rk2", ConcurrentCoupling([Relaxation(tau=timedelta(seconds=100))])
    )(state, dt)
    assert_allclose(
        direct["air_temperature"].data,
        via_coupling["air_temperature"].data,
        rtol=0.0,
        names="bare vs coupling",
    )


def test_sequential_forward_euler_is_prv_plus_dt_p_at_psi_n() -> None:
    """E(ψⁿ, Δt; P + (ψ_prov-ψⁿ)/Δt) under forward Euler == ψ_prov + Δt·P(ψⁿ)."""
    relaxation = RecordingRelaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    stepper = SequentialTendencyStepper.factory("forward_euler", relaxation)
    state = column_state()
    prv = dict(state)
    prv["air_temperature"] = state["air_temperature"].copy(data=state["air_temperature"].data + 1.5)
    dt = timedelta(seconds=10)
    _, new_state = stepper(state, prv, dt)
    t0 = state["air_temperature"].data
    assert_allclose(
        new_state["air_temperature"].data,
        prv["air_temperature"].data + 10.0 * (250.0 - t0) / 100.0,
        rtol=1e-14,
        names="STS forward_euler",
    )
    # P was evaluated at the step-initial state, not at the provisional one.
    assert len(relaxation.seen) == 1
    assert_allclose(relaxation.seen[0], t0, rtol=0.0, names="evaluation state")


def test_sequential_rk2_hand_check_and_evaluation_points() -> None:
    """PLAN pitfall regression: hand-computed Heun STS step, forcing from ψⁿ.

    k₁ = P(ψⁿ) + G; ψ* = ψⁿ + Δt·k₁ = ψ_prov + Δt·P(ψⁿ); k₂ = P(ψ*) + G;
    ψ¹ = ψⁿ + Δt/2·(k₁ + k₂), with G = (ψ_prov - ψⁿ)/Δt. A wrong implementation
    that integrates from ψ_prov (or forces from the previous section's state)
    produces different evaluation points and a different result.
    """
    tau, eq, dt_s = 100.0, 250.0, 10.0
    relaxation = RecordingRelaxation(tau=timedelta(seconds=tau), equilibrium=eq)
    stepper = SequentialTendencyStepper.factory("rk2", relaxation)
    state = column_state()
    psi_n = state["air_temperature"].data.copy()
    prv_values = psi_n + 1.5
    prv = dict(state)
    prv["air_temperature"] = state["air_temperature"].copy(data=prv_values)

    _, new_state = stepper(state, prv, timedelta(seconds=dt_s))

    def p(psi: np.ndarray) -> np.ndarray:
        return (eq - psi) / tau

    forcing = (prv_values - psi_n) / dt_s
    k1 = p(psi_n) + forcing
    psi_star = psi_n + dt_s * k1
    k2 = p(psi_star) + forcing
    expected = psi_n + 0.5 * dt_s * (k1 + k2)
    assert_allclose(new_state["air_temperature"].data, expected, rtol=1e-14, names="STS rk2 step")
    # The physics saw exactly ψⁿ then ψ* = ψ_prov + Δt·P(ψⁿ).
    assert len(relaxation.seen) == 2
    assert_allclose(relaxation.seen[0], psi_n, rtol=0.0, names="stage-1 state")
    assert_allclose(relaxation.seen[1], psi_star, rtol=1e-14, names="stage-2 state")
    # ... and the wrong variant (no ψⁿ forcing, chained from ψ_prov) differs.
    wrong_k1 = p(prv_values)
    wrong = prv_values + 0.5 * dt_s * (wrong_k1 + p(prv_values + dt_s * wrong_k1))
    assert float(np.max(np.abs(expected - wrong))) > 1e-6


def test_sequential_stepper_missing_provisional_field_raises() -> None:
    stepper = SequentialTendencyStepper.factory("rk2", Relaxation(tau=timedelta(seconds=100)))
    state = column_state()
    prv = {key: value for key, value in state.items() if key != "air_temperature"}
    with pytest.raises(KeyError, match="provisional state"):
        stepper(state, prv, timedelta(seconds=10))


def test_output_units_derived_when_prognostic_not_an_input() -> None:
    class BlindForcing(TendencyComponent):
        """Tendency for a field it does not read (units must be derived)."""

        tendency_properties: ClassVar[dict[str, Any]] = {
            "air_temperature": {"dims": _DIMS, "units": "K s-1"},
        }

        def array_call(
            self,
            inputs: dict[str, Any],
            outputs: dict[str, Any],
            timestep: timedelta | None,
        ) -> None:
            del inputs, timestep
            outputs["air_temperature"][...] = 0.5

    stepper = TendencyStepper.factory("forward_euler", BlindForcing())
    spec = stepper.parsed_properties["output_properties"]["air_temperature"]
    assert spec.units == "K"


def test_out_buffer_identity() -> None:
    stepper = TendencyStepper.factory("rk2", Relaxation(tau=timedelta(seconds=100)))
    state = column_state()
    target = state["air_temperature"].copy(deep=True)
    _, new_state = stepper(state, timedelta(seconds=10), out={"air_temperature": target})
    assert new_state["air_temperature"] is target
    with pytest.raises(ValueError, match="not outputs of this stepper"):
        stepper(state, timedelta(seconds=10), out={"nope": target})


def test_non_positive_timestep_rejects() -> None:
    stepper = TendencyStepper.factory("rk2", Relaxation(tau=timedelta(seconds=100)))
    with pytest.raises(ValueError, match="timestep must be positive"):
        stepper(column_state(), timedelta(0))
