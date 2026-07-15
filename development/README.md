# development/ — repo-internal process memory

This tree is the repo-internal process memory: policies, registers, the work-document
lifecycle (proposals, specs, plans, reports), ADRs, and reference cards for the
agent-driven implementation. It is not a Sphinx source and is never published — see
`policies/docs-boundary.md`.

## Naming convention (TD-50.1, ADR-0006)

Work documents are named `<kind>-<NNNN>-<kebab-slug>.md` — or `report-NNNN-<kebab>/`
for multi-file deliverables (inner files keep their names). NNNN is a four-digit work
id allocated in `REGISTRY.md` §1 at assignment; one number per work unit, shared
across its proposal/spec/plan/report; kind prefix = singular of the `work/` subfolder.
ADRs number independently: `ADRs/NNNN-<kebab-title>.md`, own sequence from 0000, cited
`ADR-NNNN`. Exempt: `policies/*` (snake_case, unnumbered), all `README.md`,
`REGISTRY.md`, `archive/*` contents. Historical names (`S08_…`, `26_…_REPORT`,
`008_graupel_component_spec.md`) translate via the remap tables in `REGISTRY.md`
§2/§2b.

## Lifecycle

**proposal** (`work/proposals/`, living until graduated) → **spec** (`work/specs/`,
the frozen contract: requirements, frozen interfaces, acceptance criteria) → **plan**
(`work/plans/`, the frozen work instructions an agent executes) → **report**
(`work/reports/`, the frozen account of what actually happened, written at merge).
Liveness rules per kind: `policies/document-kinds.md`. Cross-cutting instruments:
`policies/` (standing rules, living, trunk-gated), `ADRs/` (the reasoning behind
structural decisions), `REGISTRY.md` (work ids + trunk decisions and sign-offs).
`archive/` holds superseded or irrelevant documents of any kind, kept for historical
reference — dead, never authoritative.

| Folder / file | What |
|---|---|
| `REGISTRY.md` | living registry: work ids (§1), the old→new remap tables (§2, §2b), trunk decisions and sign-offs (the only living file at this level) |
| `policies/` | living rules: workflow, naming, kinds/liveness, gates, mining, review, docs boundary, repo layout |
| `ADRs/` | architecture decision records, `NNNN-<kebab-title>.md` (Nygard format, own sequence from 0000) |
| `work/proposals/` | future proposals, `proposal-NNNN-<kebab>.md`; the migrated phase outlines P2–P7 (0037–0042) |
| `work/specs/` | frozen work-unit contracts, `spec-NNNN-<kebab>.md` |
| `work/plans/` | frozen work-unit plans, `plan-NNNN-<kebab>.md`; `README.md` = how plans are used |
| `work/reports/` | outcome documents frozen at merge, `report-NNNN-<kebab>{.md,/}`: STATUS files, execution reports, `report-0000-overview.md`, `report-0036-implementation-report.md` |
| `archive/` | dead documents of any kind; nothing here is authoritative |
| `references/` | per-source reference cards + `lock.toml` (the machine provenance ledger, append-only) + gitignored `local/` for non-redistributable documents |

Where to start:

- **Implementing** a work unit: its spec in `work/specs/` and plan in `work/plans/`,
  workflow in `policies/agent-workflow.md`.
- **Reviewing**: `policies/review-protocol.md` plus the work unit's own review
  checklist.
- **Deciding** (trunk/human): `REGISTRY.md` for the pending rows; `ADRs/` for the
  reasoning behind structural decisions.
- **History of the S01–S14 slice**: `work/reports/`, overview in
  `work/reports/report-0000-overview.md`.
