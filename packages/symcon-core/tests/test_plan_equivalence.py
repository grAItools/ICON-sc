"""SPEC S05 acceptance 1: bitwise T0 ≡ T1 equivalence in fp64 over 100 steps.

(a) the S03 toy loop; (b) every S04 federation over the toy processes, all four
schemes; (c) a CallingFrequency + Subcycle composite. Same kernels, same order
⇒ bitwise is required: every comparison is exact (``assert_array_equal``),
never ``allclose`` (AGENTS.md: no tolerance creep, no reduction-order changes).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import pytest
from _plan_toys import (
    COLUMN_DT,
    ODE_DT,
    SCHEMES,
    assert_states_bitwise_equal,
    make_cf_subcycle_composite,
    make_federation,
    make_scaling_composite,
    make_toy_loop,
    ode_state,
    run_tier,
    toy_state,
)

from symcon.core import ComputeContext
from symcon.core.components.dycore import DynamicalCore
from symcon.core.state.dataarray import make_dataarray

N_STEPS = 100


def test_toy_loop_t0_t1_bitwise() -> None:
    """(a) The S03 toy loop composition: 100 steps, every field bit-identical."""
    t0 = run_tier("interpret", make_toy_loop, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS)
    t1 = run_tier("plan", make_toy_loop, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS)
    assert_states_bitwise_equal(t0, t1)


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("kind", ["fc", "ps", "sts", "sus", "ssus", "ssus03"])
def test_federations_t0_t1_bitwise(kind: str, scheme: str) -> None:
    """(b) Every S04 federation (and FC) over the ODE toys, all four schemes."""

    def make() -> Any:
        return make_federation(kind, scheme)

    t0 = run_tier("interpret", make, ode_state(), timestep=ODE_DT, n_steps=N_STEPS)
    t1 = run_tier("plan", make, ode_state(), timestep=ODE_DT, n_steps=N_STEPS)
    assert_states_bitwise_equal(t0, t1)


def test_calling_frequency_subcycle_composite_bitwise() -> None:
    """(c) CallingFrequency (period 2Δt) + Subcycle (n=3) in one SUS composite."""
    t0 = run_tier(
        "interpret", make_cf_subcycle_composite, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS
    )
    t1 = run_tier(
        "plan", make_cf_subcycle_composite, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS
    )
    assert_states_bitwise_equal(t0, t1)


def test_scaling_wrapper_folds_to_constants_bitwise() -> None:
    """ScalingWrapper dissolution (§8.2 'scaling-type wrappers fold into constants')."""
    t0 = run_tier(
        "interpret", make_scaling_composite, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS
    )
    t1 = run_tier("plan", make_scaling_composite, toy_state(), timestep=COLUMN_DT, n_steps=N_STEPS)
    assert_states_bitwise_equal(t0, t1)


# -- DynamicalCore stage/substep unrolling ---------------------------------------------

_DIMS = ["cell", "height"]


class _SubstepCore(DynamicalCore):
    """2-stage core with the super-fast tier on: exercises substep unrolling.

    Stage output ψ* is a Heun-style provisional; substeps relax the running
    substate toward the enclosing stage output (reads the ``stage/`` view, the
    chained substate, ψⁿ and the port — every substep input source).
    """

    n_stages: ClassVar[int] = 2
    substep_fraction: ClassVar[float | tuple[float, ...]] = (0.5, 1.0)
    input_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        "forcing_of_eastward_wind": {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    diagnostic_properties: ClassVar[dict[str, Any]] = {
        "core_activity": {"dims": _DIMS, "units": "1"},
    }
    tendency_port: ClassVar[dict[str, str]] = {"eastward_wind": "forcing_of_eastward_wind"}

    def stage_array_call(
        self,
        stage: int,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        dt: timedelta,
    ) -> None:
        seconds = dt.total_seconds()
        u = inputs["eastward_wind"]
        forcing = inputs["forcing_of_eastward_wind"]
        span = seconds if stage == 0 else 0.5 * seconds
        outputs["eastward_wind"][...] = u + span * (forcing - 0.25 * u)
        outputs["core_activity"][...] = u * (stage + 1.0)

    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        dt: timedelta,
    ) -> None:
        seconds = dt.total_seconds()
        current = inputs["eastward_wind"]
        target = inputs["stage/eastward_wind"]
        forcing = inputs["forcing_of_eastward_wind"]
        outputs["eastward_wind"][...] = current + seconds * (0.5 * (target - current) + forcing)
        outputs["core_activity"][...] = current + 10.0 * (stage + substep)


def _core_state() -> dict[str, Any]:
    state = ode_state()
    shape = state["eastward_wind"].data.shape
    import numpy as np

    state["forcing_of_eastward_wind"] = make_dataarray(
        np.full(shape, 0.125, dtype=np.float64),
        name="forcing_of_eastward_wind",
        dims=_DIMS,
        units="m s-2",
        location="cell",
    )
    return state


@pytest.mark.parametrize("substeps", [0, 4])
def test_dynamical_core_unrolls_bitwise(substeps: int) -> None:
    """DynamicalCore stage (and substep) tiers unroll with bound dt (§8.2)."""

    def make() -> Any:
        return _SubstepCore(substeps=substeps)

    t0 = run_tier("interpret", make, _core_state(), timestep=ODE_DT, n_steps=N_STEPS)
    t1 = run_tier("plan", make, _core_state(), timestep=ODE_DT, n_steps=N_STEPS)
    assert_states_bitwise_equal(t0, t1)


def test_plan_signatures_reflect_cadence() -> None:
    """The CF composite compiles to one op-list variant per step signature."""
    from symcon.core import ExecutionPlan, StateSchema

    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    plan = ExecutionPlan.bind(
        make_cf_subcycle_composite(), StateSchema.from_state(toy_state()), ctx
    )
    # CF period 2 steps x ping-pong parity 2 -> 2 signatures (lcm).
    assert plan.signatures == ("step 0 (mod 2)", "step 1 (mod 2)")
