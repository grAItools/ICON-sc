"""SPEC S14 (marker ``data``): the composed JW model through the plan compiler.

- Acceptance 2: the S05 zero-traffic assertions hold on the JW plan — no
  xarray/pint/negotiation frames and no state-name lookups inside ``run_step``
  (the tracemalloc criterion is toy-plan-only per SPEC S05 acceptance 3; the
  hosted granule legitimately allocates device temporaries).
- Acceptance 3 (JW pair): ``examples/02`` builds hash-identically to the
  ``presets/jw.py`` builder, and the plan-visible config knobs move the hash.

The heavy T0 ≡ T1 24 h equivalence lives in ``test_jw_plan_equivalence.py``
(marker ``data``+``slow``).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from datetime import timedelta
from pathlib import Path
from types import FrameType
from typing import Any

import pytest

from icon_sc.icon.testing import DATATEST_AVAILABLE

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not DATATEST_AVAILABLE,
        reason="icon4py datatest stack not installed (icon-sc-icon[datatest])",
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples" / "02_jw_baroclinic.py"


def _load_example() -> Any:
    spec = importlib.util.spec_from_file_location("example_02_jw_baroclinic_s14", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder_model() -> Any:
    from icon_sc.icon.presets import JWConfig, build_jw

    return build_jw(JWConfig())


def _bind(model: Any, *, timestep: timedelta | None = None, strict: bool = True) -> Any:
    from icon_sc.core import ExecutionPlan, StateSchema

    ctx = dataclasses.replace(
        model.dycore.ctx,
        tier="plan",
        strict=strict,
        timestep=timestep if timestep is not None else model.dtime,
    )
    return ExecutionPlan.bind(model.composition, StateSchema.from_state(model.state), ctx)


# -- acceptance 3: the layout-doc drift test (JW pair) ----------------------------------


def test_plan_hash_example_02_matches_builder(builder_model: Any) -> None:
    """examples/02 builds hash-identically to the preset builder (SPEC acc. 3)."""
    example = _load_example()
    example_model = example.build_model()
    assert _bind(example_model).plan_hash == _bind(builder_model).plan_hash


@pytest.mark.parametrize("knob", ["dtime", "ndyn_substeps", "strict"])
def test_plan_hash_changes_with_jw_config_knob(builder_model: Any, knob: str) -> None:
    """The plan-visible knobs move the hash (SPEC acc. 3): the bound loop Δt,
    the substep count (op-list structure) and the strict flag (ctx line).

    Constructor scalars (divdamp factors, diffusion coefficients, the JW
    perturbation amplitude) are the documented S05 ``plan_hash`` blind spot —
    they do not enter the symbolic plan.
    """
    base = _bind(builder_model).plan_hash
    if knob == "dtime":
        assert _bind(builder_model, timestep=timedelta(seconds=150)).plan_hash != base
    elif knob == "strict":
        assert _bind(builder_model, strict=False).plan_hash != base
    else:
        dycore = builder_model.dycore
        held = dycore._substeps
        try:
            # the ndyn_substeps knob without a second (expensive) archive build:
            # the compiler reads core.substeps at bind (S12 precedent for
            # touching a private in tests: upstream-style sub-step staging).
            dycore._substeps = held - 1
            assert _bind(builder_model).plan_hash != base
        finally:
            dycore._substeps = held


# -- acceptance 2: zero-traffic on the JW plan ------------------------------------------

#: Module-path fragments that must never appear on the T1 step path (the S05
#: acceptance-3 instrument, applied to the JW plan).
_FORBIDDEN = (
    "xarray",
    "pint",
    "icon_sc/core/contracts",
    "icon_sc/core/state/dataarray",
    "icon_sc/core/state/facade",
    "icon_sc/core/components/base",
    "icon_sc/core/coupling",
)


class _CountingNames(dict):  # type: ignore[type-arg]
    """A vault ``names`` map that records every lookup (S05 instrument)."""

    lookups = 0

    def __getitem__(self, key: str) -> int:
        type(self).lookups += 1
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        type(self).lookups += 1
        return super().get(key, default)


@pytest.mark.slow
def test_zero_traffic_on_the_jw_plan(builder_model: Any) -> None:
    """SPEC S14 acceptance 2: the S05 settrace + name-lookup instruments hold
    on the composed JW plan (dycore unrolled substep-outer + diffusion)."""
    from icon_sc.core import StateVault

    plan = _bind(builder_model)
    vault = StateVault.from_state(dict(builder_model.state))
    period = len(plan.signatures)
    for index in range(2 * period):  # materialize + settle both parities
        plan.run_step(vault, index)

    seen: list[str] = []

    def tracer(frame: FrameType, event: str, arg: Any) -> Any:
        if event == "call":
            seen.append(frame.f_code.co_filename.replace("\\", "/"))
        return None

    sys.settrace(tracer)
    try:
        for index in range(2 * period, 3 * period):
            plan.run_step(vault, index)
    finally:
        sys.settrace(None)

    offenders = sorted({path for path in seen if any(frag in path for frag in _FORBIDDEN)})
    assert not offenders, f"forbidden frames on the JW T1 step path: {offenders}"
    assert seen, "the tracer saw no frames at all; the instrument is broken"

    _CountingNames.lookups = 0
    vault.names = _CountingNames(vault.names)
    try:
        for index in range(3 * period, 4 * period):
            plan.run_step(vault, index)
    finally:
        vault.names = dict(vault.names)
    assert _CountingNames.lookups == 0
