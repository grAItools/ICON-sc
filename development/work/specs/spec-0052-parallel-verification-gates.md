# 0052 — Parallel verification gates (bounded two-layer test parallelism)

**Depends on:** 0051 · **Graduated from:** `proposal-0052-parallel-verification-gates.md` · **Policies:** `policies/verification-gates.md`, `policies/agent-workflow.md`

## Goal
Cut the wall-time of the verification-gate battery (`policies/verification-gates.md`) on the 16-core / 31 GB gate host **without removing any test or relaxing any acceptance criterion** — no tolerance creep, no reduction-order change, no test-marker edits, no `-x`/`-k`/`--ignore`. The set of tests the battery executes as a whole is invariant. Serial baseline ≈ 57–67 min; target ≈ 18–22 min.

## In scope

**1. Make the four partitions disjoint.** Today's `fast` expression (`not gpu and not slow`) does **not** exclude `data`, so all 43 `data and not slow` tests run inside `fast` *and again* in their own partition. This work unit changes `fast` to `not gpu and not slow and not data`. This is a partition-boundary change, not a coverage change: the union of the four partitions is **848 tests before and after** (measured), because the `data, not slow` partition already covers exactly the 43 tests removed from `fast`. Consequences: the partitions become genuinely disjoint; `fast` becomes free of reference loads (the premise the wave scheduling rests on, which is false today); and ~7 min of duplicated work leaves the battery. The `fast` baseline count therefore *drops* (740 → 697 collected) — an intentional, justified boundary move under the verification-gates.md reading rules, **not** a removal; it is recorded as the new baseline with the union figure as evidence.

**2. Parallelism.** `pytest-xdist` added to the `dev` dependency group (+ `uv.lock` regenerated). A `tools/run_gate.py` orchestrator runs the four partitions with the per-partition policy below in two waves, shelling out to the marker commands and adding only `-n`/`--dist`, capturing each partition's output verbatim, and failing on any non-zero exit.

**3. Calibration.** A measurement pass that sets the RAM-bounded worker caps from observed peak RSS **of the waves as actually run** — not of partitions in isolation, which would not bound the concurrent peak.

**4. The gt4py cache-race question.** Determine whether gt4py's persistent build cache is safe under concurrent first-compile by xdist workers, and act on the answer. No warm-up is specified up front: the gate baseline is warm caches, so a warm-up's value is unproven, and an unproven mitigation must not be built blind.

**5. Docs.** `policies/verification-gates.md` updated: the new `fast` expression, the parallel driver as the canonical way to run the gate, the serial commands retained as the fallback/baseline oracle, the calibrated caps + measured RSS ceiling, and refreshed baselines.

### Per-partition policy (the single authoritative table)

`--dist` and `-n` are chosen per partition by resource profile. The `-n` values are starting targets; the two data caps are **set by calibration** and may only be lowered. The same `-n` applies whether a partition runs inside a wave or standalone via `--partition`.

| Partition | Marker expression | Tests | `--dist` | `-n` | Why |
|---|---|---|---|---|---|
| fast | `not gpu and not slow and not data` | 697 | `load` | 10 | No reference loads → low RAM. `load` spreads the 89-test `test_scheme_constants.py` group that `loadscope` would pin to a single worker; only ~56/697 tests use module-scoped fixtures, and under `load` those merely re-run per worker (cheap grids/configs) — they never break. |
| slow, no data | `slow and not gpu and not data` | 31 | `load` | 6 | Only ~7 module groups; `load` splits the three 9-test convergence modules that would otherwise serialize. |
| data, not slow | `data and not slow and not gpu` | 43 | `loadscope` | 3 | Reference loads (RAM/IO); keep a module's savepoints on one worker. RAM-bounded — calibrated. |
| data + slow | `data and slow and not gpu` | 77 | `load` | 2 | Must split `test_static_fields_datatest.py` (55 of the 77); each worker reloads `EXCLAIM_APE` (~4.0 GB compressed / **8.7 GB extracted**), so RAM caps the count. RAM-bounded — calibrated. |

**Waves** (partitions are disjoint, so a wave's RAM is the sum of its members'): Wave 1 = `fast` (`-n 10`) with `data+slow` (`-n 2`) — 12 workers; Wave 2 = `slow-nodata` (`-n 6`) with `data-noslow` (`-n 3`) — 9 workers. Only one reference-loading partition per wave.

## Out of scope
Changing what any test asserts, its tolerances, its `pytest.mark` markers, or its reduction order. Refactoring `_get_static`/the static-fields factory recomputation. gt4py/icon4py pin bumps. GPU/MPI gate timing. CI (`test-cpu.yml`) parallelism, `actions/cache` of the compile dir, and the `serialbox4py`-in-CI investigation — all the follow-up CI work unit.

## Frozen interfaces
- `tools/run_gate.py` CLI: default = the full parallel gate (lint battery, both waves), exiting non-zero iff any partition/check fails; `--serial` = the marker commands with no `-n`/`--dist` (the baseline oracle); `--partition <fast|slow-nodata|data-noslow|data-slow>` = one partition at its table `-n`/`--dist`. The marker commands in `policies/verification-gates.md` remain the canonical definition of *what* the gate runs; the driver is only an accelerated executor of them.
- No `symcon.*` source, public API, or import-graph change: **none**. import-linter contracts stay `2 kept, 0 broken`.

## Acceptance criteria
1. **Coverage invariance (the load-bearing one).** The union of tests collected across the four partitions is **848**, identical to the union before the `fast` expression changed, and `fast ∩ data-noslow = ∅`. Demonstrated by comparing collection *sets*, not by counting. Per-partition counts otherwise unchanged: `slow-nodata` 31, `data-noslow` 43, `data-slow` 77; `fast` 697 (was 740 — the 43-test delta is exactly the `data, not slow` set, accounted for line-by-line).
2. All gate commands, driven by `tools/run_gate.py`, stay green with **identical `passed`/`skipped` counts** to `--serial` on the same expressions. Allowed skips unchanged (1 mpi opt-in, gpu-no-device, 1 upstream MCH diffusion); any new skip is a finding to explain.
3. **Independence gate:** every partition, run serially and in parallel, yields identical counts; the parallel run repeated twice shows no order-flakiness. A parallel/serial divergence is root-caused and the offending test fixed — never masked, reordered-to-hide, or marker-edited.
4. **Peak RSS of each wave, measured as that wave actually runs, stays under 75 % of 31 GB (≈ 23 GB).** Measuring partitions in isolation does not satisfy this criterion. The calibrated caps and the measured per-wave peak are recorded in `policies/verification-gates.md`.
5. The gt4py concurrent-compile question is answered with evidence, and either (a) no mitigation is needed, or (b) a mitigation is implemented and its effect measured. An unanswered question is not acceptable; a speculative warm-up is not a substitute.
6. `policies/verification-gates.md` is updated in the same PR: new `fast` expression, parallel + serial invocations, calibrated caps, measured RSS ceiling, refreshed baseline table (keep-current rule), and the corrected `EXCLAIM APE` cache figure (~4.0 GB compressed / 8.7 GB extracted).
7. `pytest-xdist` (+ transitive `execnet`) added to the `dev` group as a lower-bound declaration; `uv.lock` regenerated; `uv sync --locked` still resolves. `constraints/cpu-ci.txt` is **not** touched — it pins no pytest plugin. The new dev dependency is recorded as a `TD-PENDING` in the report and a `REGISTRY.md` §3 row (trunk-visible; it is not a gt4py/icon4py pin bump).
8. Wall-time is materially reduced (target ≈ 18–22 min; report the measured figure against the measured serial baseline), with no change to test outcomes.
