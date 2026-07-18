"""SPEC S03 acceptance 1: the sympl paper's Fig. 1/Fig. 2 pattern with two toy
processes on a 1-column state, matched against closed forms to 1e-12 (fp64)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from icon_sc.core import MemoryMonitor, timeloop
from icon_sc.core.testing import assert_allclose
from icon_sc.core.testing.toys import Damping, ImplicitDamping, Relaxation, WindSpeed, column_state

DT = timedelta(minutes=1)
TAU_RELAX = timedelta(minutes=30)
TAU_DAMP = timedelta(minutes=10)
EQUILIBRIUM = 250.0
N_STEPS = 20


def test_fig1_standalone_diagnostic_call() -> None:
    """Fig. 1: a DiagnosticComponent is usable interactively, outside any model."""
    state = column_state(n_cell=1, n_height=10)
    diagnostics = WindSpeed()(state)
    assert set(diagnostics) == {"wind_speed"}
    assert diagnostics["wind_speed"].attrs["units"] == "m s-1"
    assert_allclose(
        diagnostics["wind_speed"].data,
        np.hypot(state["eastward_wind"].data, state["northward_wind"].data),
        rtol=1e-12,
        names="wind_speed",
    )


def test_fig2_rce_style_loop_matches_closed_forms() -> None:
    """Fig. 2: legible run-script loop — diagnostics, tendencies (Euler), stepper,
    monitor — with both trajectories matching closed forms to 1e-12."""
    state = column_state(n_cell=1, n_height=10)
    initial_temperature = state["air_temperature"].data.copy()
    initial_velocity = state["upward_air_velocity"].data.copy()

    wind_speed = WindSpeed()
    relaxation = Relaxation(tau=TAU_RELAX, equilibrium=EQUILIBRIUM)
    damping = Damping(tau=TAU_DAMP)
    monitor = MemoryMonitor(variables=("air_temperature", "upward_air_velocity", "wind_speed"))

    def step(current: dict[str, Any], dt: timedelta) -> dict[str, Any]:
        current.update(wind_speed(current))  # diagnostics into the state
        tendencies, diagnostics = relaxation(current)
        current.update(diagnostics)
        for name, tendency in tendencies.items():  # forward-Euler apply
            current[name].data[...] += dt.total_seconds() * tendency.data
        diagnostics, new_state = damping(current, dt)  # stepper
        current.update(diagnostics)
        current.update(new_state)
        return current

    final = timeloop(state, step, timestep=DT, n_steps=N_STEPS, monitors=(monitor,))

    # Closed forms (module docstring of testing.toys):
    #   T_n = T_eq + (1 - dt/tau_r)^n (T_0 - T_eq)      (forward Euler)
    #   w_n = w_0 exp(-n dt/tau_d)                       (exact stepper)
    ratio = 1.0 - DT.total_seconds() / TAU_RELAX.total_seconds()
    factor = np.exp(-N_STEPS * DT.total_seconds() / TAU_DAMP.total_seconds())
    assert_allclose(
        final["air_temperature"].data,
        EQUILIBRIUM + ratio**N_STEPS * (initial_temperature - EQUILIBRIUM),
        rtol=1e-12,
        names="air_temperature",
    )
    assert_allclose(
        final["upward_air_velocity"].data,
        initial_velocity * factor,
        rtol=1e-12,
        names="upward_air_velocity",
    )

    # The monitor stored every step; intermediate records match the closed form too.
    assert len(monitor.snapshots) == N_STEPS
    for index, snapshot in enumerate(monitor.snapshots, start=1):
        assert_allclose(
            snapshot["air_temperature"].data,
            EQUILIBRIUM + ratio**index * (initial_temperature - EQUILIBRIUM),
            rtol=1e-12,
            names=f"air_temperature@{index}",
        )
    assert final["time"] == column_state()["time"] + N_STEPS * DT


def test_implicit_damping_is_exact_under_euler_apply() -> None:
    """The ImplicitTendencyComponent toy reproduces the exact stepper over one dt."""
    state = column_state()
    implicit = ImplicitDamping(tau=TAU_DAMP)
    tendencies, _ = implicit(state, DT)
    updated = state["upward_air_velocity"].data + DT.total_seconds() * (
        tendencies["upward_air_velocity"].data
    )
    _, stepped = Damping(tau=TAU_DAMP)(state, DT)
    assert_allclose(
        updated, stepped["upward_air_velocity"].data, rtol=1e-12, names="upward_air_velocity"
    )
