# S14 — Execution plan through the dycore (T1 + benchmark)

**Lane:** B (trunk-merging, closes the slice) · **Depends on:** S05, S13

## Goal
The JW composition compiles to an execution plan and runs under T1 with T0-equivalence; dispatch-overhead evidence recorded. This is the slice's exit gate: both lanes' products under the trunk's execution machinery.

## In scope
Plan-compiler coverage for everything the JW loop uses (DynamicalCore substep unrolling with private-buffer stability across even/odd variants; Monitor exclusion from the plan with a `SegmentMarker`-delimited host step) · `benchmarks/dispatch_overhead/jw_step.py` (T0 vs T1 per-step wall time; kernel-launch count via cupy profiler hooks under `gpu`) · plan-hash regression: `presets/scm.py` builder vs `examples/01` and JW builder vs `examples/02` (the layout-doc drift test, now enforceable).

## Acceptance criteria
1. T0 ≡ T1 on JW, 24 simulated hours, bitwise fp64 per backend (same kernels ⇒ required, as in S05).
2. Zero-traffic assertions (S05 acceptance 3) hold on the JW plan.
3. Plan-hash equality tests green for both example/builder pairs; hash changes on any config knob (parametrized spot-check over 3 knobs).
4. Benchmark artifact committed to STATUS.md: T0 vs T1 host-side per-step cost breakdown; observation, not threshold.
5. `pytest -m "not gpu and not slow"` full-repo runtime ≤ 15 min on CI hardware (slice hygiene gate).
