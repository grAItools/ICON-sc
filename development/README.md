# development/ — repo-internal process memory

This tree is the repo-internal process memory: policies, registers, the work-document
lifecycle (proposals, specs, plans, reports), ADRs, and reference cards for the
agent-driven implementation. It is not a Sphinx source and is never published — see
`policies/docs-boundary.md`.

## Naming convention (TD-50.1/ADR-0006, TD-51.1–2/ADR-0007)

Every filename in this tree is kebab-case (`README.md` and `lock.toml` excepted).
Each work unit's documents live in one folder `work/<NNNN>-<slug>/` holding the
bare-kind files `proposal.md` / `spec.md` / `plan.md` / `report.md` (only those that
exist); a report's extra artifacts live in the unit's `artifacts/` subfolder. NNNN is
a four-digit work id allocated in `REGISTRY.md` §1 at assignment; one folder per work
unit, the id and slug encoded once in the folder name (TD-54.1). ADRs number
independently: `ADRs/NNNN-<kebab-title>.md`, own sequence from 0000, cited `ADR-NNNN`.
Exempt from the `<NNNN>-<slug>` scheme (not from kebab-case): `policies/*` (unnumbered),
all `README.md`, `REGISTRY.md`, `archive/*` contents. Historical names (`S08_…`,
`26_…_REPORT`, `008_graupel_component_spec.md`, the pre-0054 by-kind paths
`work/specs/spec-…`) translate via the remap tables in `REGISTRY.md` §2/§2b/§2c/§2d.

## Lifecycle

**proposal** (living until graduated) → **spec** (the frozen contract: requirements,
frozen interfaces, acceptance criteria) → **plan** (the frozen work instructions an
agent executes) → **report** (the frozen account of what actually happened, written at
merge) — all four as `proposal.md` / `spec.md` / `plan.md` / `report.md` in the unit's
`work/<NNNN>-<slug>/` folder.
Liveness rules per kind: `policies/document-kinds.md`. Cross-cutting instruments:
`policies/` (standing rules, living, trunk-gated), `ADRs/` (the reasoning behind
structural decisions), `REGISTRY.md` (work ids + trunk decisions and sign-offs).
`archive/` holds superseded or irrelevant documents of any kind, kept for historical
reference — dead, never authoritative.

| Folder / file | What |
|---|---|
| `REGISTRY.md` | living registry: work ids (§1), the old→new remap tables (§2–§2d), trunk decisions and sign-offs (the only living file at this level) |
| `policies/` | living rules: workflow, naming, kinds/liveness, gates, mining, review, docs boundary, repo layout, code style |
| `ADRs/` | architecture decision records, `NNNN-<kebab-title>.md` (Nygard format, own sequence from 0000) |
| `work/<NNNN>-<slug>/` | one folder per work unit holding its `proposal.md` / `spec.md` / `plan.md` / `report.md` (only those that exist) + optional `artifacts/`; e.g. `0000-overview/report.md`, `0036-implementation-report/report.md`, the P2–P7 phase proposals (`0037-…`–`0042-…`). Lifecycle + how plans are used: `work/README.md` |
| `archive/` | dead documents of any kind; nothing here is authoritative |
| `references/` | per-source reference cards + `lock.toml` (the machine provenance ledger, append-only) + gitignored `local/` for non-redistributable documents |

Where to start:

- **Implementing** a work unit: its `spec.md` and `plan.md` in `work/<NNNN>-<slug>/`,
  workflow in `policies/agent-workflow.md`.
- **Writing code**: `policies/coding-conventions.md` (the style rules the linter can't
  enforce) alongside the gate battery in `policies/verification-gates.md`.
- **Reviewing**: `policies/review-protocol.md` plus the work unit's own review
  checklist.
- **Deciding** (trunk/human): `REGISTRY.md` for the pending rows; `ADRs/` for the
  reasoning behind structural decisions.
- **History of the S01–S14 slice**: the per-unit `report.md` files, overview in
  `work/0000-overview/report.md`.
