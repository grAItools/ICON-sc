# plans/ — frozen work-unit plans

This folder holds the frozen how-tos: one plan per work unit, `plan-NNNN-<kebab>.md`.
Numbers are allocated in the document register, `development/REGISTRY.md` §1 — the
single allocator, moved there from this README in work unit 035 (TD-35.3). Plans are
written for LLM agents **weaker than the ones that built the slice**: every plan is
self-contained, restates the non-negotiable rules inline, gives exact commands with
expected outputs, and defines stop rules. Do not "improve" a work unit beyond its
stated scope — scope discipline is the main anti-drift device.

## How to use

1. Give the implementer agent the **full text of one plan file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `development/policies/review-protocol.md` plus the plan file's "Review checklist"
   section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per work unit.

## Execution order (pending work units)

| Order | Plan | Needs | Difficulty for a weak model |
|---|---|---|---|
| 1 | `plan-0020-gpu-validation.md` | a CUDA machine | low (run + record) |
| 2 | `plan-0021-ci-hardening.md` | — | low-medium (mechanical, many small edits) |
| 3 | `plan-0022-plan-hash-config-digest.md` | — | medium (touches the 0005 core; strictly specced) |
| 4 | `plan-0023-upstream-reports.md` | — | low (writing, evidence already exists) |
| 5 | `plan-0024-pr-publication.md` | push access + human | low (drafting; human presses the buttons) |
| 6 | `plan-0025-cf-multistage-t1.md` | — | **high — prefer a strong model**; plan included so scope is frozen either way |
| 7 | `plan-0030-author-phase-specs.md` | trunk decision on which phase | medium-high (design writing, heavily templated) |

Work units 0020–0024 are independent of each other except where noted inside the files.

## Numbers, naming, boundaries

The document register (allocation at assignment, strictly monotonic, no reuse, no
backfill) is `development/REGISTRY.md` §1; the old→new name remaps are §2 and §2b
there. Full naming convention and file taxonomy:
`development/policies/naming-conventions.md` and
`development/policies/document-kinds.md`; the development/docs boundary policy is
`development/policies/docs-boundary.md`; the living trunk-decision/sign-off register is
`development/REGISTRY.md` (it supersedes
`development/work/reports/report-0036-implementation-report.md` §5/§6 going forward).

## Invariants that apply to EVERY work unit (also restated inside each plan)

- Authority order on any conflict:
  `docs/architecture/symcon_architecture.md` (v1.3) >
  `development/work/specs/spec-NNNN-*.md` > `development/work/plans/plan-NNNN-*.md`.
  Never silently resolve a contradiction — record it and stop.
- Branch from `main`, name `work/NNNN-<kebab>`, verify with
  `git branch --show-current` **before every commit**. Never commit to `main`.
- **No data files in git. No dependency pin changes** (`constraints/*.txt`, `uv.lock`
  version bumps) — pins are trunk decisions. New *lower-bound* declarations are
  allowed only where a plan says so.
- **No tolerance changes anywhere.** If a test tolerance seems wrong, stop and report;
  do not edit it. (AGENTS.md rule 4: tolerance creep is how scientific divergence
  sneaks in.)
- Do not edit `docs/architecture/*`, any `development/work/specs/*.md` or executed
  plan, or another work unit's files. Merged work units' reports are historical —
  never edit them; new findings go in YOUR report.
- Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry
  appended to `development/references/lock.toml` (schema in that file's header)
  **at the moment of consultation**, with a commit SHA or tag. Pinned pair: icon4py
  v0.2.0 (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
  icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror
  (gitlab.dwd.de does not resolve).
- Commit messages end with the `Co-Authored-By:` trailer for the model used.

## The verification gate

The gate battery, baseline counts, output-reading rules, and cache notes live in
**`development/policies/verification-gates.md`** (single living source; a merged work
unit that changes any count updates that file in the same commit).

## Background reading (skim before any work unit)

- `development/work/reports/report-0036-implementation-report.md` — what was built, findings, the sign-off ledger.
- `AGENTS.md` — the working agreement (binding).
- `development/work/reports/report-0000-overview.md` — DAG and conventions; §5 names the post-slice phases,
  outlined in `development/work/proposals/`.
