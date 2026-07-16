# 0052 — Parallel verification gates (bounded two-layer test parallelism)

**Depends on:** 0051 · **Graduated from:** `proposal-0052-parallel-verification-gates.md` · **Policies:** `policies/verification-gates.md`, `policies/agent-workflow.md`

## Goal
Cut the wall-time of the verification-gate battery (`policies/verification-gates.md`) on the 16-core / 31 GB gate host **without removing any test or relaxing any acceptance criterion** — no tolerance creep, no reduction-order change, no marker edits, no `-x`/`-k`/`--ignore`. Parallelism changes *scheduling only*, never *what runs*. Serial baseline ≈ 57–67 min; target ≈ 18–22 min.

## In scope
`pytest-xdist` added to the `dev` dependency group (+ `uv.lock` regenerated). A new orchestrator `tools/run_gate.py` that runs the four existing marker partitions with a **per-partition** `--dist`/`-n` policy, a gt4py compile warm-up pre-step, and two resource-complementary waves — shelling out to the *exact* marker commands, adding only `-n`/`--dist`, capturing each partition's output verbatim, and failing on any non-zero exit. A one-time RSS calibration that sets the two data-partition worker caps. Updates to `policies/verification-gates.md` (canonical parallel gate + retained serial fallback + calibrated caps + refreshed baseline). CI parallelism is **out of scope** (deferred follow-up work unit).

Per-partition policy (starting targets; the two data caps are set by calibration):

| Partition | `--dist` | `-n` | Why |
|---|---|---|---|
| fast (`not gpu and not slow`) | `loadscope` | 12 | 40+ module groups; preserves `scope="module"` fixtures |
| slow, no data | `load` | 8 | ~7 groups; splits the 9-test convergence modules; cheap fixtures |
| data, not slow | `loadscope` | 3–4 | RAM-bounded; savepoints stay on one worker |
| data + slow | `load` | 2–3 | must split the 55-test `test_static_fields_datatest.py`; each worker reloads `EXCLAIM_APE`, RAM caps it |

## Out of scope
Changing what any test asserts, its tolerances, markers, or reduction order. Refactoring `_get_static`/the static-fields factory recomputation. gt4py/icon4py pin bumps. GPU/MPI gate timing. CI (`test-cpu.yml`) parallelism, `actions/cache` of the compile dir, and the `serialbox4py`-in-CI investigation — all the follow-up CI work unit.

## Frozen interfaces
- `tools/run_gate.py` CLI: default run executes the full parallel gate (lint battery, warm-up, both waves) and exits non-zero iff any partition/check fails; `--serial` runs the byte-for-byte serial marker commands (the baseline oracle); `--partition <name>` runs one partition. The serial marker commands in `policies/verification-gates.md` remain the canonical definition of *what* the gate runs; the driver is only an accelerated executor of them.
- No `symcon.*` source, public API, or import-graph change: **none**. import-linter contracts stay `2 kept, 0 broken`.

## Acceptance criteria
1. All eight gate commands in `policies/verification-gates.md`, driven by `tools/run_gate.py`, stay green with **identical `passed`/`skipped`/`deselected` counts** to the serial baseline. Allowed skips unchanged (1 mpi opt-in, gpu-no-device, 1 upstream MCH diffusion); any new skip is a finding to explain.
2. **Independence gate:** every partition, run serially and in parallel, yields identical counts; the parallel run repeated twice shows no order-flakiness. A parallel/serial divergence is root-caused and the offending test fixed — never masked, reordered-to-hide, or marker-edited.
3. Peak RSS during the parallel gate stays under ~75 % of 31 GB (no OOM); the calibrated `-n` caps for the two data partitions **and** their measured RSS ceiling are recorded in `policies/verification-gates.md`.
4. The `policies/verification-gates.md` baseline table is updated in the same PR with parallel wall-times and the calibrated caps (keep-current rule).
5. `pytest-xdist` (+ transitive `execnet`) added to the `dev` group; `uv.lock` regenerated coherently; `uv sync --locked` still resolves. The new dev dependency is recorded as a `TD-PENDING` in the report and a decision row in `REGISTRY.md §3` (trunk-visible; it is not a gt4py/icon4py pin bump).
6. Wall-time is materially reduced (target ≈ 18–22 min; report the measured figure), with no change to test outcomes.
