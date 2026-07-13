"""SPEC S14 acceptance 3 (SCM pair) + the S09 composition through the plan.

The plan-hash drift test the S09 STATUS anticipated: ``examples/01`` must build
exactly the composition the ``presets/scm.py`` builder returns — enforced by
binding both and comparing ``plan_hash`` (replacing S09's textual check as the
enforceable version). Plus the composition itself under T1: the slow suite is
a top-level publishing coupling (S14 compiler feature), the consumer and the
fast SUS ride the S05 machinery — T0 ≡ T1 bitwise across cadence fire/replay
phases and both ping-pong parities.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from symcon.core import ComputeContext, ExecutionPlan, StateSchema
from symcon.icon.presets import SCMConfig, build_scm

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples" / "01_scm_column.py"

#: 2 cadence periods (slow_timestep = 10·dt) + 1 to land on the odd parity.
N_STEPS = 21


def _load_example() -> Any:
    spec = importlib.util.spec_from_file_location("example_01_scm_column_s14", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bind(composition: Any, state: dict[str, Any], cfg: SCMConfig) -> ExecutionPlan:
    ctx = ComputeContext("embedded", tier="plan", timestep=cfg.dtime)
    return ExecutionPlan.bind(composition, StateSchema.from_state(state), ctx)


def test_scm_composition_t0_t1_bitwise() -> None:
    """The full S09 composition (publishing slow suite + consumer + fast SUS)
    is bitwise T0 ≡ T1 over two cadence periods plus one step (odd parity)."""
    import numpy as np

    finals = {}
    for tier in ("interpret", "plan"):
        composition, state, cfg = build_scm()  # fresh instances per leg (stateful CF)
        ctx = ComputeContext("embedded", tier=tier)
        finals[tier] = ctx.timeloop(state, composition, timestep=cfg.dtime, n_steps=N_STEPS)
    t0, t1 = finals["interpret"], finals["plan"]
    assert set(t0) == set(t1), sorted(set(t0) ^ set(t1))
    assert t0["time"] == t1["time"]
    for name in sorted(t0):
        if name == "time":
            continue
        np.testing.assert_array_equal(
            np.asarray(t1[name].data),
            np.asarray(t0[name].data),
            err_msg=f"T1 diverges from T0 on {name!r}",
            strict=True,
        )


# -- acceptance 3: the layout-doc drift test, now enforceable ---------------------------


def test_plan_hash_example_01_matches_scm_builder() -> None:
    """examples/01 builds hash-identically to the preset builder (SPEC S14 acc. 3)."""
    example = _load_example()
    ex_composition, ex_state, ex_cfg = example.build_model()
    composition, state, cfg = build_scm(SCMConfig())
    assert ex_cfg == cfg
    example_hash = _bind(ex_composition, ex_state, ex_cfg).plan_hash
    builder_hash = _bind(composition, state, cfg).plan_hash
    assert example_hash == builder_hash


@pytest.mark.parametrize(
    "knob",
    ["dtime", "slow_timestep", "fast_order"],
)
def test_plan_hash_changes_with_scm_config_knob(knob: str) -> None:
    """Any plan-visible config knob moves the hash (SPEC S14 acceptance 3).

    The three knobs cover the three plan surfaces a config can reach: the bound
    loop Δt (ctx), the cadence-mask structure (slow_timestep), and the op-list
    structure (an extended-but-legal fast_order). Shape knobs (``nlev``,
    ``n_cell``) deliberately do *not* move the hash: the symbolic plan is
    shape-free by design (§8.2 — shapes bind at materialization against the
    vault), and constructor scalars are the documented S05 blind spot.
    """
    base_composition, base_state, base_cfg = build_scm(SCMConfig())
    base = _bind(base_composition, base_state, base_cfg).plan_hash
    if knob == "dtime":
        composition, state, cfg = build_scm(SCMConfig(dtime=timedelta(seconds=60)))
    elif knob == "slow_timestep":
        composition, state, cfg = build_scm(SCMConfig(slow_timestep=timedelta(seconds=600)))
    else:
        # a legal (constraints-satisfying) but different section order.
        composition, state, cfg = build_scm(
            SCMConfig(), fast_order=("satad", "satad", "mphys", "satad")
        )
    assert _bind(composition, state, cfg).plan_hash != base
