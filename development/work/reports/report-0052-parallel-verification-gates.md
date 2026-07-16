# Work unit 0052 — Parallel verification gates

**Branch:** `work/0052-parallel-verification-gates` · **Date:** 2026-07-16 · **State:** **blocked — one gate run outstanding** (§5 "Outstanding"). Not ready for review or PR.

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
1.1.10 wraps the whole read-check-build-recheck of its persistent build cache in a
`filelock.UnixFileLock` (`gt4py/next/otf/compilation/compiler.py:73`, whose own comment cites
"multiple MPI ranks" as the motivating case). Crucially `read_data()` is re-checked *inside*
the lock, so a worker that blocks on a peer's in-progress build skips the build entirely
rather than redundantly repeating it. This is live, not theoretical: the cache carries 490
lock files across 218 cache directories. No warm-up was built. A warm-up would also have been
unprovable here — the gate baseline is warm caches — and the plan explicitly notes that
`--collect-only` runs no test body and so compiles nothing, making it a non-warm-up.

**Item C — `tools/run_gate.py`.** An accelerated *executor* of the gate, never a redefinition
of it: every pytest invocation is the policy's marker command verbatim plus `-n`/`--dist` and
nothing else. `_assert_no_selection_flags` enforces that in code (`-x`, `--exitfirst`, `-k`,
`--ignore`, `--deselect`, `-p` are refused), and `_check_waves` asserts every partition is
scheduled exactly once with at most one RAM-heavy partition per wave, so the invariant Item A
established cannot silently regress. Failures reproduce the offending partition's output
verbatim, never a summary. Modes: default (lint battery as cheap fail-fast, then the two
waves), `--serial` (the baseline oracle), `--partition` (+ `--workers` for calibration).

**Item D — calibration, which invalidated part of the spec.** See §3 D1. The short version:
`data+slow` does not scale and now runs serially; `fast` carries the win.

## 2. Acceptance criteria → tests

| # (spec) | Criterion | Evidence |
|---|---|---|
| 1 | Coverage invariance — union 848, `fast ∩ data-noslow = ∅` | §5 collection proof: both unions 848, intersection 0, delta exactly 43 |
| 2 | Driver green, counts identical to `--serial` | §5 independence table |
| 3 | Independence: serial ≡ parallel ≡ parallel | §5 independence table |
| 4 | Per-wave peak RSS < 23 GB, measured on the waves as run | §5 wave RSS |
| 5 | gt4py concurrent-compile answered with evidence | §1 Item B — `compiler.py:73`, 490 lock files / 218 dirs |
| 6 | `verification-gates.md` updated in the same PR | Item F commit |
| 7 | `pytest-xdist` dev lower bound; `uv.lock` regenerated; `constraints/cpu-ci.txt` untouched | §4 TD-52.1 |
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
truth. `data+slow` is now serial — fastest *and* lowest-RAM, so it wins on both axes — and
stays in wave 1, where overlapping `fast` remains its only real parallelism. The spec carries
an inline amendment banner; TD-52.2 records the sanction (same class as TD-35.5, an
owner-instructed edit of a frozen document).

**No target was retrofitted to the achieved figure.** That is the substitution the gate-reading
rules exist to prevent, and the amended criterion 8 forbids it explicitly.

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

`TD-PENDING: TD-52.1` — `pytest-xdist>=3.6` added to `[dependency-groups].dev` as a
lower-bound declaration; `execnet` arrives transitively; `uv.lock` regenerated with no other
pin moved. `constraints/cpu-ci.txt` is deliberately untouched: it pins no pytest plugin at all
(`pytest`, `pytest-cov`, `pytest-mpi`, `ruff`, `mypy`, `hypothesis` are all absent from it),
so xdist does not belong there — now or in the CI follow-up. This is not a gt4py/icon4py pin
bump. Registered: `REGISTRY.md` §3.

`TD-PENDING: TD-52.2` — the sanctioned `spec-0052` amendment (D1). Owner-instructed
2026-07-16. Registered: `REGISTRY.md` §3.

## 5. Gates (dated)

All 2026-07-16, gate host 16-core / 31 GB, warm caches.

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

Three findings, all counter to the spec's expectations:

1. **xdist helps exactly one partition.** `data-noslow` gains 19 % (6:38 vs 8:12). `fast`
   gains 5 %. `slow-nodata` and `data-slow` are better serial. The corpus is dominated by
   per-worker fixed costs (gt4py/icon4py import, reference loads) that xdist duplicates
   rather than divides.
2. **Wave contention dwarfs any xdist effect.** `data-noslow` runs 6:38 alone but **14:02**
   paired with `slow-nodata` at `-n 6`. Those two, run alone and back-to-back, total 14:54 —
   the pairing bought 0.8 min. A 2× stretch is not explained by core count on a 16-core host
   with 9 workers, so the contended resource is elsewhere (memory bandwidth, or Item B's
   gt4py cache lock). This is the battery's real cost driver and the spec did not anticipate it.
3. **Almost the entire win is Item A, not parallelism.** The old `fast` baseline of ~13–15 min
   was not `fast` being slow — it was `fast` silently running the 43 duplicated `data` tests
   (~8:12 of work). With them removed, `fast` is 2:29 *serial*. Serial-with-Item-A is 51.9 min
   against the ~62 min original; the entire xdist + wave apparatus then moves 51.9 → 50.4.

### Independence — Item E / acceptance 2 & 3

| Partition | Serial (oracle) | Parallel (starting targets) |
|---|---|---|
| fast | 696 passed, 1 skipped | 696 passed, 1 skipped |
| slow-nodata | 31 passed | 31 passed |
| data-noslow | 43 passed | 43 passed |
| data-slow | 76 passed, 1 skipped | 76 passed, 1 skipped |

Identical throughout. Skips are the permitted set (1 mpi opt-in; the 1 upstream MCH diffusion
skip; gpu-marked tests deselected by marker, no CUDA device on this host). No new skip.

### Outstanding — why this report is not ready for review

**The full gate has not been run at the Amendment-3 calibrated caps.** Three consecutive
attempts were killed by the environment within ~1 min each (the three earlier long runs above
completed normally); foreground execution caps below the ~44 min the battery needs. No
partial or estimated figure is substituted here. Still required:

1. `tools/run_gate.py` at the calibrated caps, **twice** — for the headline wall-time, and for
   Item E's parallel-repeat leg (serial ≡ parallel ≡ parallel).
2. **Per-wave peak RSS at the calibrated caps** — acceptance 4 demands the waves be measured
   *as actually run*. The 7.8 / 5.4 GiB above are the *starting-target* caps; the calibrated
   caps use strictly fewer workers, so the true figures can only be lower — but "can only be
   lower" is an inference, and this criterion explicitly refuses inference. It is unmet until
   measured.

Projection, recorded as a projection and **not** a result: wave 1 ≈ 36 min (`data-slow`
serial + contention), wave 2 ≈ 8 min (max of 7:39 and 6:38, now only 4 processes), total
≈ **44 min** against the ~62 min original ≈ 1.4×.

## 6. Follow-ups

- **Restructure the waves — needs a trunk decision, worth ~8 min.** The measured per-wave RSS
  (7.8 / 5.4 GiB against the ≈ 23 GB budget) shows "one reference-loading partition per wave"
  is far more conservative than this host requires: the two RAM-heavy partitions together peak
  around 9 GiB, comfortably inside budget. `data-slow` is a 33-min serial critical path with
  most of the machine idle beside it. Chaining the other three alongside it in a single wave
  (2:22 + 7:39 + 6:38 = 16:39 of work) projects to ≈ 36 min rather than ≈ 44. This is a
  structural change to the spec's wave design, not a calibration output, so it was recorded
  rather than taken. It must be validated against per-wave RSS, and note finding 2 in §5:
  concurrency on this host is *not* free, so the projection needs measuring, not assuming.
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
