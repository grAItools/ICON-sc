"""SPEC S05 acceptance 4: ``plan_hash`` stability and sensitivity.

Stable across two processes (different PYTHONHASHSEED) for identical
(composition, schema, ctx); changes when any config field, the component
order, or a schema entry changes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from _plan_toys import COLUMN_DT, make_toy_loop, toy_state

from icon_sc.core import ComputeContext, ExecutionPlan, StateSchema
from icon_sc.core.state.dataarray import make_dataarray

_TESTS_DIR = str(Path(__file__).parent)

_HASH_SCRIPT = """
import sys
sys.path.insert(0, {tests_dir!r})
from _plan_toys import COLUMN_DT, make_toy_loop, toy_state
from icon_sc.core import ComputeContext, ExecutionPlan, StateSchema

ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
plan = ExecutionPlan.bind(make_toy_loop(), StateSchema.from_state(toy_state()), ctx)
print(plan.plan_hash)
"""


def _bind(
    composition: Any | None = None,
    state: dict[str, Any] | None = None,
    ctx: ComputeContext | None = None,
) -> ExecutionPlan:
    if composition is None:
        composition = make_toy_loop()
    if state is None:
        state = toy_state()
    if ctx is None:
        ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    return ExecutionPlan.bind(composition, StateSchema.from_state(state), ctx)


def test_plan_hash_stable_within_process() -> None:
    assert _bind().plan_hash == _bind().plan_hash


def test_plan_hash_stable_across_processes() -> None:
    """Two subprocesses with different hash seeds produce the same plan_hash."""
    script = _HASH_SCRIPT.format(tests_dir=_TESTS_DIR)
    hashes = []
    for seed in ("0", "424242"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        hashes.append(result.stdout.strip())
    assert hashes[0] == hashes[1] == _bind().plan_hash


def test_plan_hash_changes_with_config() -> None:
    base = _bind().plan_hash
    non_strict = ComputeContext("embedded", strict=False, tier="plan", timestep=COLUMN_DT)
    other_dt = ComputeContext("embedded", tier="plan", timestep=timedelta(minutes=2))
    assert _bind(ctx=non_strict).plan_hash != base
    assert _bind(ctx=other_dt).plan_hash != base


def test_plan_hash_changes_with_component_order() -> None:
    from _plan_toys import TAU_DAMP, TAU_RELAX

    from icon_sc.core import ConcurrentCoupling, SequentialUpdateSplitting
    from icon_sc.core.testing.toys import Damping, Relaxation, WindSpeed

    reordered = SequentialUpdateSplitting(
        [
            Damping(tau=TAU_DAMP),  # sections swapped vs make_toy_loop()
            (ConcurrentCoupling([WindSpeed(), Relaxation(tau=TAU_RELAX)]), "forward_euler"),
        ]
    )
    assert _bind(composition=reordered).plan_hash != _bind().plan_hash


def test_plan_hash_changes_with_member_order() -> None:
    from _plan_toys import TAU_DAMP, TAU_RELAX

    from icon_sc.core import ConcurrentCoupling, SequentialUpdateSplitting
    from icon_sc.core.testing.toys import Damping, Relaxation, WindSpeed

    reordered = SequentialUpdateSplitting(
        [
            (ConcurrentCoupling([Relaxation(tau=TAU_RELAX), WindSpeed()]), "forward_euler"),
            Damping(tau=TAU_DAMP),
        ]
    )
    assert _bind(composition=reordered).plan_hash != _bind().plan_hash


def test_plan_hash_changes_with_schema_entry() -> None:
    import numpy as np

    base = _bind().plan_hash

    extra = toy_state()
    extra["extra_tracer"] = make_dataarray(
        np.zeros((1, 10)),
        name="extra_tracer",
        dims=["cell", "height"],
        units="1",
        location="cell",
    )
    assert _bind(state=extra).plan_hash != base

    f32 = toy_state()
    f32["northward_wind"] = make_dataarray(
        f32["northward_wind"].data.astype(np.float32),
        name="northward_wind",
        dims=["cell", "height"],
        units="m s-1",
        location="cell",
    )
    assert _bind(state=f32).plan_hash != base
