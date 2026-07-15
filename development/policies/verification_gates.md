# verification_gates — the gate battery, baselines, and output-reading rules

Scope: the verification gate every work unit must leave green, its baseline counts, and
the rules for reading gate output. Keep-current rule: a merged work unit that changes
any count updates this file in the same commit.

## The verification gate (run via `uv run`, from the repo root)

Every work unit must leave ALL of these green. Run them exactly as written; where a
runtime exceeds your shell limit, split by marker or by file — never skip a partition.

```
uv run pytest packages -m "not gpu and not slow" -q
uv run pytest packages -m "slow and not gpu and not data" -q
uv run pytest packages -m "data and not slow and not gpu" -q
uv run pytest packages -m "data and slow and not gpu" -q
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict -p symcon.core
uv run lint-imports
```

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
  WK-torus ~1.6 GB, EXCLAIM APE ~4 GB, JW ~14 GB, MCH ~11 GB). Downloaded via
  icon4py's own machinery on first use.
- `~/.cache/symcon/l4_reference` — the 9-day JW reference/twin/symcon trajectories
  with a sha256 manifest. **Regenerating costs ~7 h and invalidates the recorded
  bitwise results — never regenerate** unless a plan explicitly instructs it
  (none of the current plans do).
