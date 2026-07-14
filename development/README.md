# development/ — repo-internal process memory

This tree is the repo-internal process memory: policies, registers, specs, plans,
records, ideas, and reference cards for the agent-driven implementation. It is not a
Sphinx source and is never published — see `policies/docs_boundary.md`.

## Naming convention (TD-35.1, adr 046)

Lifecycle documents are named `NNN_<slug>_<kind>.md` — or `NNN_<slug>_<kind>/` for
multi-file deliverables (inner files keep their names). NNN is a three-digit global
sequence allocated in `REGISTRY.md` §1 at assignment; one number per work unit, shared
across its idea/spec/plan/record; kind suffix = singular folder name (`idea`, `spec`,
`plan`, `record`, `adr`). Exempt: `policies/*` (snake_case, unnumbered), all
`README.md`, `REGISTRY.md`, `archive/*` contents. Historical names (`S08_…`,
`26_…_REPORT`, `P2_…`) translate via the remap table in `REGISTRY.md` §2.

## Lifecycle

**idea** (`ideas/`, living until graduated) → **spec** (`specs/`, the frozen contract:
requirements, frozen interfaces, acceptance criteria) → **plan** (`plans/`, the frozen
work instructions an agent executes) → **record** (`records/`, the frozen account of
what actually happened, written at merge). Liveness rules per kind:
`policies/records_and_liveness.md`. Cross-cutting instruments: `policies/` (standing
rules, living, trunk-gated), `adr/` (the reasoning behind structural decisions),
`REGISTRY.md` (document numbers + trunk decisions and sign-offs). `archive/` holds
superseded or irrelevant documents kept for historical reference — dead, never
authoritative.

| Folder / file | What |
|---|---|
| `REGISTRY.md` | living registry: document numbers (§1), the old→new remap table (§2), trunk decisions and sign-offs (the only living file at this level) |
| `policies/` | living rules: workflow, naming, liveness, gates, mining, review, docs boundary, repo layout |
| `adr/` | architecture decision records, `NNN_<slug>_adr.md` (Nygard format) |
| `ideas/` | future proposals, `NNN_<slug>_idea.md`; the migrated phase outlines P2–P7 (037–042) |
| `specs/` | frozen work-unit contracts, `NNN_<slug>_spec.md` |
| `plans/` | frozen work-unit plans, `NNN_<slug>_plan.md`; `README.md` = how plans are used |
| `records/` | outcome documents frozen at merge, `NNN_<slug>_record{.md,/}`: STATUS files, execution reports, `000_overview_record.md`, `036_implementation_report_record.md` |
| `archive/` | documents with no ongoing relevance; nothing here is authoritative |
| `references/` | per-source reference cards + gitignored `local/` for non-redistributable documents |

Where to start:

- **Implementing** a work unit: its spec in `specs/` and plan in `plans/`,
  workflow in `policies/agent_workflow.md`.
- **Reviewing**: `policies/review_protocol.md` plus the work unit's own review
  checklist.
- **Deciding** (trunk/human): `REGISTRY.md` for the pending rows; `adr/` for the
  reasoning behind structural decisions.
- **History of the S01–S14 slice**: `records/`, overview in
  `records/000_overview_record.md`.
