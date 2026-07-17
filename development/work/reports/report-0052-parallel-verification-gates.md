# Work unit 0052 — Parallel verification gates

**Branch:** `work/0052-parallel-verification-gates` · **Date:** 2026-07-17 · **State:** ready for review

> **Headline: this work unit delivers no parallelism, because the battery does not
> parallelize.** A single pytest process uses ~1.1 of 16 cores with the host 90 % idle and
> `wa=0` — neither CPU- nor IO-bound — yet concurrent processes serialize on *something*
> (identified: no; see §5). pytest-xdist, two-wave
> scheduling, and lane concurrency were each built and each measured to **nothing**
> (50.4 / 51.1 min against a 51.9 min sequential baseline, all inside a ±15 % noise floor).
> All three were withdrawn; the gate ships **sequential**.
>
> What it does deliver is **Item A**: the `fast` marker expression never excluded `data`, so
> 43 tests ran twice every gate. Removing them takes the battery from ~62 to ~50 min — and
> that result is proven by *set arithmetic*, not by timing, so none of the noise touches it.
> The work unit's title is now a misnomer: these are *disjoint* gates, not parallel ones.
> The negative results are recorded (TD-52.1 `rejected`; §6) so the next attempt starts by
> identifying what actually serializes, instead of rediscovering that nothing helps.

## 1. What was built

Four changes, in the order the plan sequences them:

**Item A — the partitions are now disjoint.** The `fast` marker expression was
`not gpu and not slow`, which does not exclude `data`. All 43 `data and not slow` tests
therefore ran inside `fast` *and again* in their own partition — about 7 minutes of duplicated
work, and, worse, it made `fast` a reference-loading partition, falsifying the "complementary
profiles" premise any wave scheduling rests on. `fast` is now
`not gpu and not slow and not data`. This is a partition-boundary change, not a coverage
change; §2 criterion 1 carries the proof.

**Item B — the gt4py concurrent-compile question: no mitigation needed, with evidence.** gt4py
1.1.10 wraps the read-check-build-recheck of **a given program's** build directory in a
`filelock` lock (`gt4py/next/otf/compilation/compiler.py:73` — `locking.lock(src_dir)`, where
`src_dir = cache.get_cache_folder(inp, …)`; its own comment cites "multiple MPI ranks" as the
motivating case). Crucially `read_data()` is re-checked *inside* the lock, so a process that
blocks on a peer's in-progress build skips the build entirely rather than redundantly repeating
it. This is live, not theoretical: the cache carries 490 lock files across 218 cache
directories — which is also the proof that the lock is **per-program**, since a global one
would be a single file. No warm-up was built. A warm-up would also have been
unprovable here — the gate baseline is warm caches — and the plan explicitly notes that
`--collect-only` runs no test body and so compiles nothing, making it a non-warm-up.

**But Item B asked the wrong question, and that is this work unit's central lesson.** "Is
concurrent compilation *safe*?" — yes. The question that decided the outcome was "is it
*free*?" — and measurement says no (§5), for reasons still unidentified. Asking *that* in Item
B, before building anything, would have failed the work unit's premise on day one and saved
three designs. Note the lock is **per-program**, not global (`locking.py` keys it on the
program's cache folder — hence 490 lock files across 218 dirs), and a `workflow.CachedStep`
in-memory dict above the `Compiler` means warm in-process lookups never reach it: it is *not*
a demonstrated bottleneck. Identifying the real one is the top follow-up (§6).

**Item C — `tools/run_gate.py`.** An accelerated *executor* of the gate, never a redefinition
of it: every pytest invocation is the policy's marker command **verbatim, with nothing added**
(Amendment 4 removed even `-n`/`--dist`). `_assert_no_selection_flags` enforces that in code
(`-x`, `--exitfirst`, `-k`, `--ignore`, `--deselect`, `-p` are refused) and `_check_order`
asserts every partition is scheduled exactly once, so the invariant Item A established cannot
silently regress. Failures reproduce the offending partition's output verbatim, never a
summary. The RSS budget is enforced rather than documented: the driver samples the process
tree each second and fails the gate above 23 GiB. Modes: default (lint battery as cheap
fail-fast, then every partition in sequence), `--partition` (one alone), and `--serial` —
which the spec's frozen CLI names, and which is now an explicit **alias of the default**: with
concurrency withdrawn (D6), the gate and its own baseline oracle are the same command.

**The schedule: sequential.** `fast` → `slow-nodata` → `data-noslow` → `data-slow`, one
process at a time. Concurrency was built twice (waves, then lanes) and measured to buy nothing
— see §3 D6 and §5.

**Item D — calibration, which invalidated the work unit's premise.** See §3 D1, D5, D6. The
short version: **no form of parallelism helps this battery**, because it does not parallelize —
concurrent processes serialize on an unidentified shared resource. The win is Item A, which needs none.

## 2. Acceptance criteria → tests

| # (spec) | Criterion | Evidence |
|---|---|---|
| 1 | Coverage invariance — union 848, `fast ∩ data-noslow = ∅` | §5 collection proof: both unions 848, intersection 0, delta exactly 43 |
| 2 | Driver green, counts identical to `--serial` | §5 independence table |
| 3 | Independence: serial ≡ parallel ≡ parallel | §5 independence table |
| 4 | Peak RSS of the schedule < 23 GB, measured as it runs (amended) | §5 — measured *and* enforced in code (driver fails the gate above budget) |
| 5 | gt4py concurrent-compile answered with evidence | §1 Item B — safe; lock is per-program (`locking.py`), 490 lock files / 218 dirs. Moot for the shipped gate (nothing runs concurrently), but answered as asked |
| 6 | `verification-gates.md` updated in the same PR | Item F commit |
| 7 | **Inverted (Amendment 4): no dependency added.** `git diff main -- pyproject.toml uv.lock` empty; `uv sync --locked` resolves; `import xdist` → `ModuleNotFoundError` | §3 D5; TD-52.1 `rejected` |
| 8 | Wall-time materially reduced vs the *measured* serial baseline (amended) | §5 wall-time |

## 3. Deviations

**D1 — the spec's ≈ 18–22 min target and its `data+slow` rationale were both measurably
false; the spec was amended (owner-instructed, TD-52.2) rather than the result retrofitted.**

Item D's calibration of `data+slow` produced a flat sweep:

| `data+slow` config | Wall-time | Peak RSS |
|---|---|---|
| serial (no xdist) | **33:04** | **5.0 GiB** |
| `-n 2 --dist load` | 33:08 | 6.4 GiB |
| `-n 4 --dist load` | 35:13 | 9.0 GiB |

A `--durations=25` run explains why. One test is three quarters of the partition:

```
1518.95s call  test_jw_plan_equivalence.py::test_jw_t0_t1_bitwise_24h[gtfn_cpu]
 192.93s call  test_jw_example.py::test_example_02_smoke_6h
  48.43s call  test_nonhydro_datatest.py::test_restart_bitwise_reproducibility[...]
   ...
   6.20s call  test_static_fields_datatest.py::test_metrics_parity[...altitude]
   0.10s call  test_static_fields_datatest.py::test_metrics_parity[...zdiff_gradp]
   0.06s call  test_static_fields_datatest.py::test_metrics_parity[...pg_exdist]
76 passed, 1 skipped, 806 deselected, 28 warnings in 2011.90s (0:33:31)
```

Two spec claims die here:

1. **The 55-test `test_static_fields_datatest.py` is not the bottleneck.** The spec says those
   tests "each re-run the gt4py metrics/interpolation factories". They do not:
   `_get_static` is memoized per process (`test_static_fields_datatest.py:148` cache dict,
   `:172–208` the lookup/populate), so the first test pays ~6.2 s and the rest ~0.06–0.10 s
   each — **~12 s combined, 0.6 % of the partition.** xdist cannot divide that cost; it
   *multiplies* it, once per worker, which is why `-n 4` is the slowest and hungriest row.
2. **The ≈ 18–22 min target is arithmetically impossible.** `test_jw_t0_t1_bitwise_24h`
   alone is 25.3 min, and no worker count splits a single test. It is a bitwise T0≡T1
   equivalence test, which AGENTS.md protects ("no tolerance creep, no reduction-order
   changes… bitwise T0≡T1 is required"), so it cannot be weakened to fit the target.

Both the reviewer and I had verified the *count* (55 of 77) and neither of us checked the
*time distribution*; the count was true and the inference drawn from it was worthless. Per
AGENTS.md ("never silently resolve a contradiction") the options were put to the owner, who
instructed: take the real win, and correct the spec rather than leave a false claim as merged
truth. `data+slow` became serial — fastest *and* lowest-RAM, so it won on both axes. The spec
carries an inline amendment banner; TD-52.2 records the sanction (same class as TD-35.5, an
owner-instructed edit of a frozen document).

*(D1 kept `data+slow` inside a wave, on the reasoning that overlapping `fast` was still its
only real parallelism. D5 and D6 later removed that too: there is no wave, because there is no
useful concurrency anywhere. D1 stands as the record of the first correction, not as the
shipped design.)*

**No target was retrofitted to the achieved figure.** That is the substitution the gate-reading
rules exist to prevent, and the amended criterion 8 forbids it explicitly.

**D5 — pytest-xdist withdrawn entirely: the work unit's own premise did not survive
measurement** (owner-instructed 2026-07-17; TD-52.1 → `rejected`; spec Amendment 4).

D1's calibration was re-measured on a verifiably idle host (load 0.70, 23 GB free) and **did
not reproduce**:

| Measurement | D1's figure | Re-measured (idle) | |
|---|---|---|---|
| `fast` serial | 2:29 | 2:10, 2:40, 2:32 → **~2:28** (n=4) | |
| `fast` `-n 10` | 2:22 | 2:49, 2:57 → **~2:43** (n=3) | serial now *ahead*; the "5 % xdist gain" was noise |
| `data-noslow` `-n 3` | 6:38 | **>10:00** (timed out, 39/43 done) | the 19 % gain — xdist's last justification — evaporated |

**Run-to-run variance is ±15 %, and worse on the `data` partitions.** The cause is the page
cache: `EXCLAIM_APE` is 8.7 GB extracted against ~10 GB of `buff/cache`, so those partitions'
timings track cache warmth as much as scheduling — and back-to-back calibration runs silently
guarantee a warm cache, which a fresh run does not. Every xdist effect ever claimed in this
work unit (5–19 %) sits *inside* that noise floor. They were measurements of the page cache.

Consequences, and they are the deliverable:

- **No dependency.** `pyproject.toml` and `uv.lock` end **byte-identical to main**
  (`git diff main -- pyproject.toml uv.lock` is empty). `uv sync --locked` resolves;
  `import xdist` → `ModuleNotFoundError`. TD-52.1 is `rejected`, not pending: there is
  nothing to sign off.
- **No knobs.** No `-n`, no `--dist`, no per-partition caps, no calibration table. Every
  partition runs its marker command verbatim. The `--workers` flag is gone.
- **The schedule rests on structure instead.** `data-slow` holds one core for ~33 min; the
  other three chain alongside it. "Don't idle 15 cores for half an hour" needs no statistics.
- **Amendment 3 was wrong and is superseded by Amendment 4.** It "calibrated" `slow-nodata` to
  serial on a 37 s difference and kept `data-noslow` at `-n 3` on a 94 s one — both inside the
  noise. It was fitted to a single sample per configuration. Recorded rather than quietly
  corrected, because the failure mode is the reusable lesson: **a single-sample comparison on
  this battery measures the page cache**, and the spec's own "starting targets… calibration"
  language invited exactly that error by presenting the knobs as things to be tuned rather
  than justified.

The reusable rule now lives in `policies/verification-gates.md`: do not re-add xdist without a
benchmark that beats the noise floor — multiple samples per configuration, controlled page
cache, one variable at a time.

**D6 — concurrency withdrawn too: the gate ships sequential** (owner-instructed 2026-07-17;
spec Amendment 5). With xdist gone, the lane schedule was the remaining idea, and it rested on
a structural argument I believed needed no statistics: `data-slow` holds one core for ~33 min,
so the other 15 idle. It was implemented, measured, and **rejected — 51.1 min vs 51.9 min
sequential**, with every partition 1.5–3.2× slower and total wall-time conserved (§5).

The root cause (§5) is that the battery does not parallelize at all: one partition uses ~1.1
of 16 cores with the host 90 % idle and `wa=0`, so it is neither CPU- nor IO-bound, and
concurrent processes serialize on *something* — and what, precisely, is **not identified**
(§5). Item B asked whether concurrent compilation was *safe* (yes) and never asked whether it
was *free* (no). Had that question been asked first, the work unit's premise would have failed
on day one, before any xdist, waves, lanes, or calibration were built.

**The shipped design therefore contains no parallelism of any kind**, and the work unit's title
is a misnomer: it delivers *disjoint* verification gates, not parallel ones. What it delivers
is Item A, which needs none of it, plus a documented negative result so the next person does
not rebuild this. `tools/run_gate.py` survives on its non-parallel merits — one command,
verbatim capture, exit aggregation, an enforced RSS budget, and the marker expressions encoded
so they cannot drift from the policy.

**D2 — `spec-0052` is in the diff, which plan acceptance-7 does not list.** Acceptance-7
enumerates an exhaustive file set (`pyproject.toml`, `uv.lock`, `tools/run_gate.py`,
`verification-gates.md`, `REGISTRY.md`, the report, + test files under Item E's exception).
D1's amendment necessarily adds the spec. Sanctioned by TD-52.2, flagged here rather than
waved through.

**D3 — `development/references/lock.toml` is in the diff, which the plan's review checklist
says must be empty.** The checklist asserts
`git diff main -- docs/architecture development/references/lock.toml` is empty. That
contradicts AGENTS.md's reference-mining rule and `/implement-plan` step 3, both of which
require every consulted source be appended to the ledger with its SHA — and Item B's whole
deliverable is a mined gt4py finding. The plan is the lowest authority of the three, so the
ledger entry (`[[ref]] id = "gt4py-build-cache-locking"`) stays and the checklist line is
recorded here as the drafting error it is. `docs/architecture/` is untouched, as required.

**D4 — the plan's acceptance-6 still names the ≈ 18–22 min target.** Superseded automatically
by authority order (spec > plan) via D1's amendment. The plan is frozen at assignment and was
not edited.

## 4. Tolerances & sign-off flags

**No dependency flag is raised: this work unit adds no dependency.** TD-52.1 proposed
`pytest-xdist>=3.6` as a `dev` lower bound; it was measured, rejected, and withdrawn (D5), so
`pyproject.toml`/`uv.lock` end byte-identical to main and `constraints/cpu-ci.txt` was never a
question. Its `REGISTRY.md` §3 row is `rejected` and carries the evidence, so the negative
result stays visible to whoever next reaches for xdist here.

`TD-PENDING: TD-52.2` — the sanctioned `spec-0052` amendment, **Amendments 1–5** (D1, D5, D6).
Owner-instructed 2026-07-16 (Amendments 1–2) and 2026-07-17 (Amendments 3–5, the withdrawal of
xdist and of all concurrency). Registered: `REGISTRY.md` §3.

**No tolerance, reduction-order, or marker change was made anywhere.** The 1519 s
`test_jw_t0_t1_bitwise_24h[gtfn_cpu]` is the battery's floor and was left exactly as it is: it
is a bitwise T0≡T1 equivalence test, which AGENTS.md protects. Making the gate faster by
weakening it was never on the table.

## 5. Gates (dated)

Gate host 16-core / 31 GB, warm caches. Dated per subsection: the calibration and the wave
run are 2026-07-16; the re-measurement, the lane run, and the shipped gate are 2026-07-17.

### Coverage invariance — acceptance 1, the load-bearing proof

Plan Item A's commands, re-derived:

```
fast_old 740 · fast_new 697 · data-noslow 43 · slow-nodata 31 · data-slow 77
union OLD: 848
union NEW: 848
fast_new INTERSECT data-noslow: 0        (disjoint)
fast_old MINUS fast_new:        43       (delta set-equal to data-noslow: YES)
sum of parts:                   848      (== union => partitions disjoint)
```

The delta is proven **set-equal** to the `data, not slow` partition, not merely equal in
count. No test left the battery.

### Serial oracle — `tools/run_gate.py --serial` (each partition alone, all 16 cores)

```
[ok ] ruff-check     All checks passed!
[ok ] ruff-format    175 files already formatted
[ok ] mypy           Success: no issues found in 50 source files
[ok ] lint-imports   Contracts: 2 kept, 0 broken.
[ok ] fast           696 passed, 1 skipped, 186 deselected, 41 warnings in 149.66s (0:02:29)
[ok ] slow-nodata    31 passed, 852 deselected, 5 warnings in 459.75s (0:07:39)
[ok ] data-noslow    43 passed, 840 deselected, 11 warnings in 492.44s (0:08:12)
[ok ] data-slow      76 passed, 1 skipped, 806 deselected, 28 warnings in 1996.04s (0:33:16)

wall-time: 51.9 min
GATE: green
```

`ruff format` reports **175** files against the table's 173. Attributed line-by-line: +1
`tools/spec_freeze_guard.py` (merged to main in `f6ee96a`, which did not update the baseline
table as the keep-current rule requires) and +1 `tools/run_gate.py` (this work unit). No file
in this work unit's diff is unaccounted for.

### Parallel gate at the spec's *starting targets* (i.e. before Amendment 3)

```
wave 1: peak RSS 7.8 GiB
  [ok ] fast          696 passed, 1 skipped, 50 warnings in 167.61s (0:02:47)
  [ok ] data-slow     76 passed, 1 skipped, 806 deselected, 28 warnings in 2173.07s (0:36:13)
wave 2: peak RSS 5.4 GiB
  [ok ] slow-nodata   31 passed, 10 warnings in 651.05s (0:10:51)
  [ok ] data-noslow   43 passed, 13 warnings in 842.44s (0:14:02)

wall-time: 50.4 min
GATE: green
```

Wave 1 shared the host with the collection commands above; `data-slow`'s 36:13 against 33:04
alone is that contention, and is why this run's wall-time is not quoted as the headline.

### Item D calibration — each configuration measured **alone**

| Partition | Config | Wall-time | Peak RSS |
|---|---|---|---|
| fast | serial | 2:29 | (oracle) |
| fast | `-n 10 --dist load` | **2:22** | 7.3 GiB |
| slow-nodata | serial | **7:39** | (oracle) |
| slow-nodata | `-n 6 --dist load` | 8:16 | 2.9 GiB |
| data-noslow | serial | 8:12 | (oracle) |
| data-noslow | `-n 3 --dist loadscope` | **6:38** | 3.2 GiB |
| data-slow | serial | **33:04** | **5.0 GiB** |
| data-slow | `-n 2 --dist load` | 33:08 | 6.4 GiB |
| data-slow | `-n 4 --dist load` | 35:13 | 9.0 GiB |

**These figures are single samples and were later shown unreliable — see the re-measurement
below.** They are kept because the errors built on them are the record.

### Re-measurement on a verifiably idle host — the calibration does not reproduce

Prompted by the owner's question of whether the above was perturbed by other system activity.
Host confirmed idle first (load 0.70, nothing but desktop + editor, 23 GB available):

| Config | Calibration | Re-measured (idle) | |
|---|---|---|---|
| `fast` serial | 2:29 | 2:10 · 2:40 · 2:32 → **~2:28** (n=4) | |
| `fast` `-n 10` | 2:22 | 2:49 · 2:57 → **~2:43** (n=3) | **sign flipped** — serial now ahead |
| `data-noslow` `-n 3` | 6:38 | **>10:00** (timed out, 39/43 done) | **+50 %**, same config |

**Run-to-run variance is ±15 %, worse on the `data` partitions.** They are page-cache bound:
`EXCLAIM_APE` is 8.7 GB extracted against ~10 GB of `buff/cache`, so their timings track cache
warmth — and back-to-back calibration runs silently guarantee a warm cache where a fresh run
does not. **Every xdist effect claimed above (5–19 %) sits inside that noise floor.** They were
measurements of the page cache. Consequence: xdist withdrawn (§3 D5, TD-52.1 `rejected`).

### The lane schedule — built, measured, rejected

With xdist gone, the remaining idea was structural: `data-slow` holds one core for ~33 min, so
run the other three beside it. Implemented and measured:

```
lanes (concurrent): data-slow | fast -> slow-nodata -> data-noslow
  [ok ] fast          696 passed, 1 skipped, 186 deselected, 41 warnings in 263.85s (0:04:23)
  [ok ] slow-nodata   31 passed, 852 deselected, 5 warnings in 1190.94s (0:19:50)
  [ok ] data-slow     76 passed, 1 skipped, 806 deselected, 28 warnings in 3006.33s (0:50:06)
  [ok ] data-noslow   43 passed, 840 deselected, 11 warnings in 1595.90s (0:26:35)

peak RSS: 7.7 GiB  (budget 23 GiB)
wall-time: 51.1 min
GATE: green
```

**51.1 min against the 51.9 min sequential oracle — nothing**, while every partition slowed
1.5–3.2× (`data-slow` 33:04 → 50:06; `slow-nodata` 7:39 → 19:50; `data-noslow` 8:12 → 26:35).
Total wall-time was *conserved*. That is the signature of a shared serializing resource, not of
parallel work. Concurrency withdrawn (§3 D6).

### Why nothing concurrent works — measured, and NOT explained

Measured on a single `fast` partition, host otherwise idle:

```
real pytest pid: 2088077
pytest %cpu=113  threads=101
   vmstat: r=2 b=0 us=9 sy=1 id=90 wa=0     (repeated across 5 samples)
```

**One partition uses ~1.1 of 16 cores while the host is 90 % idle, with `wa=0` and `b=0`.** The
gate is neither CPU-bound nor IO-bound. Two processes using ~2 of 16 cores *cannot* contend for
CPU — so the 1.5–3.2× slowdowns above are not resource exhaustion. **Something serializes the
partitions. What, is not established, and this report does not claim otherwise.**

**A retracted claim, and the lesson in it.** An earlier draft of this report asserted the cause
was gt4py's build-cache lock — "a global `filelock.UnixFileLock`, acquired on every program
lookup, warm hits included". The reviewer checked it against the source and it is **wrong on
both counts**:

- `compiler.py:73` is `with locking.lock(src_dir)` where `src_dir = cache.get_cache_folder(inp, …)`.
  `_core/locking.py` places the lock file *inside that program's* cache folder. The lock is
  **per-program**, not global — and this report's own evidence refutes the "global" reading:
  490 lock files across 218 directories. A global lock would be **one** file.
  `development/references/lock.toml` recorded "keyed on the per-program cache folder" from the
  start; the draft contradicted the work unit's own ledger.
- `gtx.gtfn_cpu` resolves to `run_gtfn_cpu_cached`, whose executor is a `workflow.CachedStep`
  holding an **in-memory dict** *above* the `Compiler`. A warm in-process lookup returns from
  that dict and never reaches the lock. It is taken once per distinct program per process
  (~218×), briefly — which cannot account for a 3.2× stretch over 33 minutes.

So the mechanism is unknown. Candidates worth profiling: memory bandwidth; page-cache eviction
between partitions that each want 8.7 GB of references against ~10 GB of cache; same-program
lock contention. The honest instrument is a profiler (`py-spy dump` on both partitions mid-run,
`strace -c`, `perf stat`), not reasoning from plausible mechanisms.

**This changes no decision.** The withdrawal of xdist, waves, and lanes rests on the
measurements, which stand without any mechanism. What it changes is the *guidance*: the
prerequisite for future gate parallelism is to identify the serializing resource, not to "fix
the gt4py lock". Beneath whatever it turns out to be lies the 1519 s single test.

**The lesson, stated plainly because it is the one worth keeping.** This work unit's whole
story is claims that felt obvious and dissolved under measurement — the 55-test module, the
xdist gains, the lane schedule. Then the explanation that *replaced* them was asserted without
verification and got the same treatment. Reaching for a mechanism that fits the data is not the
same as checking it, and the mistake survives right up to the moment someone reads the source.

### Independence — Item E / acceptance 2 & 3

Counts across **every** execution mode measured in this work unit — sequential, xdist at four
different worker configurations, and two concurrent schedules (waves and lanes):

| Partition | Sequential | xdist (all configs) | Waves | Lanes |
|---|---|---|---|---|
| fast | 696 passed, 1 skipped | 696 passed, 1 skipped | 696 passed, 1 skipped | 696 passed, 1 skipped |
| slow-nodata | 31 passed | 31 passed | 31 passed | 31 passed |
| data-noslow | 43 passed | 43 passed | 43 passed | 43 passed |
| data-slow | 76 passed, 1 skipped | 76 passed, 1 skipped | 76 passed, 1 skipped | 76 passed, 1 skipped |

Identical throughout — a stronger result than the criterion asks for, since the shipped design
has only one execution mode. Skips are the permitted set (1 mpi opt-in; the 1 upstream MCH
diffusion skip; gpu-marked tests deselected by marker, no CUDA device). No new skip.

### The shipped gate — `tools/run_gate.py` (sequential), 2026-07-17

```
logs: .../gate_final
lint battery (cheap fail-fast):
  [ok ] ruff-check     0.0 min  All checks passed!
  [ok ] ruff-format    0.0 min  175 files already formatted
  [ok ] mypy           0.0 min  Success: no issues found in 50 source files
  [ok ] lint-imports   0.0 min  Contracts: 2 kept, 0 broken.
partitions (sequential): fast -> slow-nodata -> data-noslow -> data-slow
  [ok ] fast           2.8 min  696 passed, 1 skipped, 186 deselected, 41 warnings in 164.01s (0:02:44)
  [ok ] slow-nodata    6.8 min  31 passed, 852 deselected, 5 warnings in 404.75s (0:06:44)
  [ok ] data-noslow    6.4 min  43 passed, 840 deselected, 11 warnings in 381.52s (0:06:21)
  [ok ] data-slow     33.6 min  76 passed, 1 skipped, 806 deselected, 28 warnings in 2012.35s (0:33:32)

peak RSS: 5.0 GiB  (budget 23 GiB)
wall-time: 49.6 min
GATE: green
```

**49.6 min against the ~62 min original battery** (acceptance 8), with peak RSS 5.0 GiB against
the 23 GiB budget (acceptance 4 — measured on the schedule as actually run, and enforced in
code). Counts match the oracle and every other configuration exactly (acceptance 2, 3).

**All of that reduction is Item A.** The sequential oracle measured 51.9 min and this run 49.6
— the same schedule, 4.4 % apart, which is simply the ±15 % noise floor breathing. Nothing in
this work unit's scheduling contributes; the disjointness fix does all the work, and it is the
one claim here that never needed a stopwatch.

## 6. Follow-ups

- **Identify what serializes concurrent partitions — the precondition for *any* future gate
  parallelism.** The fact is measured and solid (§5): a host at 90 % idle with `wa=0` cannot
  run two partitions at once for free — each slows 1.5–3.2× and total wall-time is conserved.
  The *cause* is unknown, and this work unit's guess (gt4py's cache lock) was checked against
  the source and does not hold: the lock is per-program, not global, and warm in-process
  lookups never reach it. **Profile before theorising** — `py-spy dump` on two concurrent
  partitions mid-run, `strace -c`, `perf stat` for memory-bandwidth saturation. Candidates:
  memory bandwidth; page-cache eviction between partitions each wanting 8.7 GB of references
  against ~10 GB of cache; same-program lock contention. Until it is identified and removed,
  **no xdist, no waves, no lanes, and no single-host CI sharding will help this battery** —
  which is empirical and holds regardless of the cause. Start here rather than rebuilding
  schedules, as this work unit did four times.
- **A real benchmark harness, if gate timing is ever to be optimised again.** Every timing
  conclusion in this work unit that wasn't structural turned out to be noise (D5). Anyone
  revisiting this needs: multiple samples per configuration, a controlled page cache (the
  `data` partitions are dominated by whether 8.7 GB of `EXCLAIM_APE` is warm), and one
  variable at a time. Without that, single-sample comparisons on this battery measure the
  page cache and nothing else. This is the prerequisite for re-opening xdist (TD-52.1) or
  tuning the lane schedule — not a nice-to-have.
- **`data+slow`'s 1519 s test is the floor beneath everything.** Even if the gt4py lock were
  fixed tomorrow, no schedule beats 25.3 min while `test_jw_t0_t1_bitwise_24h[gtfn_cpu]` runs
  as one test. It is a protected bitwise T0≡T1 test (AGENTS.md), so it cannot be weakened —
  any real gain has to come from making it *cheaper*, not from scheduling around it. Out of
  scope here and noted only so the ordering is clear: gt4py lock first, this second, and
  everything else in this work unit was noise.
- **Shorten `data+slow`'s critical path — the only lever left, and it is worth ~8 min.**
  `data+slow` measures 33:08 at `-n 2` but its theoretical floor is 25.3 min (the single long
  test). The gap is scheduling: `test_jw_t0_t1_bitwise_24h` sits late in collection order, so
  workers chew through the other ~8 min of tests first and then serialize on it —
  8 + 25.3 ≈ 33.3, which is the measured figure almost exactly. Running the long test **first**
  would let the remaining ~8 min hide behind it, approaching the floor. That needs a
  collection-order hook (`pytest_collection_modifyitems`), which touches test infrastructure
  and is out of this work unit's scope. Note this reorders *scheduling*, never selection — no
  test's outcome, tolerance, or marker changes.
- **The CI work unit** (unallocated; takes the next free number at assignment): `actions/cache`
  of the gt4py build dir, the marker matrix, and the `serialbox4py`-in-CI investigation. All
  explicitly out of scope here.
- `_get_static` refactoring is **not** worth a follow-up: measured at ~6 s total (D1).

## 7. Artifacts

None tracked. Gate logs are per-partition under the driver's `--logdir` and are reproducible
with the §5 commands.
