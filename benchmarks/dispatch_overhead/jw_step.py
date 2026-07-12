"""S14 in-scope benchmark: JW per-step wall time, T0 vs T1 (report-only).

Observation, not threshold (SPEC S14 acceptance 4) — the numbers land in
plan/steps/S14_plan_through_dycore/STATUS.md. Two legs over independently
built JW models (the dycore is stateful), pyperf-style repetition (N steps per
repeat, best/median reported):

- **T0**: the composed model under interpret semantics — full per-call sympl
  machinery (negotiation, ingress, DataArray wrapping) around the two hosted
  granules per step;
- **T1**: ``ExecutionPlan.run_step`` on the frozen plan — the dycore unrolled
  substep-outer (13 BoundCalls) + diffusion (1 BoundCall) + 1 vault swap.

The delta is the host-side dispatch cost the §8.2 phase split removes; on this
model the hosted gtfn kernels dominate the step, so expect the delta to be a
small *fraction* — the point of the artifact is to quantify exactly that, in
contrast to the kernel-free S05 toy benchmark (~50x on dispatch alone).

GPU (informational, motivates P5): with ``--backend gtfn_gpu`` on a CUDA
device, the T1 leg additionally attempts a kernel-launch count by capturing
one step into a CUDA graph via cupy stream capture and counting the graph's
kernel nodes through ``cudaGraphGetNodes`` (ctypes; cupy v13 does not bind it —
REFERENCES.lock ``cupy-graph-launch-count``). Capture legitimately fails across
host seams (numpy work in hooks, allocations): the failure position *is* the
T2 segment observation, and is reported as such.

Run: ``uv run python benchmarks/dispatch_overhead/jw_step.py [--steps 20]
[--repeats 3] [--backend gtfn_cpu]``
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import statistics
import time
import warnings

os.environ.setdefault("GT4PY_BUILD_CACHE_LIFETIME", "persistent")
os.environ.setdefault(
    "GT4PY_BUILD_CACHE_DIR", str(pathlib.Path.home() / ".cache" / "symcon" / "gt4py")
)


def bench_t0(backend: str, n_steps: int, repeats: int) -> list[float]:
    from symcon.icon.presets import JWConfig, build_jw

    model = build_jw(JWConfig(backend=backend))
    state = dict(model.state)
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(n_steps):
            diagnostics, new_state = model.composition(state, model.dtime)
            state.update(diagnostics)
            state.update(new_state)
        timings.append((time.perf_counter() - start) / n_steps)
    return timings


def bench_t1(backend: str, n_steps: int, repeats: int) -> tuple[list[float], float]:
    from symcon.core import ExecutionPlan, StateSchema, StateVault
    from symcon.icon.presets import JWConfig, build_jw

    model = build_jw(JWConfig(backend=backend))
    ctx = dataclasses.replace(model.dycore.ctx, tier="plan", timestep=model.dtime)

    bind_start = time.perf_counter()
    plan = ExecutionPlan.bind(model.composition, StateSchema.from_state(model.state), ctx)
    vault = StateVault.from_state(dict(model.state))
    plan.run_step(vault, 0)  # materialization included in the bind cost
    bind_seconds = time.perf_counter() - bind_start

    timings = []
    step = 1
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(n_steps):
            plan.run_step(vault, step)
            step += 1
        timings.append((time.perf_counter() - start) / n_steps)

    if "gpu" in backend:
        _report_gpu_launch_count(plan, vault, step)
    return timings, bind_seconds


def _report_gpu_launch_count(plan, vault, step) -> None:  # type: ignore[no-untyped-def]
    """Best-effort kernel-launch count via cupy stream capture (gpu only)."""
    try:
        import ctypes

        import cupy
    except ImportError:
        print("gpu launch count:      skipped (no cupy)")
        return
    stream = cupy.cuda.Stream(non_blocking=True)
    try:
        with stream:
            stream.begin_capture()
            try:
                plan.run_step(vault, step)
            finally:
                graph = stream.end_capture()
        n_nodes = ctypes.c_size_t(0)
        cudart = ctypes.CDLL("libcudart.so")
        status = cudart.cudaGraphGetNodes(ctypes.c_void_p(graph.graph), None, ctypes.byref(n_nodes))
        if status != 0:
            print(f"gpu launch count:      cudaGraphGetNodes failed (status {status})")
        else:
            print(f"gpu graph nodes:       {n_nodes.value}  (one step under capture)")
    except Exception as exc:  # capture fails across host seams — the T2 observation
        print(f"gpu capture:           failed at a host seam ({type(exc).__name__}: {exc})")
        print("                       -> T2 will need SegmentMarker-delimited capture (§8.3)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=20, help="steps per repeat")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--backend", default="gtfn_cpu")
    args = parser.parse_args()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t0 = bench_t0(args.backend, args.steps, args.repeats)
        t1, bind_seconds = bench_t1(args.backend, args.steps, args.repeats)

    t0_best, t1_best = min(t0), min(t1)
    t0_med, t1_med = statistics.median(t0), statistics.median(t1)
    delta = (t0_best - t1_best) * 1e3
    print(f"model:                 JW dry (R02B04, 35 levels), backend {args.backend}")
    print(f"steps per repeat:      {args.steps}  (repeats: {args.repeats}, best reported)")
    print(f"T0 per step:           {t0_best * 1e3:9.1f} ms  (median {t0_med * 1e3:.1f} ms)")
    print(f"T1 per step:           {t1_best * 1e3:9.1f} ms  (median {t1_med * 1e3:.1f} ms)")
    print(
        f"host-side delta:       {delta:9.1f} ms/step  ({(1 - t1_best / t0_best) * 100:.1f}% of T0)"
    )
    print(f"one-time bind cost:    {bind_seconds:9.2f} s  (negotiation + materialize + step 0)")


if __name__ == "__main__":
    main()
