"""S05 acceptance 6: per-step dispatch cost, T0 vs T1, 20 toy components.

Report-only (no hard threshold — SPEC S05); the numbers land in
development/records/005_vault_plan_t1_record/STATUS.md. The composition is the 20-component
toy loop of the zero-traffic suite (9 x WindSpeed+Relaxation couplings under
forward Euler + 2 bare Damping steppers) on the (1, 10) column state, so the
kernels are negligible and the measured time is dispatch.

Run: ``uv run python benchmarks/s05_dispatch.py``
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages/symcon-core/tests"))

from _plan_toys import COLUMN_DT, make_twenty_component_loop, toy_state

from symcon.core import (
    ComputeContext,
    ExecutionPlan,
    StateSchema,
    StateVault,
)

N_STEPS = 2000
REPEATS = 5


def bench_t0() -> list[float]:
    composition = make_twenty_component_loop()
    timings = []
    for _ in range(REPEATS):
        state = dict(toy_state())
        start = time.perf_counter()
        for _ in range(N_STEPS):
            diagnostics, new_state = composition(state, COLUMN_DT)
            state.update(diagnostics)
            state.update(new_state)
        timings.append((time.perf_counter() - start) / N_STEPS)
    return timings


def bench_t1() -> tuple[list[float], float, int]:
    ctx = ComputeContext("embedded", tier="plan", timestep=COLUMN_DT)
    state = toy_state()
    schema = StateSchema.from_state(state)
    composition = make_twenty_component_loop()

    bind_start = time.perf_counter()
    plan = ExecutionPlan.bind(composition, schema, ctx)
    vault = StateVault.from_state(state)
    plan.run_step(vault, 0)  # materialization included in the bind cost
    bind_seconds = time.perf_counter() - bind_start

    timings = []
    step = 1
    for _ in range(REPEATS):
        start = time.perf_counter()
        for _ in range(N_STEPS):
            plan.run_step(vault, step)
            step += 1
        timings.append((time.perf_counter() - start) / N_STEPS)
    return timings, bind_seconds, len(plan.signatures)


def main() -> None:
    t0 = bench_t0()
    t1, bind_seconds, signatures = bench_t1()
    t0_best = min(t0)
    t1_best = min(t1)
    print("components:            20 (state (1, 10), fp64, embedded backend)")
    print(f"steps per repeat:      {N_STEPS}  (repeats: {REPEATS}, best repeat reported)")
    t0_median = statistics.median(t0) * 1e6
    t1_median = statistics.median(t1) * 1e6
    print(f"T0 per-step dispatch:  {t0_best * 1e6:9.2f} us  (median {t0_median:.2f} us)")
    print(f"T1 per-step dispatch:  {t1_best * 1e6:9.2f} us  (median {t1_median:.2f} us)")
    print(f"speedup (best/best):   {t0_best / t1_best:9.1f}x")
    print(f"one-time bind cost:    {bind_seconds * 1e3:9.2f} ms  ({signatures} signatures)")
    print(f"bind amortizes after:  {bind_seconds / (t0_best - t1_best):9.0f} steps")


if __name__ == "__main__":
    main()
