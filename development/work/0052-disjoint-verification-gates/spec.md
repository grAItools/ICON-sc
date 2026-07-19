# 0052 — Disjoint verification gates (renamed from "parallel"; see the amendment banner)

**Depends on:** 0051 · **Graduated from:** `proposal-0052-disjoint-verification-gates.md` · **Policies:** `policies/verification-gates.md`, `policies/agent-workflow.md`

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
> 3. ~~**`-n` values calibrated from their starting targets.**~~ **SUPERSEDED BY AMENDMENT 4 —
>    every claim in this item is false.** It read: xdist helps exactly one partition,
>    `data-noslow` (6:38 at `-n 3` vs 8:12 serial); `fast` gains 5 %; the dominant cost is
>    wave contention. All of it was fitted to *single samples per configuration* and none of
>    it reproduced. Kept visible, not deleted: the mistake is the reusable lesson (§5 of the
>    report), and the ±15 % noise floor that swallowed these effects is a standing hazard for
>    anyone who times this battery.
>
> 4. **pytest-xdist is withdrawn entirely — it does not help this corpus** (owner-instructed
>    2026-07-17; TD-52.1 `rejected`). Amendment 3's per-partition `-n` values were
>    re-measured on an idle host and **did not reproduce**. Run-to-run variance is **±15 %**,
>    worse on the `data` partitions, because `EXCLAIM_APE` is 8.7 GB extracted against ~10 GB
>    of page cache — those timings track cache warmth, not scheduling. Every apparent xdist
>    gain sat inside that noise: `fast` is 2:28 serial vs 2:43 at `-n 10` (means of 4 and 3
>    samples — serial *ahead*, reversing Amendment 3's 5 % claim), and `data-noslow`'s 19 %
>    gain — the sole remaining justification for the dependency — evaporated on
>    re-measurement (6:38 → >10:00, same config, idle host). No `-n`, no `--dist`, no
>    dependency. The driver runs each marker command **verbatim**.
> 5. **No concurrency at all: the gate runs sequentially** (owner-instructed 2026-07-17).
>    Lane concurrency was implemented, measured, and **rejected**: two concurrent lanes ran
>    **51.1 min against 51.9 min sequential** — a 1.5 % difference against a ±15 % noise
>    floor — while every partition slowed 1.5–3.2× (`data+slow` 33:04 → 50:06, `slow-nodata`
>    7:39 → 19:50, `data-noslow` 8:12 → 26:35). Total wall-time was *conserved*: the
>    signature of a shared serializing resource, not of parallel work.
>
> **Why the premise was unsound — measured, but not explained.** A single pytest process uses
> **~1.1 of 16 cores with the host 90 % idle and `wa=0`**: the gate is neither CPU- nor
> IO-bound, so two processes on 16 cores cannot be contending for CPU — yet concurrency slows
> each by 1.5–3.2× and *conserves* total wall-time. Something serializes them.
>
> **The mechanism is NOT identified, and this spec does not claim one.** An earlier draft of
> this amendment blamed gt4py's build-cache lock; a reviewer checked it against the source and
> it is wrong as stated — `compiler.py:73` locks the *per-program* cache folder (490 lock files
> across 218 dirs; a global lock would be one), and a `workflow.CachedStep` in-memory dict above
> the `Compiler` means warm in-process lookups never reach it. `lock.toml`'s own entry said
> "per-program cache folder" all along; the draft contradicted the work unit's own ledger. That
> claim received none of the skepticism applied to the timing results it replaced — the same
> failure mode as Amendments 2–3, committed against the very claim that displaced them.
>
> The withdrawal of xdist/waves/lanes rests on **measurements, which need no mechanism to be
> valid**. Identifying the serializing resource is the prerequisite for any future attempt and
> is now the top follow-up. The floor beneath even that is one unsplittable 1519 s test.
>
> **What the work unit actually delivers.** The battery's win is **Item A (disjointness)**
> alone, and it needs no parallelism: the old ~13–15 min `fast` baseline was `fast` silently
> re-running the 43 duplicated `data` tests. Item A is proven by *set arithmetic* (union 848
> before and after, intersection empty) — immune to the noise that invalidated every
> timing-based claim here. ~62 min → ~50 min, and the title of this work unit is now a
> misnomer: it delivers *disjoint* verification gates, not parallel ones.
>
> Evidence and the full measurement table: `report-0052-disjoint-verification-gates.md`.
> The disjointness fix, the driver, and the RSS criterion were measured sound and stand.

## Goal
Cut the wall-time of the verification-gate battery (`policies/verification-gates.md`) on the 16-core / 31 GB gate host **without removing any test or relaxing any acceptance criterion** — no tolerance creep, no reduction-order change, no test-marker edits, no `-x`/`-k`/`--ignore`. The set of tests the battery executes as a whole is invariant. Serial baseline ≈ 57–67 min. **(Amendment 1)** The battery's wall-time floor is set by its longest single test — `test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, 1519 s, unsplittable — so the target is the measured floor, not a fixed figure; the achieved figure is reported against the measured serial baseline.

## In scope

**1. Make the four partitions disjoint.** Today's `fast` expression (`not gpu and not slow`) does **not** exclude `data`, so all 43 `data and not slow` tests run inside `fast` *and again* in their own partition. This work unit changes `fast` to `not gpu and not slow and not data`. This is a partition-boundary change, not a coverage change: the union of the four partitions is **848 tests before and after** (measured), because the `data, not slow` partition already covers exactly the 43 tests removed from `fast`. Consequences: the partitions become genuinely disjoint; `fast` becomes free of reference loads (the premise the wave scheduling rests on, which is false today); and ~7 min of duplicated work leaves the battery. The `fast` baseline count therefore *drops* (740 → 697 collected) — an intentional, justified boundary move under the verification-gates.md reading rules, **not** a removal; it is recorded as the new baseline with the union figure as evidence.

**2. Parallelism.** ~~`pytest-xdist` added to the `dev` dependency group (+ `uv.lock` regenerated).~~ **(Amendment 4: withdrawn — measured, does not help; `pyproject.toml`/`uv.lock` end byte-identical to main.)** A `tools/run_gate.py` orchestrator runs the four partitions, shelling out to the marker commands **verbatim** and adding nothing, capturing each partition's output verbatim, and failing on any non-zero exit. **(Amendment 5: there is no concurrency of any kind — not within partitions, not between them. The battery serializes on something unidentified rather than running in parallel, so the driver's value is operational (one command, verbatim capture, exit aggregation, enforced RSS budget), not parallelism.)**

**3. Calibration.** A measurement pass that sets the RAM-bounded worker caps from observed peak RSS **of the waves as actually run** — not of partitions in isolation, which would not bound the concurrent peak. **(Amendment 4: there are no worker caps left to calibrate. What survives is the RSS obligation — the peak must be measured on the schedule as actually run, which the driver now samples every second and enforces against the 23 GiB budget. Calibration's real product was the negative result: the noise floor (±15 %) exceeds every effect the caps were tuning, so the knobs were removed rather than tuned.)**

**4. The gt4py cache-race question.** Determine whether gt4py's persistent build cache is safe under concurrent first-compile by xdist workers, and act on the answer. **(Amendments 4–5: answered — safe, and the lock is per-program, not global. The question that decided this work unit was a different one: whether concurrency is *free*. Measured: it is not. Why: still unknown — the lock is not the demonstrated cause. Asking "is it free?" here, before building, would have failed the premise on day one.)** No warm-up is specified up front: the gate baseline is warm caches, so a warm-up's value is unproven, and an unproven mitigation must not be built blind.

**5. Docs.** `policies/verification-gates.md` updated: the new `fast` expression, the driver as the canonical way to run the gate, the marker commands, the measured RSS ceiling, and refreshed baselines. **(Amendments 4–5: "the parallel driver" → the sequential driver; "the calibrated caps" → nothing to record, there are none. Added instead: why the gate is sequential, the gt4py-lock root cause, and the ±15 % noise floor — so the next person does not repeat this work unit.)**

### Per-partition policy (the single authoritative table)

**(Amendments 4–5 — this table replaces the `--dist`/`-n` table.)** There are no worker counts and no `--dist` modes: every partition runs its marker command **verbatim**, in one process, one at a time. No concurrency survives anywhere in the design.

| Partition | Marker expression | Tests | Measured (alone) | Peak RSS |
|---|---|---|---|---|
| fast | `not gpu and not slow and not data` | 697 | **~2:28** (mean of 4; 2:10–2:40) | 2.8 GiB |
| slow, no data | `slow and not gpu and not data` | 31 | ~7:39 | ~2.9 GiB |
| data, not slow | `data and not slow and not gpu` | 43 | ~8:12 (6:38–>10:00 — page-cache bound) | ~3.2 GiB |
| data + slow | `data and slow and not gpu` | 77 | **~33:04** — the critical path | **5.0 GiB** |

`data+slow` is 75 % one test (`test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, 1519 s), which nothing splits; it sets the battery's floor. `_get_static` is memoized per process (`test_static_fields_datatest.py:148,172–208`), so the 55 static-fields tests cost ~12 s combined — they were never the bottleneck (Amendment 2).

**Treat every timing above as ±15 %.** The `data` partitions are page-cache bound (`EXCLAIM_APE` is 8.7 GB extracted against ~10 GB of cache), so their figures track cache warmth as much as anything else. They justify *structural* decisions only — never a tuning knob, which is precisely the trap Amendments 2–3 fell into.

**Schedule (Amendment 5, superseding both the waves and the lanes): sequential.** `fast` → `slow-nodata` → `data-noslow` → `data+slow`, one process at a time, ≈ 50 min (49.6 min measured 2026-07-17). Concurrency was built and measured twice — as waves (50.4 min) and as lanes (51.1 min) — against a 51.9 min sequential baseline. Neither beat the ±15 % noise floor: the partitions serialize on *something* rather than running in parallel, and what that something is remains unidentified (see the banner). The "one reference-loading partition per wave" rule dies with the waves; peak RSS is **5.0 GiB** sequential against a 23 GiB budget, and the driver samples the real peak each second and **fails the gate** above it, so the bound is enforced by measurement rather than by a rule of thumb.

## Out of scope
Changing what any test asserts, its tolerances, its `pytest.mark` markers, or its reduction order. Refactoring `_get_static`/the static-fields factory recomputation (**Amendment 2**: measured at ~6 s total, so there is nothing here worth refactoring; the real cost is the single 1519 s test, equally out of scope — it is a protected bitwise T0≡T1 test, and shortening the `data+slow` critical path is the follow-up work unit's problem, not this one's). gt4py/icon4py pin bumps. GPU/MPI gate timing. CI (`test-cpu.yml`) parallelism, `actions/cache` of the compile dir, and the `serialbox4py`-in-CI investigation — all the follow-up CI work unit.

## Frozen interfaces
- `tools/run_gate.py` CLI: default = the full gate (lint battery, then every partition **in sequence**), exiting non-zero iff any partition/check fails **or the measured peak RSS exceeds the 23 GiB budget**; `--partition <fast|slow-nodata|data-noslow|data-slow>` = one partition alone. **(Amendments 4–5:** the `-n`/`--dist` wording is withdrawn along with xdist and the calibration-only `--workers` flag is gone. `--serial` is still accepted — the frozen CLI names it — but is now an explicit **alias of the default**, since the default *is* sequential: with concurrency withdrawn, the gate and its own baseline oracle are the same command. The CLI surface is otherwise as frozen.**)** The marker commands in `policies/verification-gates.md` remain the canonical definition of *what* the gate runs; the driver is only an accelerated executor of them.
- No `icon_sc.*` source, public API, or import-graph change: **none**. import-linter contracts stay `2 kept, 0 broken`.

## Acceptance criteria
1. **Coverage invariance (the load-bearing one).** The union of tests collected across the four partitions is **848**, identical to the union before the `fast` expression changed, and `fast ∩ data-noslow = ∅`. Demonstrated by comparing collection *sets*, not by counting. Per-partition counts otherwise unchanged: `slow-nodata` 31, `data-noslow` 43, `data-slow` 77; `fast` 697 (was 740 — the 43-test delta is exactly the `data, not slow` set, accounted for line-by-line).
2. All gate commands, driven by `tools/run_gate.py`, stay green with **identical `passed`/`skipped` counts** to `--serial` on the same expressions. Allowed skips unchanged (1 mpi opt-in, gpu-no-device, 1 upstream MCH diffusion); any new skip is a finding to explain.
3. **Independence gate:** every partition, run serially and in parallel, yields identical counts; the parallel run repeated twice shows no order-flakiness. A parallel/serial divergence is root-caused and the offending test fixed — never masked, reordered-to-hide, or marker-edited.
4. **Peak RSS of the schedule, measured as it actually runs, stays under 75 % of 31 GB (≈ 23 GB).** Measuring partitions in isolation does not satisfy this criterion. **(Amendments 4–5:** "each wave" → the sequential schedule, there being no waves; "the calibrated caps" → the schedule itself, there being no caps. The obligation is unchanged and now *enforced in code*: the driver samples the peak each second and fails the gate if the budget is exceeded.**)** The measured peak is recorded in `policies/verification-gates.md`.
5. The gt4py concurrent-compile question is answered with evidence, and either (a) no mitigation is needed, or (b) a mitigation is implemented and its effect measured. An unanswered question is not acceptable; a speculative warm-up is not a substitute.
6. `policies/verification-gates.md` is updated in the same PR: new `fast` expression, parallel + serial invocations, calibrated caps, measured RSS ceiling, refreshed baseline table (keep-current rule), and the corrected `EXCLAIM APE` cache figure (~4.0 GB compressed / 8.7 GB extracted).
7. **(Amendment 4 — inverted.)** ~~`pytest-xdist` (+ transitive `execnet`) added to the `dev` group…~~ **No dependency is added.** xdist was measured and does not help this corpus, so `pyproject.toml` and `uv.lock` end **byte-identical to main** (`git diff main -- pyproject.toml uv.lock` empty), `uv sync --locked` still resolves, and `constraints/cpu-ci.txt` is untouched. TD-52.1 is recorded as **`rejected`** in `REGISTRY.md` §3 rather than pending — the negative result is the deliverable, and the register keeps it visible so a future work unit does not re-litigate it blind.
8. **(Amendments 1, 5.)** Wall-time is materially reduced against the *measured* baseline, and the achieved figure is reported. No fixed target. The reduction that materialised is **Item A's** (~62 → ~50 min): the 43 `data, not slow` tests no longer run twice. Scheduling contributes **nothing** — measured — because the battery serializes on an unidentified shared resource instead of running in parallel; and beneath that lies `data+slow`'s single unsplittable 1519 s test. Both are properties of the corpus and its toolchain, not of anything this work unit controls. Retrofitting a target to match the achieved figure is expressly not permitted; the withdrawn ≈ 18–22 min target is recorded as a deviation in the report with its measurement.
