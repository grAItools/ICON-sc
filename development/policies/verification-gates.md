# verification-gates — the gate battery, baselines, and output-reading rules

Scope: the verification gate every work unit must leave green, its baseline counts, and
the rules for reading gate output. Keep-current rule: a merged work unit that changes
any count updates this file in the same commit.

## The verification gate (run via `uv run`, from the repo root)

Every work unit must leave ALL of these green.

**Canonical invocation (work unit 0052):**

```
uv run python tools/run_gate.py            # the whole battery, sequentially; exits non-zero iff anything failed
```

The driver is an accelerated *executor* of the commands below, never a redefinition of them:
it runs each marker command **verbatim**, adding nothing. It adds one command instead of
eight, verbatim failure output, exit aggregation, and an enforced RSS budget. The marker
expressions here remain the canonical statement of *what* the gate runs. See "Why the gate is
sequential" below before attempting to speed it up.

**The commands themselves** — identical to what the driver runs. Run them exactly as written;
where a runtime exceeds your shell limit, split by marker or by file — never skip a partition.

```
uv run pytest packages -m "not gpu and not slow and not data" -q
uv run pytest packages -m "slow and not gpu and not data" -q
uv run pytest packages -m "data and not slow and not gpu" -q
uv run pytest packages -m "data and slow and not gpu" -q
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict -p icon_sc.core
uv run lint-imports
```

The `fast` expression gained `and not data` in work unit 0052. It previously did **not**
exclude `data`, so all 43 `data, not slow` tests ran in `fast` *and again* in their own
partition. Its baseline count therefore *drops* 739 → 696 passed. That is a partition-boundary
move, **not** a removal: the union across the four partitions is **848 tests before and
after**, `fast ∩ data-noslow = ∅`, and the 43-test delta is exactly the `data, not slow` set.
Under the reading rules below, this is the one sanctioned way a passed count may fall.

Baseline after the work-unit-0052 merge (warm caches — see "Caches" below; timings 2026-07-17). Keep this table current: a merged work unit that adds tests must update it in
the same commit (the ruff-format file count moves with any new file):

| Command | Baseline |
|---|---|
| fast (`not gpu and not slow and not data`) | 696 passed, 1 skipped (mpi), ~2:28 warm (was 739/1 and ~13–15 min under the old expression, which double-ran the 43 `data` tests — work unit 0052) |
| slow, no data | 31 passed, ~6:44 |
| data, not slow | 43 passed, ~6:21 (6:21–>10:00 observed: page-cache bound) |
| data and slow | 76 passed, 1 skipped, ~33:32 |
| ruff check / format | `All checks passed!` / `175 files already formatted` |
| mypy | `Success: no issues found in 50 source files` |
| lint-imports | `Contracts: 2 kept, 0 broken` |

Timings are ±15 % run-to-run on this host and the `data` rows swing further (page cache); treat
them as orders of magnitude, not as a regression signal. **Counts** are the signal.

## Why the gate is sequential — do not "parallelize" it (work unit 0052)

**This battery does not parallelize. Every attempt has been made and measured; none worked.**
`tools/run_gate.py` runs the four partitions one at a time, and that is a measured decision,
not an omission.

| Attempt | Wall-time | vs sequential (51.9 min) |
|---|---|---|
| pytest-xdist, per-partition worker counts | — | every gain inside the noise floor |
| Two waves (`fast‖data-slow`, then `slow-nodata‖data-noslow`) | 50.4 min | nothing |
| Two lanes (`data-slow` ‖ the other three chained) | 51.1 min | nothing |

The whole battery, sequential, measures **~50 min** (49.6 min on 2026-07-17; 51.9 min on
2026-07-16 — the same schedule, 4.4 % apart, which is the noise floor breathing).

**What is measured.** A single pytest process uses **~1.1 of 16 cores with the host 90 % idle
and `wa=0`** — the gate is neither CPU- nor IO-bound. Two processes therefore cannot be
contending for CPU, yet running them concurrently slows each by **1.5–3.2×** and **conserves
total wall-time**. Something serializes them.

**What is NOT known: why.** The mechanism is unidentified, and no one should act as though it
is. Work unit 0052 blamed gt4py's build-cache lock; that claim was checked against the source
and is **wrong as stated** — `compiler.py:73` locks `cache.get_cache_folder(inp, ...)`, the
*per-program* directory (490 lock files across 218 dirs; a global lock would be one), and a
`workflow.CachedStep` in-memory dict sits above the `Compiler`, so warm in-process lookups
never reach it. A briefly-held per-program lock cannot account for a 3.2× stretch.

**So the prerequisite for any future gate parallelism is to identify the serializing resource
first** — profile two concurrent partitions (`py-spy dump` on both, `strace -c`, `perf stat`
for memory-bandwidth saturation) rather than reasoning from plausible mechanisms. Candidates:
memory bandwidth; page-cache eviction between partitions that each want 8.7 GB of references
against ~10 GB of cache; same-program lock contention. **Until it is identified and removed,
xdist / wave / lane schedules and single-host CI sharding are all measured to buy nothing** —
that part is empirical and does not depend on knowing why.

**Where the win actually came from.** Not parallelism: **the disjointness fix** (`fast` gaining
`and not data`). The old ~13–15 min `fast` was `fast` silently re-running the 43 duplicated
`data` tests; without them it is ~2:28, and the battery is ~62 → ~50 min. That rests on set
arithmetic (union 848 before and after), not timing — which is why it is the one result here
that survived scrutiny.

**Measurement discipline — read before optimising anything here.** Run-to-run variance on this
host is **±15 %**, and the `data` partitions swing further: they are page-cache bound
(`EXCLAIM APE` is 8.7 GB extracted against ~10 GB of cache), so their timings track cache
warmth as much as scheduling. Work unit 0052 twice drew conclusions from single-sample
comparisons and twice had them reverse on re-measurement (`fast` serial-vs-`-n 10` flipped
sign; `data-noslow` went 6:38 → >10:00 in the *same* configuration). **A single-sample timing
comparison on this battery measures the page cache.** Anything proposing to change the gate's
scheduling needs multiple samples per configuration, a controlled page cache, and one variable
at a time — or a structural argument that needs no timing at all.

**RAM.** Sequential peak is **5.0 GiB** against a **23 GiB budget** (75 % of 31 GB), enforced
rather than assumed: the driver samples the process tree's peak RSS every second and **fails
the gate** if the budget is exceeded.

**gt4py concurrent compile — safe; no warm-up needed.** gt4py 1.1.10 wraps the
read-check-build-recheck of a program's build directory in a `filelock` lock
(`gt4py/next/otf/compilation/compiler.py:73`, comment cites "multiple MPI ranks");
`read_data()` is re-checked *inside* the lock, so a process blocked on a peer's build skips the
build rather than repeating it. The lock is **per-program** — keyed on that program's cache
folder (`_core/locking.py`), which is why this cache holds 490 lock files across 218 dirs — and
a `workflow.CachedStep` in-memory dict above the `Compiler` means warm in-process lookups do
not reach it. Concurrent compilation is therefore safe, and this lock is **not** a
demonstrated bottleneck (see "What is NOT known" above). `--collect-only` executes no test body
and so compiles nothing — it is not a warm-up.

Rules for reading gate output:
- **Passed counts may only grow** (you added tests). Any `failed`, any `error`, or a
  *drop* in passed counts you cannot attribute line-by-line to your own intentional
  test removal (which requires justification in your report) means: **stop, do not
  commit, report the failure verbatim** (the full pytest failure block, not a summary).
- `skipped` must only ever be: the 1 mpi opt-in skip, gpu-marked tests on a machine
  without CUDA, and the 1 upstream MCH-only diffusion skip. Any NEW skip is a finding
  to explain, not to ignore.
- Never add `-x`, `--ignore`, `-k`, or edit markers to make a gate pass. Never delete
  or comment out a failing assertion. If you cannot make the gate green within your
  work unit's scope, report honestly and stop.

## Caches (read-only context; do not delete or regenerate)

- `~/.cache/icon-sc/gt4py` — persistent gtfn program cache. First runs after code
  changes may recompile (minutes per variant); reruns are fast. Never point tests at
  a cold cache except where a plan explicitly says so.
- `~/.cache/icon-sc/icon4py-testdata` — serialized reference archives (GAUSS3D 57 MB,
  WK-torus ~1.6 GB, EXCLAIM APE **~4.0 GB compressed / 8.7 GB extracted**, JW ~14 GB,
  MCH ~11 GB). Downloaded via icon4py's own machinery on first use. The extracted APE
  figure is the load-bearing one for worker-count calibration (work unit 0052): it is what
  each reference-loading worker actually holds.
- `~/.cache/icon-sc/l4_reference` — the 9-day JW reference/twin/ICON-sc trajectories
  with a sha256 manifest. **Regenerating costs ~7 h and invalidates the recorded
  bitwise results — never regenerate** unless a plan explicitly instructs it
  (none of the current plans do).
