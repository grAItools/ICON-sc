# plan/prompts — task prompts for the post-slice work

Ready-to-use prompts for the next design and development tasks. They are written for
LLM agents **weaker than the ones that built the slice**: every prompt is
self-contained, restates the non-negotiable rules inline, gives exact commands with
expected outputs, and defines stop rules. Do not "improve" a task beyond its stated
scope — scope discipline is the main anti-drift device.

## How to use

1. Give the implementer agent the **full text of one prompt file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `10_REVIEW_PROTOCOL.md` plus the task file's "Review checklist" section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per task.

## Execution order

| Order | Prompt | Needs | Difficulty for a weak model |
|---|---|---|---|
| 1 | `20_gpu_validation.md` | a CUDA machine | low (run + record) |
| 2 | `21_ci_hardening.md` | — | low-medium (mechanical, many small edits) |
| 3 | `22_plan_hash_config_digest.md` | — | medium (touches S05 core; strictly specced) |
| 4 | `23_upstream_reports.md` | — | low (writing, evidence already exists) |
| 5 | `24_pr_publication.md` | push access + human | low (drafting; human presses the buttons) |
| 6 | `25_cf_multistage_t1.md` | — | **high — prefer a strong model**; prompt included so scope is frozen either way |
| 7 | `30_author_phase_specs.md` | trunk decision on which phase | medium-high (design writing, heavily templated) |

Tasks 1–5 are independent of each other except where noted inside the files.

## Task-number register (the single allocator)

A task number is allocated by adding a row here **at assignment**, even when the prompt
text is delivered ad hoc and never committed (the row says so). Numbers are strictly
monotonic, never reused; gaps are never backfilled. On a collision, the first-registered
number wins and the latecomer takes the next free one. Full naming convention, file
taxonomy, forward SPEC/STATUS templates, and the plan/docs boundary policy live in
`plan/README.md`; the living trunk-decision/sign-off register is
`plan/TRUNK_DECISIONS.md` (it supersedes `plan/IMPLEMENTATION_REPORT.md` §5/§6 going
forward).

| N | Task | Prompt | Status | Deliverable |
|---|---|---|---|---|
| 10 | review protocol | `10_REVIEW_PROTOCOL.md` | living protocol | — |
| 20 | gpu validation | `20_gpu_validation.md` | pending | `reports/20_gpu_validation_REPORT.md` |
| 21 | ci hardening | `21_ci_hardening.md` | pending | `reports/21_ci_hardening_REPORT.md` |
| 22 | plan-hash config digest | `22_plan_hash_config_digest.md` | pending | `reports/22_plan_hash_REPORT.md` |
| 23 | upstream reports | `23_upstream_reports.md` | pending | `reports/upstream/` |
| 24 | pr publication | `24_pr_publication.md` | pending | `reports/prs/` |
| 25 | cf multistage t1 | `25_cf_multistage_t1.md` | pending | `reports/25_cf_multistage_REPORT.md` |
| 26 | gridgen integration | ad hoc (not committed) | executed | `reports/26_gridgen_integration_REPORT.md` |
| 27 | docs plan | ad hoc (not committed) | executed | `reports/27_docs_plan/27_docs_plan.md` |
| 28 | docs implementation | `28_docs_implementation.md` | executed | `reports/28_docs_implementation_REPORT.md` |
| 29 | plan-structure proposal | ad hoc (not committed) | executed | `reports/29_plan_structure/29_plan_structure.md` |
| 30 | author phase specs | `30_author_phase_specs.md` | pending | `reports/30_specs_<phase>_REPORT.md` |
| 31 | plan-structure migration | 29 proposal §8 (liftable spec) | executed | `reports/31_plan_structure_migration_REPORT.md` |
| 32 | development-structure evaluation | ad hoc (not committed) | executed | `reports/32_docs_development_structure/32_docs_development_structure.md` |
| 33 | structure migration (plan → development/) | `33_structure_migration.md` | pending | `development/records/33_structure_migration/REPORT.md` (born in the new tree) |

## Invariants that apply to EVERY task (also restated inside each prompt)

- Authority order on any conflict:
  `docs/architecture/symcon_architecture.md` (v1.3) > step `SPEC.md` > step `PLAN.md`
  > these prompts. Never silently resolve a contradiction — record it and stop.
- Branch from `main`, name `task/<prompt-number>-<short-name>`, verify with
  `git branch --show-current` **before every commit**. Never commit to `main`.
- **No data files in git. No dependency pin changes** (`constraints/*.txt`, `uv.lock`
  version bumps) — pins are trunk decisions. New *lower-bound* declarations are
  allowed only where a prompt says so.
- **No tolerance changes anywhere.** If a test tolerance seems wrong, stop and report;
  do not edit it. (AGENTS.md rule 6: tolerance creep is how scientific divergence
  sneaks in.)
- Do not edit `docs/architecture/*`, any `plan/steps/*/SPEC.md` or `PLAN.md`, or
  another task's files. Completed steps' `STATUS.md` files are historical records —
  never edit them; new findings go in YOUR task report.
- Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry
  appended to `REFERENCES.lock` (schema in that file's header) **at the moment of
  consultation**, with a commit SHA or tag. Pinned pair: icon4py v0.2.0
  (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
  icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror
  (gitlab.dwd.de does not resolve).
- Commit messages end with the `Co-Authored-By:` trailer for the model used.

## The verification gate (run via `uv run`, from the repo root)

Every task must leave ALL of these green. Run them exactly as written; where a runtime
exceeds your shell limit, split by marker or by file — never skip a partition.

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

Baseline after the task-26 merge (`main` = `a38ca01`, warm caches — see "Caches"
below). Keep this table current: a merged task that adds tests must update it in
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
  task's scope, report honestly and stop.

## Caches (read-only context; do not delete or regenerate)

- `~/.cache/symcon/gt4py` — persistent gtfn program cache. First runs after code
  changes may recompile (minutes per variant); reruns are fast. Never point tests at
  a cold cache except where a prompt explicitly says so.
- `~/.cache/symcon/icon4py-testdata` — serialized reference archives (GAUSS3D 57 MB,
  WK-torus ~1.6 GB, EXCLAIM APE ~4 GB, JW ~14 GB, MCH ~11 GB). Downloaded via
  icon4py's own machinery on first use.
- `~/.cache/symcon/l4_reference` — the 9-day JW reference/twin/symcon trajectories
  with a sha256 manifest. **Regenerating costs ~7 h and invalidates the recorded
  bitwise results — never regenerate** unless a prompt explicitly instructs it
  (none of the current prompts do).

## Background reading (skim before any task)

- `plan/IMPLEMENTATION_REPORT.md` — what was built, findings, the sign-off ledger.
- `AGENTS.md` — the working agreement (binding).
- `plan/00_OVERVIEW.md` — DAG and conventions; §5 names the post-slice phases,
  outlined in `plan/outlines/`.
