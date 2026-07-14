# development/ — repo-internal process memory

This tree is the repo-internal process memory: policies, decisions, specs, plans,
records, ideas, and reference cards for the agent-driven implementation. It is not a
Sphinx source and is never published — see `policies/docs_boundary.md`.

| Folder / file | What |
|---|---|
| `REGISTRY.md` | living trunk-decision and sign-off register (the only living file at this level) |
| `policies/` | living rules: workflow, naming, liveness, gates, mining, review protocol, docs boundary |
| `adr/` | architecture decision records, `NNNN-<kebab-title>.md` (Nygard format) |
| `ideas/` | future proposals; the migrated phase outlines P2–P7 |
| `specs/` | frozen step/feature contracts, `SXX_<snake>.md` |
| `plans/` | frozen step PLANs + task prompts; `README.md` is the task-number register |
| `records/` | outcome documents, frozen at merge: STATUS files, task reports, `00_OVERVIEW.md`, `IMPLEMENTATION_REPORT.md` |
| `archive/` | documents with no ongoing relevance; nothing here is authoritative |
| `references/` | per-source reference cards + gitignored `local/` for non-redistributable documents |

Where to start:

- **Implementing** a step/task: its spec in `specs/` and plan/prompt in `plans/`,
  workflow in `policies/agent_workflow.md`.
- **Reviewing**: `policies/review_protocol.md` plus the task's own review checklist.
- **Deciding** (trunk/human): `REGISTRY.md` for the pending rows; `adr/` for the
  reasoning behind structural decisions.
- **History of the S01–S14 slice**: `records/`, overview in `records/000_overview_record.md`.
