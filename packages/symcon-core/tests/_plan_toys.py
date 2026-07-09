"""Shared composition builders for the S05 plan acceptance suite.

Everything is a zero-argument factory so T0 and T1 runs (and cross-process
plan-hash checks) always bind against freshly constructed, identical
compositions — wrappers carry runtime state (CallingFrequency phase), so
instances must never be shared between runs.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
from _coupling_toys import PlaneDamping, PlaneRelaxation, Rotation, plane_state

from symcon.core import (
    SSUS,
    CallingFrequency,
    ComputeContext,
    ConcurrentCoupling,
    ParallelSplitting,
    ScalingWrapper,
    SequentialTendencySplitting,
    SequentialUpdateSplitting,
    Subcycle,
    TendencyStepper,
)
from symcon.core.testing.toys import Damping, Relaxation, WindSpeed, column_state

__all__ = [
    "COLUMN_DT",
    "ODE_DT",
    "SCHEMES",
    "assert_states_bitwise_equal",
    "make_cf_multistage",
    "make_cf_subcycle_composite",
    "make_federation",
    "make_scaling_composite",
    "make_toy_loop",
    "make_twenty_component_loop",
    "ode_state",
    "run_tier",
    "toy_state",
]

#: The S04 ODE ladder's coarsest stable Δt (1.024 s / 128; exact microseconds).
ODE_DT = timedelta(milliseconds=8)
#: The S03 toy-loop Δt.
COLUMN_DT = timedelta(minutes=1)

SCHEMES = ("forward_euler", "rk2", "rk3ws", "ssprk3")

TAU_RELAX = timedelta(minutes=30)
TAU_DAMP = timedelta(minutes=10)


def toy_state() -> dict[str, Any]:
    return column_state()


def ode_state() -> dict[str, Any]:
    return plane_state(1.0, 0.5)


def make_toy_loop() -> Any:
    """The S03 toy loop as a composition: diagnostics + Euler tendencies + stepper."""
    return SequentialUpdateSplitting(
        [
            (ConcurrentCoupling([WindSpeed(), Relaxation(tau=TAU_RELAX)]), "forward_euler"),
            Damping(tau=TAU_DAMP),
        ]
    )


def make_federation(kind: str, scheme: str = "rk2") -> Any:
    """One S04 federation (or FC) over the ODE toy processes."""
    dynamics = Rotation()
    sections = [(PlaneRelaxation(), scheme), (PlaneDamping(), scheme)]
    if kind == "fc":
        coupling = ConcurrentCoupling([dynamics, PlaneRelaxation(), PlaneDamping()])
        return TendencyStepper.factory(scheme, coupling)
    if kind == "ps":
        return ParallelSplitting([(dynamics, scheme), *sections])
    if kind == "sts":
        return SequentialTendencySplitting([(dynamics, scheme), *sections])
    if kind == "sus":
        return SequentialUpdateSplitting([(dynamics, scheme), *sections])
    if kind == "ssus":
        return SSUS(sections, (dynamics, scheme), 0.5)
    if kind == "ssus03":
        return SSUS(sections, (dynamics, scheme), 0.3)
    raise ValueError(kind)


def make_cf_subcycle_composite() -> Any:
    """Acceptance 1(c): CallingFrequency (period 2Δt) + Subcycle (n=3) composite."""
    return SequentialUpdateSplitting(
        [
            (
                CallingFrequency(Relaxation(tau=TAU_RELAX), timedelta(minutes=2)),
                "forward_euler",
            ),
            Subcycle(Damping(tau=TAU_DAMP), n=3),
        ]
    )


def make_cf_multistage(scheme: str) -> Any:
    """Review round 1 (MINOR-1): one CF occurrence under a multi-stage scheme.

    The stepper re-evaluates its coupling once per stage; T0 replays the CF
    cache on stage > 0 (state time unchanged), so T1's stage-0-only firing must
    reproduce it bitwise.
    """
    return SequentialUpdateSplitting(
        [
            (
                ConcurrentCoupling(
                    [
                        CallingFrequency(Relaxation(tau=TAU_RELAX), timedelta(minutes=3)),
                        WindSpeed(),
                    ]
                ),
                scheme,
            ),
        ]
    )


def make_twenty_component_loop() -> Any:
    """20 toy components: 9 x (WindSpeed+Relaxation coupling, euler) + 2 steppers."""
    sections: list[Any] = []
    for index in range(9):
        coupling = ConcurrentCoupling(
            [
                WindSpeed(name=f"wind_speed_{index}"),
                Relaxation(tau=timedelta(minutes=30 + index), name=f"relaxation_{index}"),
            ]
        )
        sections.append((coupling, "forward_euler"))
    sections.append(Damping(tau=timedelta(minutes=10), name="damping_a"))
    sections.append(Damping(tau=timedelta(minutes=11), name="damping_b"))
    return SequentialUpdateSplitting(sections)


def make_scaling_composite() -> Any:
    """ScalingWrapper folding: scaled inputs and outputs around both toy kinds."""
    scaled_relaxation = ScalingWrapper(
        Relaxation(tau=TAU_RELAX),
        input_scale_factors={"air_temperature": 1.25},
        tendency_scale_factors={"air_temperature": 0.5},
        diagnostic_scale_factors={"departure_from_equilibrium": 2.0},
    )
    scaled_damping = ScalingWrapper(
        Damping(tau=TAU_DAMP),
        output_scale_factors={"upward_air_velocity": 0.75},
    )
    return SequentialUpdateSplitting(
        [
            (ConcurrentCoupling([scaled_relaxation]), "rk2"),
            scaled_damping,
        ]
    )


def run_tier(
    tier: str,
    make: Any,
    state: dict[str, Any],
    *,
    timestep: timedelta,
    n_steps: int,
) -> dict[str, Any]:
    """Run a freshly built composition under the given tier; return the final state."""
    ctx = ComputeContext("embedded", tier=tier)
    return ctx.timeloop(state, make(), timestep=timestep, n_steps=n_steps)


def assert_states_bitwise_equal(t0: dict[str, Any], t1: dict[str, Any]) -> None:
    """Exact (bitwise) equality over every field + the time entry (AGENTS.md rule)."""
    assert set(t0) == set(t1), f"key sets differ: {sorted(set(t0) ^ set(t1))}"
    assert t0["time"] == t1["time"]
    for name in sorted(t0):
        if name == "time":
            continue
        np.testing.assert_array_equal(
            t1[name].data,
            t0[name].data,
            err_msg=f"T1 diverges from T0 on {name!r}",
            strict=True,
        )
