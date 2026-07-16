# verification-gates — the gate battery, baselines, and output-reading rules

Scope: the verification gate every work unit must leave green, its baseline counts, and
the rules for reading gate output. Keep-current rule: a merged work unit that changes
any count updates this file in the same commit.

## The verification gate (run via `uv run`, from the repo root)

Every work unit must leave ALL of these green.

**Canonical invocation (work unit 0052):**

```
uv run python tools/run_gate.py            # the whole battery, in two waves; exits non-zero iff anything failed
```

The driver is an accelerated *executor* of the commands below, never a redefinition of them:
it runs each marker command verbatim and adds only `-n`/`--dist`. The marker expressions here
remain the canonical statement of *what* the gate runs. See "Parallelism" below.

**Serial fallback and baseline oracle** — the same battery, no parallelism
(`uv run python tools/run_gate.py --serial` runs exactly these). Run them exactly as written;
where a runtime exceeds your shell limit, split by marker or by file — never skip a partition.

```
uv run pytest packages -m "not gpu and not slow and not data" -q
uv run pytest packages -m "slow and not gpu and not data" -q
uv run pytest packages -m "data and not slow and not gpu" -q
uv run pytest packages -m "data and slow and not gpu" -q
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict -p symcon.core
uv run lint-imports
```

The `fast` expression gained `and not data` in work unit 0052. It previously did **not**
exclude `data`, so all 43 `data, not slow` tests ran in `fast` *and again* in their own
partition. Its baseline count therefore *drops* 739 → 696 passed. That is a partition-boundary
move, **not** a removal: the union across the four partitions is **848 tests before and
after**, `fast ∩ data-noslow = ∅`, and the 43-test delta is exactly the `data, not slow` set.
Under the reading rules below, this is the one sanctioned way a passed count may fall.

Baseline after the work-unit-026 merge (`main` = `a38ca01`, warm caches — see "Caches"
below). Keep this table current: a merged work unit that adds tests must update it in
the same commit (the ruff-format file count moves with any new file):

| Command | Baseline |
|---|---|
| fast (`not gpu and not slow`) | 739 passed, 1 skipped (mpi), ~13–15 min warm |
| slow, no data | 31 passed, ~5–13 min |
| data, not slow | 43 passed, ~7 min |
| data and slow | 76 passed, 1 skipped, ~32 min |
| ruff check / format | `All checks passed!` / `173 files already formatted` |
| mypy | `Success: no issues found in 50 source files` |
| lint-imports | `Contracts: 2 kept, 0 broken` |

## Parallelism (work unit 0052)

`tools/run_gate.py` runs the four partitions in two waves. `--dist`/`-n` are chosen per
partition by resource profile; the authoritative table is `spec-0052`'s, transcribed into the
driver's `PARTITIONS` constant so a change lands in exactly one place.

| Partition | `--dist` | `-n` | Why |
|---|---|---|---|
| fast | `load` | 10 | No reference loads → low RAM. `load` spreads the 89-test `test_scheme_constants.py` group that `loadscope` would pin to one worker. |
| slow, no data | `load` | 6 | Only ~7 module groups; `load` splits the three 9-test convergence modules that would otherwise serialize. |
| data, not slow | `loadscope` | 3 | Reference loads (RAM/IO); keep a module's savepoints on one worker. RAM-bounded — calibrated. |
| data + slow | — | **1 (serial)** | **Does not scale — measured.** One test, `test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, is 1519 s of the partition's 2012 s (75 %), and no worker count splits a single test. Serial is both fastest and lowest-RAM (33:04/5.0 GiB vs `-n 2` 33:08/6.4 GiB vs `-n 4` 35:13/9.0 GiB): `EXCLAIM_APE` is loaded once instead of per worker. |

**Waves:** W1 = `fast` ‖ `data+slow`, W2 = `slow-nodata` ‖ `data-noslow`. **At most one
reference-loading partition per wave** — asserted by `_check_waves()`, and sound only because
0052 made the partitions disjoint (before that, `fast` silently carried all 43 `data` tests and
the pairing would have stacked reference loads). `data+slow` stays in a wave despite running
serially: overlapping `fast` is precisely where its parallelism comes from.

Calibration rule: each RAM-bounded cap is the largest `-n` whose **wave** peak RSS — measured
on the wave as actually run, not on the partition alone — stays under 75 % of 31 GB (≈ 23 GB).
Caps may only be lowered without new per-wave RSS evidence.

**gt4py concurrent compile — safe, no warm-up needed.** gt4py 1.1.10 wraps the whole
read-check-build-recheck of the persistent build cache in a `filelock.UnixFileLock`
(`gt4py/next/otf/compilation/compiler.py:73`, comment cites "multiple MPI ranks");
`read_data()` is re-checked *inside* the lock, so a worker blocked on a peer's build skips the
build rather than repeating it. Live in this cache: 490 lock files across 218 cache dirs. Note
`--collect-only` executes no test body and so compiles nothing — it is not a warm-up.

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

- `~/.cache/symcon/gt4py` — persistent gtfn program cache. First runs after code
  changes may recompile (minutes per variant); reruns are fast. Never point tests at
  a cold cache except where a plan explicitly says so.
- `~/.cache/symcon/icon4py-testdata` — serialized reference archives (GAUSS3D 57 MB,
  WK-torus ~1.6 GB, EXCLAIM APE **~4.0 GB compressed / 8.7 GB extracted**, JW ~14 GB,
  MCH ~11 GB). Downloaded via icon4py's own machinery on first use. The extracted APE
  figure is the load-bearing one for worker-count calibration (work unit 0052): it is what
  each reference-loading worker actually holds.
- `~/.cache/symcon/l4_reference` — the 9-day JW reference/twin/symcon trajectories
  with a sha256 manifest. **Regenerating costs ~7 h and invalidates the recorded
  bitwise results — never regenerate** unless a plan explicitly instructs it
  (none of the current plans do).
