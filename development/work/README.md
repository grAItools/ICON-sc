# work/ — the work-document lifecycle

One work unit, one four-digit id (allocated in `../REGISTRY.md` §1 at assignment), one
folder `<NNNN>-<kebab-slug>/`, one lifecycle: **proposal** (living until graduated) →
**spec** (frozen contract) → **plan** (frozen instructions) → **report** (frozen account,
written at merge). All four live as bare-kind files inside the unit folder —
`proposal.md` / `spec.md` / `plan.md` / `report.md` — only those that exist.

Naming (TD-54.1, superseding the per-kind-subfolder scheme of TD-50.1/TD-51.2): the id and
slug are encoded once, in the folder name; e.g. `0005-vault-plan-t1/` holds `spec.md` /
`plan.md` / `report.md`. A report's extra artifacts (tracked sidecars or untracked generated
files) live in the unit's `artifacts/` subfolder — an `artifacts/` holding ONLY untracked
files gets its own `.gitignore` line. The work-id sequence is independent of everything
outside `work/` (ADRs number separately in `../ADRs/`). Branches: `work/NNNN-<kebab>`.
Liveness rules and templates: `../policies/document-kinds.md`; the full naming rule:
`../policies/naming-conventions.md`; historical names (incl. the pre-0054 by-kind paths):
`../REGISTRY.md` §2/§2b/§2c/§2d.

**Proposals** carry a `Status:` header above the title:
`proposed / accepted / accepted-roadmap / rejected / superseded / graduated → spec NNNN`.

## How a work unit is executed

Give the implementer agent the **full text of one plan file**; when it reports done, give a
**fresh** agent `../policies/review-protocol.md` plus that plan's "Review checklist"; iterate
implementer ↔ reviewer until the verdict is `approve`; merge only then. One branch, one PR per
work unit. Full sequence: `../policies/agent-workflow.md`; the gate battery and baselines:
`../policies/verification-gates.md`.

## Invariants that apply to EVERY work unit (also restated inside each plan)

The non-negotiable rules; a plan restates them inline because it is written for an agent
weaker than the one that built the slice. (Durable content consolidated here from the
former per-kind `plans/README.md` under TD-54.1; `../REGISTRY.md` §2d bridges the old path.)

- Authority order on any conflict:
  `docs/architecture/icon-sc_architecture.md` (v1.3) > `work/<NNNN>-<slug>/spec.md` >
  `work/<NNNN>-<slug>/plan.md`. Never silently resolve a contradiction — record it and stop.
- Branch from `main`, name `work/NNNN-<kebab>`, verify with `git branch --show-current`
  **before every commit**. Never commit to `main`.
- **No data files in git. No dependency pin changes** (`constraints/*.txt`, `uv.lock`
  version bumps) — pins are trunk decisions. New *lower-bound* declarations are allowed only
  where a plan says so.
- **No tolerance changes anywhere.** If a test tolerance seems wrong, stop and report; do not
  edit it. (AGENTS.md rule 4: tolerance creep is how scientific divergence sneaks in.)
- Do not edit `docs/architecture/*`, any other work unit's `spec.md` or executed `plan.md`,
  or another work unit's files. Merged work units' reports are historical — never edit them;
  new findings go in YOUR report.
- Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry appended
  to `../references/lock.toml` (schema in that file's header) **at the moment of
  consultation**, with a commit SHA or tag. Pinned pair: icon4py v0.2.0
  (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
  icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror (gitlab.dwd.de does not
  resolve).
- Commit messages end with the `Co-Authored-By:` trailer for the model used.

## Execution order (pending work units)

| Order | Plan | Needs | Difficulty for a weak model |
|---|---|---|---|
| 1 | `0020-gpu-validation/plan.md` | a CUDA machine | low (run + record) |
| 2 | `0021-ci-hardening/plan.md` | — | low-medium (mechanical, many small edits) |
| 3 | `0022-plan-hash-config-digest/plan.md` | — | medium (touches the 0005 core; strictly specced) |
| 4 | `0023-upstream-reports/plan.md` | — | low (writing, evidence already exists) |
| 5 | `0024-pr-publication/plan.md` | push access + human | low (drafting; human presses the buttons) |
| 6 | `0025-cf-multistage-t1/plan.md` | — | **high — prefer a strong model**; plan included so scope is frozen either way |
| 7 | `0030-author-phase-specs/plan.md` | trunk decision on which phase | medium-high (design writing, heavily templated) |

Work units 0020–0024 are independent of each other except where noted inside the files.

## Background reading (skim before any work unit)

- `0036-implementation-report/report.md` — what was built across the S01–S14 slice, findings,
  the sign-off ledger (its §5/§6 superseded going forward by `../REGISTRY.md`).
- `AGENTS.md` (repo root) — the working agreement (binding).
- `0000-overview/report.md` — the S01–S14 DAG, agent contract, and lanes; §5 names the
  post-slice phases, outlined in the `0037-…`–`0042-…` proposals.
