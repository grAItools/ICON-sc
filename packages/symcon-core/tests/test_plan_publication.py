"""SPEC S14: top-level ``ConcurrentCoupling`` publication through the plan.

The §5.1/§4.2 LFC bus-publication pattern (SPEC S09's slow suite): the run
script evaluates a coupling once per step and merges the returned tendency dict
into the state, so the tendency fields *are* state fields downstream. The S05
compiler refused a top-level coupling; S14 compiles it — member evaluation as a
stage-0 walk (cadence masks preserved) plus one publication Axpy per tendency
field into its published cell, replaying T0's ``acc = c1; acc += c2; ...``
member order exactly. All equivalence is bitwise (AGENTS.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest
from _plan_toys import assert_states_bitwise_equal, run_tier

from symcon.core import (
    CallingFrequency,
    ComputeContext,
    ConcurrentCoupling,
    MemoryMonitor,
)
from symcon.core.components.base import Stepper, TendencyComponent
from symcon.core.testing.toys import Damping, column_state
from symcon.core.typing import FieldBuffer

DT = timedelta(minutes=1)
_DIMS = ["cell", "height"]
_SLOT = "slow_forcing_of_air_temperature"


class _SlowForcing(TendencyComponent):
    """Publishes a bus-slot tendency (the slot name is not a stepped field)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        _SLOT: {"dims": _DIMS, "units": "K s-1"},
    }

    def __init__(self, *, scale: float, name: str | None = None) -> None:
        super().__init__(name=name)
        self._scale = scale

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        temperature = np.asarray(inputs["air_temperature"])
        np.multiply(temperature, -self._scale, out=np.asarray(outputs[_SLOT]))


class _ApplySlowForcing(Stepper):
    """The consumer: forward-Euler application of the published slot."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
        _SLOT: {"dims": _DIMS, "units": "K s-1"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K"},
    }
    timestep_required: ClassVar[bool] = True

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        temperature = np.asarray(inputs["air_temperature"])
        forcing = np.asarray(inputs[_SLOT])
        out = np.asarray(outputs["air_temperature"])
        np.multiply(forcing, timestep.total_seconds(), out=out)
        np.add(temperature, out, out=out)


class _LoopComposite:
    """The §5.1 loop body shape (SCMComposition-lite): slow → consumer → fast."""

    def __init__(self, slow: ConcurrentCoupling, core: Any, fast: Any) -> None:
        self.slow = slow
        self.core = core
        self.fast = fast

    def step(self, state: Mapping[str, Any], timestep: timedelta) -> dict[str, Any]:
        working: dict[str, Any] = dict(state)
        tendencies, diagnostics = self.slow(working, timestep)
        working.update(diagnostics)
        working.update(tendencies)
        diags, new_state = self.core(working, timestep)
        working.update(diags)
        working.update(new_state)
        diags, new_state = self.fast(working, timestep)
        working.update(diags)
        working.update(new_state)
        return working

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del out
        return {}, self.step(state, timestep)

    def visit(self, plan_builder: Any) -> None:
        self.slow.visit(plan_builder)
        self.core.visit(plan_builder)
        self.fast.visit(plan_builder)


def _make_cadenced(cadence_steps: int = 3) -> _LoopComposite:
    cooling = CallingFrequency(_SlowForcing(scale=1e-5, name="cooling"), cadence_steps * DT)
    return _LoopComposite(
        slow=ConcurrentCoupling([cooling], name="slow_suite"),
        core=_ApplySlowForcing(name="apply_slow"),
        fast=Damping(tau=timedelta(hours=2)),
    )


def _make_multimember() -> _LoopComposite:
    """Three members on one slot: T0 sums acc = c1; acc += c2; acc += c3."""
    members = [
        _SlowForcing(scale=1e-5, name="a"),
        _SlowForcing(scale=3e-6, name="b"),
        _SlowForcing(scale=7e-7, name="c"),
    ]
    return _LoopComposite(
        slow=ConcurrentCoupling(members, name="slow_suite"),
        core=_ApplySlowForcing(name="apply_slow"),
        fast=Damping(tau=timedelta(hours=2)),
    )


@pytest.mark.parametrize("n_steps", [100, 101])
def test_cadenced_publication_t0_t1_bitwise(n_steps: int) -> None:
    """CF-wrapped publication: fire + replay phases, both parities, bitwise."""
    t0 = run_tier("interpret", _make_cadenced, column_state(), timestep=DT, n_steps=n_steps)
    t1 = run_tier("plan", _make_cadenced, column_state(), timestep=DT, n_steps=n_steps)
    assert_states_bitwise_equal(t0, t1)


def test_multimember_publication_t0_t1_bitwise() -> None:
    """Three contributions to one slot: the Axpy replays T0's member order."""
    t0 = run_tier("interpret", _make_multimember, column_state(), timestep=DT, n_steps=100)
    t1 = run_tier("plan", _make_multimember, column_state(), timestep=DT, n_steps=100)
    assert_states_bitwise_equal(t0, t1)


def test_published_slot_series_is_piecewise_constant_and_matches_t0() -> None:
    """The published cell replays the CF cache verbatim between fires (per step)."""
    series: dict[str, list[np.ndarray]] = {}
    for tier in ("interpret", "plan"):
        monitor = MemoryMonitor(variables=(_SLOT, "air_temperature"))
        ctx = ComputeContext("embedded", tier=tier)
        ctx.timeloop(column_state(), _make_cadenced(), timestep=DT, n_steps=9, monitors=[monitor])
        series[tier] = [np.asarray(snap[_SLOT].data).copy() for snap in monitor.snapshots]
    assert len(series["interpret"]) == len(series["plan"]) == 9
    for step, (t0_slot, t1_slot) in enumerate(
        zip(series["interpret"], series["plan"], strict=True)
    ):
        np.testing.assert_array_equal(t1_slot, t0_slot, err_msg=f"step {step}", strict=True)
    # piecewise-constant at cadence 3: steps [0,1,2], [3,4,5], [6,7,8] share values.
    for block in range(3):
        for offset in (1, 2):
            np.testing.assert_array_equal(
                series["plan"][3 * block + offset], series["plan"][3 * block], strict=True
            )
    # ... and the blocks differ (temperature moved between fires).
    assert not np.array_equal(series["plan"][0], series["plan"][3])


def test_publishing_coupling_cannot_enter_a_federation_section() -> None:
    """A bare coupling is not a federation section: the publication pattern is
    kept out of redirected (PS/STS) sections by the S04 constructor itself; the
    compiler's redirected-path guard is defense in depth behind it."""
    from symcon.core import ParallelSplitting

    with pytest.raises(TypeError, match="neither"):
        ParallelSplitting([ConcurrentCoupling([_SlowForcing(scale=1e-5)])])


def test_publication_plan_hash_is_stable_and_cadence_sensitive() -> None:
    """The published composition hashes stably and sees the cadence knob."""
    from symcon.core import ExecutionPlan, StateSchema

    ctx = ComputeContext("embedded", tier="plan", timestep=DT)
    schema = StateSchema.from_state(column_state())
    base = ExecutionPlan.bind(_make_cadenced(3), schema, ctx).plan_hash
    again = ExecutionPlan.bind(_make_cadenced(3), schema, ctx).plan_hash
    other = ExecutionPlan.bind(_make_cadenced(5), schema, ctx).plan_hash
    assert base == again
    assert base != other
