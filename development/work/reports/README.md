# reports/ — outcome documents, frozen at merge

Every outcome document of a merged work unit lives here (liveness rules and templates:
`development/policies/document_kinds.md`). Shapes:

- **Single-file reports:** `report-NNNN-<kebab>.md` (execution reports).
- **Multi-file reports:** `report-NNNN-<kebab>/` — inner files keep their names
  (`STATUS.md`, `REPORT.md`, a design document, sidecars), plus an optional untracked
  `artifacts/` (gitignored; every artifact is cited in its report *with its
  regeneration command*, never as a bare path).
- **Slice-level reports:** `report-0000-overview.md` (the S01–S14 implementation plan:
  agent contract, dependency DAG, lanes) and `report-0036-implementation-report.md`
  (the slice process report; its §5/§6 are superseded going forward by
  `development/REGISTRY.md`).
- **Thematic subdirectories** for external-facing drafts, created only by their
  owning work unit.

## Work-unit reports of the S01–S14 slice

| Report | Work unit |
|---|---|
| `report-0001-repo-scaffold/STATUS.md` | repo scaffold |
| `report-0002-core-state-contracts/STATUS.md` | core state + contracts |
| `report-0003-component-abi-t0/STATUS.md` | component ABI + wrappers + T0 |
| `report-0004-coupling-algebra/STATUS.md` | coupling algebra + DynamicalCore |
| `report-0005-vault-plan-t1/STATUS.md` | vault + plan compiler + T1 |
| `report-0006-vertical-grid-thermo/STATUS.md` | vertical grid + thermo |
| `report-0007-satad-component/STATUS.md` | satad component |
| `report-0008-graupel-component/STATUS.md` | graupel component |
| `report-0009-scm-composition/STATUS.md` | SCM composition |
| `report-0010-ftier-column-gradients/STATUS.md` | F-tier column + gradients |
| `report-0011-icon-grid-metrics/STATUS.md` | ICON grid + metrics |
| `report-0012-nonhydro-hosting/STATUS.md` | NonhydroSolver hosting |
| `report-0013-diffusion-jw-l4/STATUS.md` | diffusion + JW baroclinic L4 |
| `report-0014-plan-through-dycore/STATUS.md` | plan through the dycore |

## Post-slice reports

| Entry | Work unit | Kind |
|---|---|---|
| `report-0026-gridgen-integration.md` | 0026 (plan ad hoc, not committed) | execution report |
| `report-0027-docs-plan/27_docs_plan.md` | 0027 (plan ad hoc, not committed) | design document — docs-stack evaluation and plan; TD-27.1–3 in `development/REGISTRY.md` |
| `report-0028-docs-implementation.md` | 0028 (`../plans/plan-0028-docs-implementation.md`) | execution report |
| `report-0029-plan-structure/29_plan_structure.md` | 0029 (plan ad hoc, not committed) | design document — plan/memory structure analysis + proposal; TD-29.x in `development/REGISTRY.md`; §8 is the liftable 031 spec |
| `report-0031-plan-structure-migration.md` | 0031 (plan: 0029 report §8) | execution report |
| `report-0032-docs-development-structure/32_docs_development_structure.md` | 0032 (plan ad hoc, not committed) | design document — development-tree evaluation; decisions implemented by work unit 033 |
| `report-0033-structure-migration/REPORT.md` | 0033 (`../plans/plan-0033-structure-migration.md`) | execution report (+ sidecar `layout_doc_revision.diff`, TD-33.4) |
| `report-0034-naming-iteration/34_naming_iteration.md` | 0034 (plan ad hoc, not committed) | design document — naming-convention evaluation; implemented by work unit 035 |
| `report-0035-naming-migration/REPORT.md` | 0035 (`../plans/plan-0035-naming-migration.md`) | execution report |
| `report-0049-work-structure-iteration.md` | 0049 (plan ad hoc, not committed) | design document — `work/` tree evaluation; implemented by work unit 0050 |
| `report-0050-work-tree-migration.md` | 0050 (`../plans/plan-0050-work-tree-migration.md`) | execution report |
| `upstream/` | 0023 (unexecuted) | external-facing drafts (icon4py issue texts) — created by work unit 0023, do not pre-create |
| `prs/` | 0024 (unexecuted) | external-facing drafts (per-work-unit PR bodies, publish script) — created by work unit 0024, do not pre-create |
