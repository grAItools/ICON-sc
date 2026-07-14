# plans/ — step PLANs, task prompts, and the task-number register

This folder holds the frozen how-tos: the S-series step PLANs (`SXX_<snake>.md`) and
the N-series task prompts (`NN_<snake>.md`). Prompts are written for LLM agents
**weaker than the ones that built the slice**: every prompt is self-contained,
restates the non-negotiable rules inline, gives exact commands with expected outputs,
and defines stop rules. Do not "improve" a task beyond its stated scope — scope
discipline is the main anti-drift device.

## How to use

1. Give the implementer agent the **full text of one prompt file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `development/policies/review_protocol.md` plus the task file's "Review checklist"
   section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per task.

## Execution order

| Order | Prompt | Needs | Difficulty for a weak model |
|---|---|---|---|
| 1 | `020_gpu_validation_plan.md` | a CUDA machine | low (run + record) |
| 2 | `021_ci_hardening_plan.md` | — | low-medium (mechanical, many small edits) |
| 3 | `022_plan_hash_config_digest_plan.md` | — | medium (touches S05 core; strictly specced) |
| 4 | `023_upstream_reports_plan.md` | — | low (writing, evidence already exists) |
| 5 | `024_pr_publication_plan.md` | push access + human | low (drafting; human presses the buttons) |
| 6 | `025_cf_multistage_t1_plan.md` | — | **high — prefer a strong model**; prompt included so scope is frozen either way |
| 7 | `030_author_phase_specs_plan.md` | trunk decision on which phase | medium-high (design writing, heavily templated) |

Tasks 1–5 are independent of each other except where noted inside the files.

## Task-number register (the single allocator)

A task number is allocated by adding a row here **at assignment**, even when the prompt
text is delivered ad hoc and never committed (the row says so). Numbers are strictly
monotonic, never reused; gaps are never backfilled. On a collision, the first-registered
number wins and the latecomer takes the next free one. Full naming convention, file
taxonomy, and forward SPEC/STATUS templates live in
`development/policies/naming_conventions.md` and
`development/policies/records_and_liveness.md`; the development/docs boundary policy is
`development/policies/docs_boundary.md`; the living trunk-decision/sign-off register is
`development/REGISTRY.md` (it supersedes `development/records/036_implementation_report_record.md`
§5/§6 going forward).

| N | Task | Prompt | Status | Deliverable |
|---|---|---|---|---|
| 10 | review protocol | `development/policies/review_protocol.md` (moved in task 33) | living protocol | — |
| 20 | gpu validation | `020_gpu_validation_plan.md` | pending | `records/20_gpu_validation_REPORT.md` |
| 21 | ci hardening | `021_ci_hardening_plan.md` | pending | `records/21_ci_hardening_REPORT.md` |
| 22 | plan-hash config digest | `022_plan_hash_config_digest_plan.md` | pending | `records/22_plan_hash_REPORT.md` |
| 23 | upstream reports | `023_upstream_reports_plan.md` | pending | `records/upstream/` |
| 24 | pr publication | `024_pr_publication_plan.md` | pending | `records/prs/` |
| 25 | cf multistage t1 | `025_cf_multistage_t1_plan.md` | pending | `records/25_cf_multistage_REPORT.md` |
| 26 | gridgen integration | ad hoc (not committed) | executed | `records/026_gridgen_integration_record.md` |
| 27 | docs plan | ad hoc (not committed) | executed | `records/027_docs_plan_record/27_docs_plan.md` |
| 28 | docs implementation | `028_docs_implementation_plan.md` | executed | `records/028_docs_implementation_record.md` |
| 29 | plan-structure proposal | ad hoc (not committed) | executed | `records/029_plan_structure_record/29_plan_structure.md` |
| 30 | author phase specs | `030_author_phase_specs_plan.md` | pending | `records/30_specs_<phase>_REPORT.md` |
| 31 | plan-structure migration | 29 proposal §8 (liftable spec) | executed | `records/031_plan_structure_migration_record.md` |
| 32 | structure evaluation | ad hoc (not committed) | executed | `records/032_docs_development_structure_record/` |
| 33 | structure migration | `033_structure_migration_plan.md` | executed | `records/033_structure_migration_record/` |
| 34 | naming-convention iteration | ad hoc (not committed) | executed | `records/034_naming_iteration_record/34_naming_iteration.md` |
| 35 | naming migration | `035_naming_migration_plan.md` | pending | `records/035_naming_migration_record/` |

## Invariants that apply to EVERY task (also restated inside each prompt)

- Authority order on any conflict:
  `docs/architecture/symcon_architecture.md` (v1.3) > `development/specs/SXX_*.md`
  > `development/plans/SXX_*.md` > these prompts. Never silently resolve a
  contradiction — record it and stop.
- Branch from `main`, name `task/<prompt-number>-<short-name>`, verify with
  `git branch --show-current` **before every commit**. Never commit to `main`.
- **No data files in git. No dependency pin changes** (`constraints/*.txt`, `uv.lock`
  version bumps) — pins are trunk decisions. New *lower-bound* declarations are
  allowed only where a prompt says so.
- **No tolerance changes anywhere.** If a test tolerance seems wrong, stop and report;
  do not edit it. (AGENTS.md rule 6: tolerance creep is how scientific divergence
  sneaks in.)
- Do not edit `docs/architecture/*`, any `development/specs/*.md` or step PLAN
  (`development/plans/SXX_*.md`), or another task's files. Completed steps'
  `STATUS.md` records are historical — never edit them; new findings go in YOUR
  task report.
- Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry
  appended to `REFERENCES.lock` (schema in that file's header) **at the moment of
  consultation**, with a commit SHA or tag. Pinned pair: icon4py v0.2.0
  (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
  icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror
  (gitlab.dwd.de does not resolve).
- Commit messages end with the `Co-Authored-By:` trailer for the model used.

## The verification gate

The gate battery, baseline counts, output-reading rules, and cache notes live in
**`development/policies/verification_gates.md`** (single living source; a merged task
that changes any count updates that file in the same commit).

## Background reading (skim before any task)

- `development/records/036_implementation_report_record.md` — what was built, findings, the sign-off ledger.
- `AGENTS.md` — the working agreement (binding).
- `development/records/000_overview_record.md` — DAG and conventions; §5 names the post-slice phases,
  outlined in `development/ideas/`.
