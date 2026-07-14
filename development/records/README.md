# records/ — outcome documents, frozen at merge

Every outcome document of a merged work unit lives here (liveness rules and templates:
`development/policies/records_and_liveness.md`). Shapes:

- **Single-file records:** `NNN_<slug>_record.md` (execution reports).
- **Multi-file records:** `NNN_<slug>_record/` — inner files keep their names
  (`STATUS.md`, `REPORT.md`, a design document, sidecars), plus an optional untracked
  `artifacts/` (gitignored; every artifact is cited in its record *with its
  regeneration command*, never as a bare path).
- **Slice-level records:** `000_overview_record.md` (the S01–S14 implementation plan:
  agent contract, dependency DAG, lanes) and `036_implementation_report_record.md`
  (the slice process record; its §5/§6 are superseded going forward by
  `development/REGISTRY.md`).
- **Thematic subdirectories** for external-facing drafts, created only by their
  owning work unit.

## Work-unit records of the S01–S14 slice

| Record | Work unit |
|---|---|
| `001_repo_scaffold_record/STATUS.md` | repo scaffold |
| `002_core_state_contracts_record/STATUS.md` | core state + contracts |
| `003_component_abi_t0_record/STATUS.md` | component ABI + wrappers + T0 |
| `004_coupling_algebra_record/STATUS.md` | coupling algebra + DynamicalCore |
| `005_vault_plan_t1_record/STATUS.md` | vault + plan compiler + T1 |
| `006_vertical_grid_thermo_record/STATUS.md` | vertical grid + thermo |
| `007_satad_component_record/STATUS.md` | satad component |
| `008_graupel_component_record/STATUS.md` | graupel component |
| `009_scm_composition_record/STATUS.md` | SCM composition |
| `010_ftier_column_gradients_record/STATUS.md` | F-tier column + gradients |
| `011_icon_grid_metrics_record/STATUS.md` | ICON grid + metrics |
| `012_nonhydro_hosting_record/STATUS.md` | NonhydroSolver hosting |
| `013_diffusion_jw_l4_record/STATUS.md` | diffusion + JW baroclinic L4 |
| `014_plan_through_dycore_record/STATUS.md` | plan through the dycore |

## Post-slice records

| Entry | Work unit | Kind |
|---|---|---|
| `026_gridgen_integration_record.md` | 026 (plan ad hoc, not committed) | execution report |
| `027_docs_plan_record/27_docs_plan.md` | 027 (plan ad hoc, not committed) | design document — docs-stack evaluation and plan; TD-27.1–3 in `development/REGISTRY.md` |
| `028_docs_implementation_record.md` | 028 (`../plans/028_docs_implementation_plan.md`) | execution report |
| `029_plan_structure_record/29_plan_structure.md` | 029 (plan ad hoc, not committed) | design document — plan/memory structure analysis + proposal; TD-29.x in `development/REGISTRY.md`; §8 is the liftable 031 spec |
| `031_plan_structure_migration_record.md` | 031 (plan: 029 record §8) | execution report |
| `032_docs_development_structure_record/32_docs_development_structure.md` | 032 (plan ad hoc, not committed) | design document — development-tree evaluation; decisions implemented by work unit 033 |
| `033_structure_migration_record/REPORT.md` | 033 (`../plans/033_structure_migration_plan.md`) | execution report (+ sidecar `layout_doc_revision.diff`, TD-33.4) |
| `034_naming_iteration_record/34_naming_iteration.md` | 034 (plan ad hoc, not committed) | design document — naming-convention evaluation; implemented by work unit 035 |
| `035_naming_migration_record/REPORT.md` | 035 (`../plans/035_naming_migration_plan.md`) | execution report |
| `upstream/` | 023 (unexecuted) | external-facing drafts (icon4py issue texts) — created by work unit 023, do not pre-create |
| `prs/` | 024 (unexecuted) | external-facing drafts (per-work-unit PR bodies, publish script) — created by work unit 024, do not pre-create |
