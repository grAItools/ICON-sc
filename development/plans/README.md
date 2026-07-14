# plans/ — frozen work-unit plans

This folder holds the frozen how-tos: one plan per work unit, `NNN_<slug>_plan.md`.
Numbers are allocated in the document register, `development/REGISTRY.md` §1 — the
single allocator, moved there from this README in work unit 035 (TD-35.3). Plans are
written for LLM agents **weaker than the ones that built the slice**: every plan is
self-contained, restates the non-negotiable rules inline, gives exact commands with
expected outputs, and defines stop rules. Do not "improve" a work unit beyond its
stated scope — scope discipline is the main anti-drift device.

## How to use

1. Give the implementer agent the **full text of one plan file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `development/policies/review_protocol.md` plus the plan file's "Review checklist"
   section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per work unit.

## Execution order (pending work units)

| Order | Plan | Needs | Difficulty for a weak model |
|---|---|---|---|
| 1 | `020_gpu_validation_plan.md` | a CUDA machine | low (run + record) |
| 2 | `021_ci_hardening_plan.md` | — | low-medium (mechanical, many small edits) |
| 3 | `022_plan_hash_config_digest_plan.md` | — | medium (touches the 005 core; strictly specced) |
| 4 | `023_upstream_reports_plan.md` | — | low (writing, evidence already exists) |
| 5 | `024_pr_publication_plan.md` | push access + human | low (drafting; human presses the buttons) |
| 6 | `025_cf_multistage_t1_plan.md` | — | **high — prefer a strong model**; plan included so scope is frozen either way |
| 7 | `030_author_phase_specs_plan.md` | trunk decision on which phase | medium-high (design writing, heavily templated) |

Work units 020–024 are independent of each other except where noted inside the files.

## Numbers, naming, boundaries

The document register (allocation at assignment, strictly monotonic, no reuse, no
backfill) is `development/REGISTRY.md` §1; the old→new name remap is §2 there. Full
naming convention and file taxonomy:
`development/policies/naming_conventions.md` and
`development/policies/records_and_liveness.md`; the development/docs boundary policy is
`development/policies/docs_boundary.md`; the living trunk-decision/sign-off register is
`development/REGISTRY.md` (it supersedes
`development/records/036_implementation_report_record.md` §5/§6 going forward).

## Invariants that apply to EVERY work unit (also restated inside each plan)

- Authority order on any conflict:
  `docs/architecture/symcon_architecture.md` (v1.3) > `development/specs/NNN_*_spec.md`
  > `development/plans/NNN_*_plan.md`. Never silently resolve a contradiction —
  record it and stop.
- Branch from `main`, name `work/NNN-<slug>`, verify with
  `git branch --show-current` **before every commit**. Never commit to `main`.
- **No data files in git. No dependency pin changes** (`constraints/*.txt`, `uv.lock`
  version bumps) — pins are trunk decisions. New *lower-bound* declarations are
  allowed only where a plan says so.
- **No tolerance changes anywhere.** If a test tolerance seems wrong, stop and report;
  do not edit it. (AGENTS.md rule 4: tolerance creep is how scientific divergence
  sneaks in.)
- Do not edit `docs/architecture/*`, any `development/specs/*.md` or executed plan, or
  another work unit's files. Merged work units' records are historical — never edit
  them; new findings go in YOUR record.
- Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry
  appended to `REFERENCES.lock` (schema in that file's header) **at the moment of
  consultation**, with a commit SHA or tag. Pinned pair: icon4py v0.2.0
  (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
  icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror
  (gitlab.dwd.de does not resolve).
- Commit messages end with the `Co-Authored-By:` trailer for the model used.

## The verification gate

The gate battery, baseline counts, output-reading rules, and cache notes live in
**`development/policies/verification_gates.md`** (single living source; a merged work
unit that changes any count updates that file in the same commit).

## Background reading (skim before any work unit)

- `development/records/036_implementation_report_record.md` — what was built, findings, the sign-off ledger.
- `AGENTS.md` — the working agreement (binding).
- `development/records/000_overview_record.md` — DAG and conventions; §5 names the post-slice phases,
  outlined in `development/ideas/`.
