"""SPEC S14: the ICON substep-outer ``DynamicalCore`` nesting through the plan.

The compiler unrolls a ``substep_nesting = "substep_outer"`` core into the exact
per-substep op sequence of ``perform_dyn_substepping`` (REFERENCES.lock
``icon4py-driver-substep-op-order``, ``icon-fortran-substep-op-order``): step
ingress → per substep [private carry swaps → stage sequence → private time-level
swap (not after the last)] → step egress. Verified with the S05 hand-worked
op-list technique on ``substeps=2`` (PLAN S14 pitfall) before the full model:

- the emitted call/prefix/dt sequence is written out by hand and asserted;
- the **only** vault-visible effects are the boundary prognostics' step-level
  ping-pong — the per-substep internal swaps live inside component BoundCalls
  and never leak into the even/odd variants (the vault holds boundary fields
  only, §8.2/§4.5);
- T0 ≡ T1 bitwise in fp64 over 100 *and* 101 steps (odd count settles both
  parities), including the initial-timestep carry-swap exception, which lives
  in component-private state at both tiers.

All comparisons are exact (``assert_array_equal``), never ``allclose``
(AGENTS.md: no tolerance creep).
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest
from _plan_toys import assert_states_bitwise_equal, ode_state, run_tier

from symcon.core import ComputeContext, ExecutionPlan, StateSchema
from symcon.core.components.dycore import DynamicalCore
from symcon.core.plan.guards import PlanCompileError
from symcon.core.state.dataarray import make_dataarray

DT = timedelta(seconds=60)
_DIMS = ["cell", "height"]


class _IconNestedCore(DynamicalCore):
    """A stub substep-outer core: private time levels + a carry pair (§4.5).

    Mirrors the ``NonhydroSolver`` structure without icon4py: data flows through
    component-private buffers; the boundary dicts are ingested/egressed once per
    step; the carry pair swaps under the MOST_EFFICIENT rule (skipped on the
    very first substep of the very first step). The stage arithmetic is
    arbitrary but asymmetric in (stage, carry side), so a missing or misplaced
    swap changes the trajectory.
    """

    substep_nesting: ClassVar[str] = "substep_outer"
    n_stages: ClassVar[int] = 2
    input_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        "forcing_of_eastward_wind": {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[dict[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    tendency_port: ClassVar[dict[str, str]] = {"eastward_wind": "forcing_of_eastward_wind"}

    def __init__(self, *, substeps: int, name: str | None = None) -> None:
        super().__init__(substeps=substeps, name=name)
        self._now: Any = None
        self._new: Any = None
        self._pair: list[Any] = []
        self._at_initial = True
        self._steps_done = 0
        self.hook_log: list[tuple[Any, ...]] = []

    # -- plan hooks (S14 contract; T0's array_call drives the same privates) ----------

    def plan_ingress(
        self, n_substeps: int, inputs: dict[str, Any], outputs: dict[str, Any], dt: timedelta
    ) -> None:
        del outputs, dt
        u = inputs["eastward_wind"]
        if self._now is None:
            self._now = np.zeros_like(u)
            self._new = np.zeros_like(u)
            self._pair = [np.zeros_like(u), np.full_like(u, 1e-3)]
        assert n_substeps == self._resolved_substeps
        self._now[...] = u
        self._new[...] = u
        self.hook_log.append(("ingress", n_substeps, self._at_initial))

    def plan_substep_begin(
        self, substep: int, inputs: dict[str, Any], outputs: dict[str, Any], dt: timedelta
    ) -> None:
        del inputs, outputs, dt
        if not (self._at_initial and substep == 0):
            self._pair.reverse()
            self.hook_log.append(("swap_pair", substep))

    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        dt: timedelta,
    ) -> None:
        del outputs
        seconds = dt.total_seconds()
        forcing = inputs["forcing_of_eastward_wind"]
        if stage == 0:  # "predictor": reads/updates carry side 0
            self._pair[0][...] = 0.5 * self._now + 0.25 * self._pair[0]
            self._new[...] = self._now + seconds * (forcing + 1e-3 * self._pair[0])
        else:  # "corrector": reads/updates carry side 1
            self._pair[1][...] = 0.5 * self._new + 0.25 * self._pair[1]
            self._new[...] = self._new + seconds * 1e-3 * (self._pair[1] - self._pair[0])
        self.hook_log.append(("stage", stage, substep, self._at_initial))

    def plan_substep_end(
        self, substep: int, inputs: dict[str, Any], outputs: dict[str, Any], dt: timedelta
    ) -> None:
        del inputs, outputs, dt
        self._now, self._new = self._new, self._now
        self.hook_log.append(("swap_levels", substep))

    def plan_egress(self, inputs: dict[str, Any], outputs: dict[str, Any], dt: timedelta) -> None:
        del inputs, dt
        self._at_initial = False
        self._steps_done += 1
        outputs["eastward_wind"][...] = self._new
        self.hook_log.append(("egress",))

    # -- T0 orchestration (substep-outer, mirrors NonhydroSolver.array_call) ----------

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        n = self._resolved_substeps
        sub_dt = timestep / n
        assert sub_dt * n == timestep, "test misconfiguration: Δt not divisible"
        self.plan_ingress(n, inputs, outputs, timestep)
        for substep in range(n):
            self.plan_substep_begin(substep, inputs, outputs, sub_dt)
            for stage in range(self.n_stages):
                self.substep_array_call(stage, substep, inputs, outputs, sub_dt)
            if substep != n - 1:
                self.plan_substep_end(substep, inputs, outputs, sub_dt)
        self.plan_egress(inputs, outputs, timestep)

    def stage_array_call(
        self, stage: int, inputs: dict[str, Any], outputs: dict[str, Any], dt: timedelta
    ) -> None:
        self.substep_array_call(stage, 0, inputs, outputs, dt)


def _core_state() -> dict[str, Any]:
    state = ode_state()
    shape = state["eastward_wind"].data.shape
    state["forcing_of_eastward_wind"] = make_dataarray(
        np.full(shape, 0.125, dtype=np.float64),
        name="forcing_of_eastward_wind",
        dims=_DIMS,
        units="m s-2",
        location="cell",
    )
    return state


def _bind(substeps: int = 2, dt: timedelta = DT) -> ExecutionPlan:
    ctx = ComputeContext("embedded", tier="plan", timestep=dt)
    return ExecutionPlan.bind(
        _IconNestedCore(substeps=substeps), StateSchema.from_state(_core_state()), ctx
    )


# -- the hand-worked op list (PLAN S14 pitfall: verify n=2 before the full model) -------


def _phase_ops(plan: ExecutionPlan) -> list[list[str]]:
    """The describe() op lines, split per phase."""
    phases: list[list[str]] = []
    for line in plan.describe().splitlines():
        if line.startswith("phase "):
            phases.append([])
        elif phases and line.startswith("  "):
            phases[-1].append(line.strip())
    return phases


def test_hand_worked_op_list_two_substeps() -> None:
    """substeps=2: the emitted sequence, prefixes and dts — written out by hand."""
    plan = _bind(substeps=2)
    phases = _phase_ops(plan)
    assert len(phases) == 2  # boundary ping-pong parity only (no cadence)

    step_us = 60_000_000
    sub_us = step_us // 2
    expected = [
        ("plan_ingress", "2", step_us),
        ("plan_substep_begin", "0", sub_us),
        ("substep_array_call", "0,0", sub_us),
        ("substep_array_call", "1,0", sub_us),
        ("plan_substep_end", "0", sub_us),
        ("plan_substep_begin", "1", sub_us),
        ("substep_array_call", "0,1", sub_us),
        ("substep_array_call", "1,1", sub_us),
        ("plan_egress", "", step_us),
    ]
    for ops in phases:
        calls = [op for op in ops if op.startswith("call ")]
        parsed = [
            (
                re.search(r"method=(\S+)", op).group(1),  # type: ignore[union-attr]
                re.search(r"prefix=\(([^)]*)\)", op).group(1).replace(" ", ""),  # type: ignore[union-attr]
                int(re.search(r"dt_us=(\d+)", op).group(1)),  # type: ignore[union-attr]
            )
            for op in calls
        ]
        assert parsed == expected, f"op sequence diverges from the hand-worked list:\n{parsed}"


def test_internal_swaps_do_not_leak_into_the_vault() -> None:
    """PLAN S14 pitfall: only the boundary ping-pong reaches the vault.

    The plan owns exactly one unpublished cell — ``alt/eastward_wind``, the
    boundary pair partner — and each phase ends with exactly one vault ``Swap``
    (the step-level prognostic ping-pong). The private time levels and the
    carry pair produce **no** slots and **no** swaps: they live inside the
    component's BoundCalls.
    """
    plan = _bind(substeps=2)
    slot_lines = [line for line in plan.describe().splitlines() if line.startswith("slot ")]
    scratch = [line for line in slot_lines if "published=0" in line]
    assert len(scratch) == 1 and "alt/eastward_wind" in scratch[0], scratch
    for ops in _phase_ops(plan):
        swaps = [op for op in ops if op.startswith("swap ")]
        assert len(swaps) == 1 and "field=eastward_wind" in swaps[0], swaps


# -- T0 ≡ T1 (bitwise, both parities, initial-timestep exception included) --------------


@pytest.mark.parametrize("substeps", [1, 2, 5])
@pytest.mark.parametrize("n_steps", [100, 101])
def test_substep_outer_core_t0_t1_bitwise(substeps: int, n_steps: int) -> None:
    def make() -> Any:
        return _IconNestedCore(substeps=substeps)

    t0 = run_tier("interpret", make, _core_state(), timestep=DT, n_steps=n_steps)
    t1 = run_tier("plan", make, _core_state(), timestep=DT, n_steps=n_steps)
    assert_states_bitwise_equal(t0, t1)


def test_hook_order_matches_t0_including_initial_step() -> None:
    """The T1 hook sequence (swaps, stages, flags) equals T0's, steps 0..2.

    The initial-timestep carry-swap exception is component-private state at
    both tiers: step 0 skips the first pair swap, later steps do not.
    """
    t0_core = _IconNestedCore(substeps=2)
    t1_core = _IconNestedCore(substeps=2)
    ctx0 = ComputeContext("embedded", tier="interpret")
    ctx1 = ComputeContext("embedded", tier="plan")
    ctx0.timeloop(_core_state(), t0_core, timestep=DT, n_steps=3)
    ctx1.timeloop(_core_state(), t1_core, timestep=DT, n_steps=3)
    assert t0_core.hook_log == t1_core.hook_log
    # spot-check the hand-worked shape: no pair swap at (step 0, substep 0) only.
    swaps = [entry for entry in t1_core.hook_log if entry[0] == "swap_pair"]
    assert len(swaps) == 5  # 1 (step 0) + 2 + 2


# -- loud rejections ---------------------------------------------------------------------


def test_zero_substeps_is_rejected() -> None:
    with pytest.raises(PlanCompileError, match="mandatory"):
        _bind(substeps=0)


def test_non_divisible_timestep_is_rejected() -> None:
    with pytest.raises(PlanCompileError, match="not divisible"):
        _bind(substeps=2, dt=timedelta(microseconds=3))


def test_missing_plan_hooks_are_rejected() -> None:
    class _Hookless(DynamicalCore):
        substep_nesting: ClassVar[str] = "substep_outer"
        input_properties: ClassVar[dict[str, Any]] = dict(_IconNestedCore.input_properties)
        output_properties: ClassVar[dict[str, Any]] = dict(_IconNestedCore.output_properties)

        def stage_array_call(self, stage: int, inputs: Any, outputs: Any, dt: Any) -> None:
            raise NotImplementedError

        def substep_array_call(
            self, stage: int, substep: int, inputs: Any, outputs: Any, dt: Any
        ) -> None:
            raise NotImplementedError

    ctx = ComputeContext("embedded", tier="plan", timestep=DT)
    with pytest.raises(PlanCompileError, match="plan hooks"):
        ExecutionPlan.bind(_Hookless(substeps=2), StateSchema.from_state(_core_state()), ctx)


def test_unknown_nesting_is_rejected() -> None:
    class _Odd(_IconNestedCore):
        substep_nesting: ClassVar[str] = "diagonal"

    ctx = ComputeContext("embedded", tier="plan", timestep=DT)
    with pytest.raises(PlanCompileError, match="diagonal"):
        ExecutionPlan.bind(_Odd(substeps=2), StateSchema.from_state(_core_state()), ctx)


def test_monitor_in_composition_is_rejected_loudly() -> None:
    """Monitors are excluded from the plan (S14): they belong to the host step."""
    from symcon.core import MemoryMonitor

    ctx = ComputeContext("embedded", tier="plan", timestep=DT)
    with pytest.raises(PlanCompileError, match="host step"):
        ExecutionPlan.bind(MemoryMonitor(), StateSchema.from_state(_core_state()), ctx)
