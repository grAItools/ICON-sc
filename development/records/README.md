# plan/prompts/reports — task deliverables index

Three kinds of files live here (taxonomy: `plan/README.md` §1). Naming rule
(`plan/README.md` §2): flat `NN_<snake>_REPORT.md` for task *execution reports*; a
subdirectory `NN_<snake>/NN_<snake>.md` when the deliverable *is a document* (design
docs, proposals) or spans multiple files; thematic subdirectories for external-facing
drafts, created only by their owning task.

| Entry | Task | Kind |
|---|---|---|
| `26_gridgen_integration_REPORT.md` | 26 (prompt ad hoc, not committed) | execution report |
| `27_docs_plan/27_docs_plan.md` | 27 (prompt ad hoc, not committed) | design document — docs-stack evaluation and plan; TD-27.1–3 in `plan/TRUNK_DECISIONS.md` |
| `28_docs_implementation_REPORT.md` | 28 (`../28_docs_implementation.md`) | execution report |
| `29_plan_structure/29_plan_structure.md` | 29 (prompt ad hoc, not committed) | design document — plan/memory structure analysis + proposal; TD-29.x in `plan/TRUNK_DECISIONS.md`; §8 is the liftable task-31 spec |
| `31_plan_structure_migration_REPORT.md` | 31 (prompt: 29 proposal §8) | execution report |
| `upstream/` | 23 (unexecuted) | external-facing drafts (icon4py issue texts) — created by task 23, do not pre-create |
| `prs/` | 24 (unexecuted) | external-facing drafts (per-step PR bodies, publish script) — created by task 24, do not pre-create |
