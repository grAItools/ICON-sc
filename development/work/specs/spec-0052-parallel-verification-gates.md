# 0052 — Parallel verification gates (bounded two-layer test parallelism)

**Depends on:** 0051 · **Graduated from:** `proposal-0052-parallel-verification-gates.md` · **Policies:** `policies/verification-gates.md`, `policies/agent-workflow.md`

> **Amended 2026-07-16 during execution — owner-instructed, sanctioned; TD-52.2.**
> Item D's calibration measured two of this spec's claims to be false. Per AGENTS.md
> ("never silently resolve a contradiction"), they are corrected here rather than left as
> merged truth, and the amendments are marked inline:
> 1. **The ≈ 18–22 min target is unreachable** and is withdrawn. One test,
>    `test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, runs 1519 s (25.3 min) — 75 % of the
>    `data+slow` partition — and no worker count can split a single test. It is a bitwise
>    T0≡T1 equivalence test, which AGENTS.md forbids weakening.
> 2. **The `data+slow` rationale was factually wrong.** `test_static_fields_datatest.py`
>    does not re-run the gt4py factories per test: `_get_static` is memoized per process,
>    so its 55 tests cost ~12 s combined, not the bulk of the partition. `data+slow`
>    therefore runs **serially** — measured fastest *and* lowest-RAM.
> 3. **`-n` values calibrated from their starting targets** (the latitude this table
>    grants). Measured alone, xdist helps exactly one partition: `data-noslow` (6:38 at
>    `-n 3` vs 8:12 serial). `fast` gains 5 % (2:22 vs 2:29); `slow-nodata` and `data+slow`
>    are better serial. The battery's dominant cost is **wave contention, not xdist**:
>    `data-noslow` runs 6:38 alone but 14:02 when paired with `slow-nodata` at `-n 6`.
>
> **Open for trunk (not resolved here):** the wave *structure* is now the binding
> constraint, and the measured per-wave RSS (7.8 / 5.4 GiB against a ≈ 23 GB budget) shows
> the "one reference-loading partition per wave" rule is far more conservative than the
> hardware needs. A single-wave schedule — the other three partitions chained alongside
> `data+slow`'s 33-min critical path — projects to ≈ 36 min against this design's ≈ 45.
> That is a structural change, not a calibration output, so it is recorded as a follow-up
> rather than taken (report §6).
>
> Evidence and the full measurement table: `report-0052-parallel-verification-gates.md`.
> Everything else in this spec — the disjointness fix, the driver, the RSS criterion — was
> measured sound and is unchanged.

## Goal
Cut the wall-time of the verification-gate battery (`policies/verification-gates.md`) on the 16-core / 31 GB gate host **without removing any test or relaxing any acceptance criterion** — no tolerance creep, no reduction-order change, no test-marker edits, no `-x`/`-k`/`--ignore`. The set of tests the battery executes as a whole is invariant. Serial baseline ≈ 57–67 min. **(Amendment 1)** The battery's wall-time floor is set by its longest single test — `test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, 1519 s, unsplittable — so the target is the measured floor, not a fixed figure; the achieved figure is reported against the measured serial baseline.

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
| slow, no data | `slow and not gpu and not data` | 31 | — | **1 (serial)** | **(Amendment 3 — calibrated from the `-n 6` starting target.)** Measured alone: 7:39 serial vs 8:16 at `-n 6`. Splitting the three 9-test convergence modules does not pay for the per-worker startup. Serial also drops wave 2 from 9 worker processes to 4, which matters more than the 37 s: wave contention, not xdist, is this battery's real cost (see Waves). |
| data, not slow | `data and not slow and not gpu` | 43 | `loadscope` | 3 | Reference loads (RAM/IO); keep a module's savepoints on one worker. RAM-bounded — calibrated: **the one partition xdist genuinely helps**, 6:38 at `-n 3` vs 8:12 serial (measured alone). Peak RSS 3.2 GiB. |
| data + slow | `data and slow and not gpu` | 77 | — | **1 (serial)** | **(Amendment 2 — calibrated.)** Does not scale, because it is not 55 factory re-runs but one unsplittable test: `test_jw_t0_t1_bitwise_24h[gtfn_cpu]` is 1519 s of the partition's 2012 s (75 %). `_get_static` is memoized per process (`test_static_fields_datatest.py:148,172–208`), so the 55 static-fields tests cost ~12 s combined (6.2 s first, ~0.06–0.10 s each after) — xdist only duplicates that fixed cost per worker. Measured: serial **33:04 / 5.0 GiB** · `-n 2` 33:08 / 6.4 GiB · `-n 4` 35:13 / 9.0 GiB. Serial is fastest *and* lowest-RAM, so it wins on both axes; `EXCLAIM_APE` (~4.0 GB compressed / **8.7 GB extracted**) is loaded once instead of per worker. |

**Waves** (partitions are disjoint, so a wave's RAM is the sum of its members'): Wave 1 = `fast` (`-n 10`) with `data+slow` (**serial, 1 process** — Amendment 2) — 11 processes; Wave 2 = `slow-nodata` (**serial** — Amendment 3) with `data-noslow` (`-n 3`) — 4 processes. Only one reference-loading partition per wave. `data+slow` staying in a wave is what still buys its parallelism: it runs concurrently with `fast` rather than after it.

**(Amendment 3.)** Wave contention is real and larger than any xdist effect: at the original targets, wave 2's 9 worker processes stretched `data-noslow` from 6:38 (alone) to 14:02, while the same two partitions run alone and back-to-back total 14:54 — the pairing bought 0.8 min. Core count does not explain a 2× stretch on a 16-core host, so the contended resource is elsewhere (memory bandwidth, or the gt4py cache lock of Item B). Both amended `-n` reductions cut wave 2 to 4 processes, and the caps stand or fall on the *wave* RSS/wall-time evidence, never on solo figures alone.

## Out of scope
Changing what any test asserts, its tolerances, its `pytest.mark` markers, or its reduction order. Refactoring `_get_static`/the static-fields factory recomputation (**Amendment 2**: measured at ~6 s total, so there is nothing here worth refactoring; the real cost is the single 1519 s test, equally out of scope — it is a protected bitwise T0≡T1 test, and shortening the `data+slow` critical path is the follow-up work unit's problem, not this one's). gt4py/icon4py pin bumps. GPU/MPI gate timing. CI (`test-cpu.yml`) parallelism, `actions/cache` of the compile dir, and the `serialbox4py`-in-CI investigation — all the follow-up CI work unit.

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
8. **(Amendment 1.)** Wall-time is materially reduced against the *measured* serial baseline, and the achieved figure is reported. No fixed target: the floor is `data+slow`'s single 1519 s test plus wave 2, which is a property of the test corpus, not of the scheduling this work unit controls. Retrofitting a target to match the achieved figure is expressly not permitted; the withdrawn ≈ 18–22 min target is recorded as a deviation in the report with its measurement.
