# records/ — outcome documents, frozen at merge

Every outcome document of a merged work unit lives here (liveness rules and templates:
`development/policies/records_and_liveness.md`). Shapes:

- **Step records:** `SXX_<snake>/STATUS.md` — one folder per S-series step, plus an
  optional untracked `SXX_<snake>/artifacts/` (gitignored; every artifact is cited in
  its STATUS *with its regeneration command*, never as a bare path).
- **Task execution reports:** flat `NN_<snake>_REPORT.md`.
- **Document-deliverables:** subdirectory `NN_<snake>/NN_<snake>.md` when the
  deliverable *is a document* (design docs, proposals) or spans multiple files
  (sidecars); thematic subdirectories for external-facing drafts, created only by
  their owning task.
- **Slice-level records:** `00_OVERVIEW.md` (the S01–S14 implementation plan: agent
  contract, dependency DAG, lanes) and `IMPLEMENTATION_REPORT.md` (the slice process
  record; its §5/§6 are superseded going forward by `development/REGISTRY.md`).

## Step records (S01–S14)

| Record | Step |
|---|---|
| `S01_repo_scaffold/STATUS.md` | repo scaffold |
| `S02_core_state_contracts/STATUS.md` | core state + contracts |
| `S03_component_abi_t0/STATUS.md` | component ABI + wrappers + T0 |
| `S04_coupling_algebra/STATUS.md` | coupling algebra + DynamicalCore |
| `S05_vault_plan_t1/STATUS.md` | vault + plan compiler + T1 |
| `S06_vertical_grid_thermo/STATUS.md` | vertical grid + thermo |
| `S07_satad_component/STATUS.md` | satad component |
| `S08_graupel_component/STATUS.md` | graupel component |
| `S09_scm_composition/STATUS.md` | SCM composition |
| `S10_ftier_column_gradients/STATUS.md` | F-tier column + gradients |
| `S11_icon_grid_metrics/STATUS.md` | ICON grid + metrics |
| `S12_nonhydro_hosting/STATUS.md` | NonhydroSolver hosting |
| `S13_diffusion_jw_l4/STATUS.md` | diffusion + JW baroclinic L4 |
| `S14_plan_through_dycore/STATUS.md` | plan through the dycore |

## Task records

| Entry | Task | Kind |
|---|---|---|
| `026_gridgen_integration_record.md` | 26 (prompt ad hoc, not committed) | execution report |
| `027_docs_plan_record/27_docs_plan.md` | 27 (prompt ad hoc, not committed) | design document — docs-stack evaluation and plan; TD-27.1–3 in `development/REGISTRY.md` |
| `028_docs_implementation_record.md` | 28 (`../plans/028_docs_implementation_plan.md`) | execution report |
| `029_plan_structure_record/29_plan_structure.md` | 29 (prompt ad hoc, not committed) | design document — plan/memory structure analysis + proposal; TD-29.x in `development/REGISTRY.md`; §8 is the liftable task-31 spec |
| `031_plan_structure_migration_record.md` | 31 (prompt: 29 proposal §8) | execution report |
| `032_docs_development_structure_record/32_docs_development_structure.md` | 32 (prompt ad hoc, not committed) | design document — development-tree evaluation; decisions implemented by task 33 |
| `033_structure_migration_record/REPORT.md` | 33 (`../plans/033_structure_migration_plan.md`) | execution report (+ sidecar `layout_doc_revision.diff`, TD-33.4) |
| `upstream/` | 23 (unexecuted) | external-facing drafts (icon4py issue texts) — created by task 23, do not pre-create |
| `prs/` | 24 (unexecuted) | external-facing drafts (per-step PR bodies, publish script) — created by task 24, do not pre-create |
