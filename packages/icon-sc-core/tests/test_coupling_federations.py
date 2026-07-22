"""Federation semantics (SPEC S04): PS recombination, SUS chaining, STS forcing,
SSUS traversal/split, pre-stepper legality (acceptance 5), constraints (acceptance 3)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest

from icon_sc.core.components.base import Stepper
from icon_sc.core.components.wrappers import CallingFrequency
from icon_sc.core.coupling import (
    SSUS,
    CouplingConstraintError,
    CouplingConstraints,
    ParallelSplitting,
    SequentialTendencySplitting,
    SequentialUpdateSplitting,
)
from icon_sc.core.testing import assert_allclose
from icon_sc.core.testing.toys import Damping, Relaxation, WindSpeed, column_state

DT = timedelta(seconds=10)
_DIMS = ["cell", "height"]


class RecordingDamping(Damping):
    """Exact-damping Stepper recording (label, dt_seconds) per call."""

    def __init__(self, log: list[tuple[str, float]], label: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._log = log
        self._label = label

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        self._log.append((self._label, timestep.total_seconds()))
        super().array_call(inputs, outputs, timestep)


# -- ParallelSplitting ---------------------------------------------------------------


def test_ps_recombination_matches_eq_2_10d() -> None:
    """Two sections stepping the same field: ψⁿ⁺¹ = ψ₁ + ψ₂ - ψⁿ."""
    a = Relaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    b = Relaxation(tau=timedelta(seconds=50), equilibrium=200.0)
    ps = ParallelSplitting([(a, "forward_euler"), (b, "forward_euler")])
    state = column_state()
    t0 = state["air_temperature"].data.copy()
    _, new_state = ps(state, DT)
    psi_1 = t0 + 10.0 * (250.0 - t0) / 100.0
    psi_2 = t0 + 10.0 * (200.0 - t0) / 50.0
    assert_allclose(
        new_state["air_temperature"].data,
        psi_1 + psi_2 - t0,
        rtol=1e-14,
        names="PS recombination",
    )
    # ψⁿ untouched.
    assert_allclose(state["air_temperature"].data, t0, rtol=0.0, names="input state")


def test_ps_sections_all_see_psi_n() -> None:
    """PS sections are independent: both evaluate their physics at ψⁿ."""
    seen: list[np.ndarray] = []

    class Probe(Relaxation):
        def array_call(
            self,
            inputs: dict[str, Any],
            outputs: dict[str, Any],
            timestep: timedelta | None,
        ) -> None:
            seen.append(np.array(inputs["air_temperature"], copy=True))
            super().array_call(inputs, outputs, timestep)

    ps = ParallelSplitting(
        [
            (Probe(tau=timedelta(seconds=100)), "forward_euler"),
            (Probe(tau=timedelta(seconds=50)), "forward_euler"),
        ]
    )
    state = column_state()
    ps(state, DT)
    assert len(seen) == 2
    assert_allclose(seen[0], state["air_temperature"].data, rtol=0.0, names="section 1")
    assert_allclose(seen[1], state["air_temperature"].data, rtol=0.0, names="section 2")


# -- SequentialUpdateSplitting ---------------------------------------------------------


def test_sus_chains_sections_in_place() -> None:
    """Bare Stepper then (TendencyComponent, name): the second sees the first's state."""
    damping = Damping(tau=timedelta(seconds=100))
    relaxation = Relaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    sus = SequentialUpdateSplitting([damping, (relaxation, "forward_euler")])
    state = column_state()
    w0 = state["upward_air_velocity"].data.copy()
    t0 = state["air_temperature"].data.copy()
    diagnostics, new_state = sus(state, DT)
    assert_allclose(
        new_state["upward_air_velocity"].data,
        w0 * np.exp(-10.0 / 100.0),
        rtol=1e-14,
        names="SUS damping",
    )
    assert_allclose(
        new_state["air_temperature"].data,
        t0 + 10.0 * (250.0 - t0) / 100.0,
        rtol=1e-14,
        names="SUS relaxation",
    )
    assert "damping_rate" in diagnostics


def test_sus_second_section_sees_first_sections_update() -> None:
    """Two dampings on the same field: SUS composes them multiplicatively."""
    sus = SequentialUpdateSplitting(
        [Damping(tau=timedelta(seconds=100)), Damping(tau=timedelta(seconds=50))]
    )
    state = column_state()
    w0 = state["upward_air_velocity"].data.copy()
    _, new_state = sus(state, DT)
    assert_allclose(
        new_state["upward_air_velocity"].data,
        w0 * np.exp(-10.0 / 100.0) * np.exp(-10.0 / 50.0),
        rtol=1e-14,
        names="SUS chained damping",
    )


# -- SequentialTendencySplitting -------------------------------------------------------


def test_sts_hand_check_matches_eq_2_11() -> None:
    """Two relaxations, Euler then Heun; hand-computed per eq. (2.11)."""
    tau_a, eq_a, tau_b, eq_b, dt_s = 80.0, 260.0, 40.0, 240.0, 10.0
    sts = SequentialTendencySplitting(
        [
            (Relaxation(tau=timedelta(seconds=tau_a), equilibrium=eq_a), "forward_euler"),
            (Relaxation(tau=timedelta(seconds=tau_b), equilibrium=eq_b), "rk2"),
        ]
    )
    state = column_state()
    psi_n = state["air_temperature"].data.copy()
    _, new_state = sts(state, DT)

    p_a = (eq_a - psi_n) / tau_a
    psi_0 = psi_n + dt_s * p_a  # eq. (2.11a), forward Euler

    def p_b(psi: np.ndarray) -> np.ndarray:
        return (eq_b - psi) / tau_b

    forcing = (psi_0 - psi_n) / dt_s  # == p_a: the ψⁿ-based forcing
    k1 = p_b(psi_n) + forcing
    psi_star = psi_n + dt_s * k1
    k2 = p_b(psi_star) + forcing
    expected = psi_n + 0.5 * dt_s * (k1 + k2)  # eq. (2.11b), Heun
    assert_allclose(new_state["air_temperature"].data, expected, rtol=1e-14, names="STS step")


def test_sts_rejects_bare_stepper_past_position_zero() -> None:
    damping = Damping(tau=timedelta(seconds=100))
    relaxation = Relaxation(tau=timedelta(seconds=100))
    # Position 0 is fine (eq. 2.11a is a plain step) ...
    SequentialTendencySplitting([damping, (relaxation, "rk2")])
    # ... later positions need the two-state signature.
    with pytest.raises(TypeError, match=r"bare\s+Stepper"):
        SequentialTendencySplitting([(relaxation, "rk2"), damping])


# -- SSUS ------------------------------------------------------------------------------


def test_ssus_traversal_and_split_match_eq_2_13() -> None:
    """Reverse pass over λΔt, core over Δt, forward pass over (1-λ)Δt."""
    log: list[tuple[str, float]] = []
    a = RecordingDamping(log, "A", tau=timedelta(seconds=100))
    b = RecordingDamping(log, "B", tau=timedelta(seconds=200))
    core = RecordingDamping(log, "core", tau=timedelta(seconds=50))
    ssus = SSUS([a, b], core, 0.3)
    ssus(column_state(), DT)
    assert log == [
        ("B", 3.0),  # (2.13a) reverse order, λΔt
        ("A", 3.0),  # (2.13b)
        ("core", 10.0),  # (2.13c) full Δt
        ("A", 7.0),  # (2.13d) forward order, (1-λ)Δt
        ("B", 7.0),  # (2.13e)
    ]


def test_ssus_strang_on_commuting_processes_is_exact() -> None:
    """Exact-damping sections commute: SSUS composes the exact flows."""
    a = Damping(tau=timedelta(seconds=100))
    core = Damping(tau=timedelta(seconds=50))
    ssus = SSUS([a], core, 0.5)
    state = column_state()
    w0 = state["upward_air_velocity"].data.copy()
    _, new_state = ssus(state, DT)
    assert_allclose(
        new_state["upward_air_velocity"].data,
        w0 * np.exp(-5.0 / 100.0) * np.exp(-10.0 / 50.0) * np.exp(-5.0 / 100.0),
        rtol=1e-14,
        names="Strang exact composition",
    )


def test_ssus_pre_steppers_differ_from_post_steppers() -> None:
    """Acceptance 5: Eₗ* ≠ Eₗ is legal and changes the trajectory."""
    relaxation = Relaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    core = Damping(tau=timedelta(seconds=50))
    mixed = SSUS([(relaxation, "rk2")], core, 0.5, pre_steppers=["forward_euler"])
    same = SSUS([(relaxation, "rk2")], core, 0.5)
    state = column_state()
    _, out_mixed = mixed(state, DT)
    _, out_same = same(state, DT)
    assert np.all(np.isfinite(out_mixed["air_temperature"].data))
    assert (
        float(np.max(np.abs(out_mixed["air_temperature"].data - out_same["air_temperature"].data)))
        > 0.0
    )


def test_ssus_validation_errors() -> None:
    relaxation = Relaxation(tau=timedelta(seconds=100))
    damping = Damping(tau=timedelta(seconds=100))
    core = Damping(tau=timedelta(seconds=50))
    with pytest.raises(ValueError, match="lam must be in"):
        SSUS([(relaxation, "rk2")], core, 1.0)
    with pytest.raises(ValueError, match="pre_steppers has"):
        SSUS([(relaxation, "rk2")], core, 0.5, pre_steppers=["rk2", "rk2"])
    with pytest.raises(ValueError, match="its own numerics"):
        SSUS([damping], core, 0.5, pre_steppers=["rk2"])
    with pytest.raises(ValueError, match="at least one section"):
        SSUS([], core, 0.5)


def test_federations_compose() -> None:
    """A federation is a component: a SUS can be the SSUS core."""
    inner = SequentialUpdateSplitting([Damping(tau=timedelta(seconds=50))])
    ssus = SSUS([(Relaxation(tau=timedelta(seconds=100)), "rk2")], inner, 0.5)
    _, new_state = ssus(column_state(), DT)
    assert set(new_state) == {"air_temperature", "upward_air_velocity"}
    assert "air_temperature" in ssus.parsed_properties["output_properties"]


# -- constraints at construction (acceptance 3) ---------------------------------------


class Convection(Relaxation):
    """Named toy carrying no constraints."""


class Microphysics(Relaxation):
    """Toy declaring it must run after convection."""

    coupling_constraints: ClassVar[CouplingConstraints] = CouplingConstraints(
        must_follow=("Convection",)
    )


def test_sus_honors_must_follow() -> None:
    convection = Convection(tau=timedelta(seconds=100))
    microphysics = Microphysics(tau=timedelta(seconds=50))
    # Legal order constructs...
    SequentialUpdateSplitting([(convection, "rk2"), (microphysics, "rk2")])
    # ... the violating order raises with both component names (acceptance 3).
    with pytest.raises(CouplingConstraintError) as excinfo:
        SequentialUpdateSplitting([(microphysics, "rk2"), (convection, "rk2")])
    message = str(excinfo.value)
    assert "Microphysics" in message
    assert "Convection" in message


def test_must_follow_binds_only_when_present() -> None:
    microphysics = Microphysics(tau=timedelta(seconds=50))
    SequentialUpdateSplitting([(microphysics, "rk2")])  # no Convection: fine


def test_constraints_bind_through_wrappers() -> None:
    """Review round 1 (MINOR 1): wrapping must not shed constraints in either direction.

    ``CallingFrequency`` renames its component; constraint matching unwraps the
    wrapper chain, so constraints declared *against* a wrapped component (the
    S09/S12 pattern: CallingFrequency-wrapped slow physics) still bind — and a
    wrapped *constrained* component still carries its own constraints.
    """
    period = timedelta(seconds=60)

    # Direction 1: the referenced component enters wrapped.
    wrapped_convection = CallingFrequency(Convection(tau=timedelta(seconds=100)), period)
    microphysics = Microphysics(tau=timedelta(seconds=50))
    with pytest.raises(CouplingConstraintError) as excinfo:
        SequentialUpdateSplitting([(microphysics, "rk2"), (wrapped_convection, "rk2")])
    message = str(excinfo.value)
    assert "Microphysics" in message
    assert "Convection" in message
    # Correct order constructs (doubly wrapped, for the chain walk).
    SequentialUpdateSplitting(
        [
            (CallingFrequency(wrapped_convection, period), "rk2"),
            (microphysics, "rk2"),
        ]
    )

    # Direction 2: the constrained component enters wrapped.
    wrapped_microphysics = CallingFrequency(Microphysics(tau=timedelta(seconds=50)), period)
    with pytest.raises(CouplingConstraintError) as excinfo:
        SequentialUpdateSplitting(
            [(wrapped_microphysics, "rk2"), (Convection(tau=timedelta(seconds=100)), "rk2")]
        )
    message = str(excinfo.value)
    assert "Microphysics" in message
    assert "Convection" in message
    SequentialUpdateSplitting(
        [(Convection(tau=timedelta(seconds=100)), "rk2"), (wrapped_microphysics, "rk2")]
    )


def test_admissible_operators_checked_per_federation() -> None:
    class SUSOnly(Relaxation):
        coupling_constraints: ClassVar[CouplingConstraints] = CouplingConstraints(
            admissible_operators=("sequential_update_splitting",)
        )

    component = SUSOnly(tau=timedelta(seconds=100))
    SequentialUpdateSplitting([(component, "rk2")])  # admitted
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        ParallelSplitting([(component, "rk2")])
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        SSUS([(component, "rk2")], Damping(tau=timedelta(seconds=50)), 0.5)


# -- component surface -----------------------------------------------------------------


def test_bad_section_specs_reject() -> None:
    with pytest.raises(TypeError, match="neither a Stepper-shaped component"):
        SequentialUpdateSplitting([WindSpeed()])
    with pytest.raises(TypeError, match=r"must be \(component, stepper_name\)"):
        SequentialUpdateSplitting([(Relaxation(tau=timedelta(seconds=1)), "rk2", 3)])
    with pytest.raises(TypeError, match="not a tendency provider"):
        SequentialUpdateSplitting([(WindSpeed(), "rk2")])


def test_federation_out_buffers() -> None:
    sus = SequentialUpdateSplitting([Damping(tau=timedelta(seconds=100))])
    state = column_state()
    target = state["upward_air_velocity"].copy(deep=True)
    _, new_state = sus(state, DT, out={"upward_air_velocity": target})
    assert new_state["upward_air_velocity"] is target
    with pytest.raises(ValueError, match="not outputs of this federation"):
        sus(state, DT, out={"nope": target})


class _StatefulStepper(Stepper):
    """Stepper with restart carry, for the delegation round trip."""

    input_properties: ClassVar[dict[str, Any]] = {
        "upward_air_velocity": {"dims": _DIMS, "units": "m s-1"},
    }
    output_properties: ClassVar[dict[str, Any]] = {
        "upward_air_velocity": {"dims": _DIMS, "units": "m s-1"},
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.calls = 0

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        self.calls += 1
        outputs["upward_air_velocity"][...] = inputs["upward_air_velocity"]

    def restart_state(self) -> dict[str, Any]:
        import xarray as xr

        return {"calls": xr.DataArray(np.zeros(()), attrs={"value": self.calls})}

    def load_restart_state(self, restart: Any) -> None:
        self.calls = int(restart["calls"].attrs["value"])


def test_federation_restart_delegation() -> None:
    stateful = _StatefulStepper()
    sus = SequentialUpdateSplitting([stateful])
    sus(column_state(), DT)
    saved = sus.restart_state()
    assert set(saved) == {"section0/calls"}
    fresh_inner = _StatefulStepper()
    fresh = SequentialUpdateSplitting([fresh_inner])
    fresh.load_restart_state(saved)
    assert fresh_inner.calls == 1
    with pytest.raises(ValueError, match="unknown restart key"):
        fresh.load_restart_state({"bogus/x": saved["section0/calls"]})
