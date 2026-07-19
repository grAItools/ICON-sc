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
