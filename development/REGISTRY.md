# REGISTRY — document numbers and trunk decisions

One file, two registers: the document-number register (§1, with the permanent old→new
remap table in §2) and the trunk-decision/sign-off register (§3). Rules for the
decision register: append-mostly (rows are added, and their `Status` field updated in
place; nothing else is edited); every new `TD-PENDING:` line in any report gets a row
here **in the same PR**; decision text that quotes a tolerance or signature is copied
verbatim from its source. This register supersedes
`development/work/reports/report-0036-implementation-report.md` §5 (sign-off ledger) and §6
(standing follow-ups) going forward — that report stays frozen as the historical record.
Conventions: ID `TD-<origin>.<k>` where origin is the work unit (`S08`, `27`, `35`) that
raised it. Status: `pending` / `signed-off` / `rejected` / `superseded(TD-…)`. `Date` is the date the
decision entered main (the merge of its source).
Formerly DECISIONS.md (renamed in work unit 035, TD-35.3); before that
plan/TRUNK_DECISIONS.md.

Seeded 2026-07-13 by work unit 031 (spec: `development/work/reports/report-0029-plan-structure.md` §8).

## 1. Document register (the single allocator)

A number is allocated by adding a row here **at assignment**, even when the plan text
is delivered ad hoc and never committed (the row says so). Numbers are strictly
monotonic, never reused; gaps are never backfilled — 0015–0019 stay open forever. On a
collision, the first-registered number wins and the latecomer takes the next free one.
One number per work unit — four digits since work unit 0050, numeric values preserved
from the three-digit scheme (TD-50.1, ADR-0006) — shared by its
proposal/spec/plan/report files (`<kind>-<NNNN>-<kebab-slug>`); single-kind documents
consume one number. ADRs are no longer registered here: they number independently in
`development/ADRs/` (index: `ADRs/README.md`); the former ADR rows 043–048 remapped to
ADRs 0000–0005 (§2b) and their work ids stay consumed, never reused.
**Next free number: 0054.**

| NNNN | slug | kinds | status |
|---|---|---|---|
| 0000 | overview | report | executed (S01–S14 slice overview, frozen) |
| 0001 | repo-scaffold | spec + plan + report | executed |
| 0002 | core-state-contracts | spec + plan + report | executed |
| 0003 | component-abi-t0 | spec + plan + report | executed |
| 0004 | coupling-algebra | spec + plan + report | executed |
| 0005 | vault-plan-t1 | spec + plan + report | executed |
| 0006 | vertical-grid-thermo | spec + plan + report | executed |
| 0007 | satad-component | spec + plan + report | executed |
| 0008 | graupel-component | spec + plan + report | executed |
| 0009 | scm-composition | spec + plan + report | executed |
| 0010 | ftier-column-gradients | spec + plan + report | executed |
| 0011 | icon-grid-metrics | spec + plan + report | executed |
| 0012 | nonhydro-hosting | spec + plan + report | executed |
| 0013 | diffusion-jw-l4 | spec + plan + report | executed |
| 0014 | plan-through-dycore | spec + plan + report | executed |
| 0020 | gpu-validation | plan | pending |
| 0021 | ci-hardening | plan | pending |
| 0022 | plan-hash-config-digest | plan | pending |
| 0023 | upstream-reports | plan | pending |
| 0024 | pr-publication | plan | pending |
| 0025 | cf-multistage-t1 | plan | pending |
| 0026 | gridgen-integration | report | executed (plan ad hoc, not committed) |
| 0027 | docs-plan | report | executed (plan ad hoc, not committed) |
| 0028 | docs-implementation | plan + report | executed |
| 0029 | plan-structure | report | executed (plan ad hoc, not committed) |
| 0030 | author-phase-specs | plan | pending |
| 0031 | plan-structure-migration | report | executed (plan: 0029 report §8) |
| 0032 | docs-development-structure | report | executed (plan ad hoc, not committed) |
| 0033 | structure-migration | plan + report | executed |
| 0034 | naming-iteration | report | executed (plan ad hoc, not committed) |
| 0035 | naming-migration | plan + report | executed |
| 0036 | implementation-report | report | executed (S01–S14 slice process report, frozen) |
| 0037 | p2-distributed | proposal | accepted-roadmap |
| 0038 | p3-full-physics | proposal | accepted-roadmap |
| 0039 | p4-ingestion-realdata | proposal | accepted-roadmap |
| 0040 | p5-tiers-t2-t3 | proposal | accepted-roadmap |
| 0041 | p6-differentiable-distributed-da | proposal | accepted-roadmap |
| 0042 | p7-presets-docs-anemoi | proposal | accepted-roadmap |
| 0049 | work-structure-iteration | report | executed (plan ad hoc, not committed) |
| 0050 | work-tree-migration | plan + report | executed |
| 0051 | kebab-and-flat-reports | plan + report | executed |
| 0052 | disjoint-verification-gates | proposal + spec + plan + report | executed |
| 0053 | project-rename-icon-sc | spec + plan + report | executed |

**Slug rename (work 0052, TD-52.3):** 0052's slug was `parallel-verification-gates`
until 2026-07-17 — the name under which its proposal, spec and plan were merged to main, and
the form any pre-2026-07-17 history or branch name will use. It is now
`disjoint-verification-gates`: measurement removed every parallel mechanism from the work
unit, leaving the disjointness fix as what it delivers, so the old name described machinery
that no longer exists. The number is unchanged (never reused, never renumbered); only the
slug moved.

Numbers 0000–0014 are the remapped S-series work units. The old N-series number 10
(the review protocol) is superseded by this remap: the protocol is a policy
(`policies/review-protocol.md`), unnumbered and exempt from the scheme. Numbers
0015–0019 were never allocated and stay open per the never-backfill rule. Work ids
0043–0048 were consumed by the former ADR rows (now `ADRs/0000`–`0005`, see §2b) and
are never reused.

## 2. Remap table (permanent — the bridge for historical names and `development/references/lock.toml` ids)

Old→new for every file renamed by work unit 035 (commit C1). Historical wording in
frozen records ("step S08", "task 26", `ADR-0002`, old paths) translates via this
table; `development/references/lock.toml` step ids ("S08") stay as written and resolve here.
**Note (work 0050):** the "New" column shows the 035 names; those files were renamed
again by work unit 0050 — every "New" entry resolves further via §2b below (the second
hop of the historical bridge, e.g. `S08` → `008_graupel_component_spec.md` →
`spec-0008-graupel-component.md`).

| Old | New |
|---|---|
| `specs/S01_repo_scaffold.md` | `specs/001_repo_scaffold_spec.md` |
| `specs/S02_core_state_contracts.md` | `specs/002_core_state_contracts_spec.md` |
| `specs/S03_component_abi_t0.md` | `specs/003_component_abi_t0_spec.md` |
| `specs/S04_coupling_algebra.md` | `specs/004_coupling_algebra_spec.md` |
| `specs/S05_vault_plan_t1.md` | `specs/005_vault_plan_t1_spec.md` |
| `specs/S06_vertical_grid_thermo.md` | `specs/006_vertical_grid_thermo_spec.md` |
| `specs/S07_satad_component.md` | `specs/007_satad_component_spec.md` |
| `specs/S08_graupel_component.md` | `specs/008_graupel_component_spec.md` |
| `specs/S09_scm_composition.md` | `specs/009_scm_composition_spec.md` |
| `specs/S10_ftier_column_gradients.md` | `specs/010_ftier_column_gradients_spec.md` |
| `specs/S11_icon_grid_metrics.md` | `specs/011_icon_grid_metrics_spec.md` |
| `specs/S12_nonhydro_hosting.md` | `specs/012_nonhydro_hosting_spec.md` |
| `specs/S13_diffusion_jw_l4.md` | `specs/013_diffusion_jw_l4_spec.md` |
| `specs/S14_plan_through_dycore.md` | `specs/014_plan_through_dycore_spec.md` |
| `plans/S01…S14_<slug>.md` (14) | `plans/001…014_<slug>_plan.md` (same slugs as the specs) |
| `plans/20_gpu_validation.md` | `plans/020_gpu_validation_plan.md` |
| `plans/21_ci_hardening.md` | `plans/021_ci_hardening_plan.md` |
| `plans/22_plan_hash_config_digest.md` | `plans/022_plan_hash_config_digest_plan.md` |
| `plans/23_upstream_reports.md` | `plans/023_upstream_reports_plan.md` |
| `plans/24_pr_publication.md` | `plans/024_pr_publication_plan.md` |
| `plans/25_cf_multistage_t1.md` | `plans/025_cf_multistage_t1_plan.md` |
| `plans/28_docs_implementation.md` | `plans/028_docs_implementation_plan.md` |
| `plans/30_author_phase_specs.md` | `plans/030_author_phase_specs_plan.md` |
| `plans/33_structure_migration.md` | `plans/033_structure_migration_plan.md` |
| `records/00_OVERVIEW.md` | `records/000_overview_record.md` |
| `records/S01…S14_<slug>/` (14 folders) | `records/001…014_<slug>_record/` (inner files unchanged) |
| `records/26_gridgen_integration_REPORT.md` | `records/026_gridgen_integration_record.md` |
| `records/27_docs_plan/` | `records/027_docs_plan_record/` |
| `records/28_docs_implementation_REPORT.md` | `records/028_docs_implementation_record.md` |
| `records/29_plan_structure/` | `records/029_plan_structure_record/` |
| `records/31_plan_structure_migration_REPORT.md` | `records/031_plan_structure_migration_record.md` |
| `records/32_docs_development_structure/` | `records/032_docs_development_structure_record/` |
| `records/33_structure_migration/` | `records/033_structure_migration_record/` |
| `records/34_naming_iteration/` | `records/034_naming_iteration_record/` |
| `records/IMPLEMENTATION_REPORT.md` | `records/036_implementation_report_record.md` |
| `ideas/P2_distributed.md` | `ideas/037_p2_distributed_idea.md` |
| `ideas/P3_full_physics.md` | `ideas/038_p3_full_physics_idea.md` |
| `ideas/P4_ingestion_realdata.md` | `ideas/039_p4_ingestion_realdata_idea.md` |
| `ideas/P5_tiers_t2_t3.md` | `ideas/040_p5_tiers_t2_t3_idea.md` |
| `ideas/P6_differentiable_distributed_da.md` | `ideas/041_p6_differentiable_distributed_da_idea.md` |
| `ideas/P7_presets_docs_anemoi.md` | `ideas/042_p7_presets_docs_anemoi_idea.md` |
| `adr/0001-development-tree-reorganization.md` (cited `ADR-0001`) | `adr/043_development_tree_reorganization_adr.md` (cite `adr 043`) |
| `adr/0002-content-frozen-records.md` (cited `ADR-0002`) | `adr/044_content_frozen_records_adr.md` (cite `adr 044`) |
| `adr/0003-decision-register-and-adrs.md` (cited `ADR-0003`) | `adr/045_decision_register_and_adrs_adr.md` (cite `adr 045`) |
| `development/DECISIONS.md` | `development/REGISTRY.md` |
| `docs/architecture/symcon_repo_layout.md` | `development/policies/repo_layout.md` |

## 2b. Remap table (work 0050 — the second hop: 035 names → the `work/` tree)

Old→new for every file renamed by work unit 0050 (commit C1, 84 renames; TD-50.1,
ADR-0006). Paths are relative to `development/` unless prefixed. Slug rule: the 035
name's snake slug converted to kebab (`_`→`-`); inner files of folder-shaped reports
are unchanged.

| Old (035 scheme) | New (work 0050) |
|---|---|
| `specs/NNN_<slug>_spec.md` (001…014) | `work/specs/spec-0NNN-<kebab-slug>.md` |
| `specs/README.md` | `work/specs/README.md` |
| `plans/NNN_<slug>_plan.md` (001…014, 020…025, 028, 030, 033, 035) | `work/plans/plan-0NNN-<kebab-slug>.md` |
| `plans/README.md` | `work/plans/README.md` |
| `records/000_overview_record.md` | `work/reports/report-0000-overview.md` |
| `records/NNN_<slug>_record/` (001…014, the STATUS folders) | `work/reports/report-0NNN-<kebab-slug>/` |
| `records/026_gridgen_integration_record.md` | `work/reports/report-0026-gridgen-integration.md` |
| `records/027_docs_plan_record/` | `work/reports/report-0027-docs-plan/` |
| `records/028_docs_implementation_record.md` | `work/reports/report-0028-docs-implementation.md` |
| `records/029_plan_structure_record/` | `work/reports/report-0029-plan-structure/` |
| `records/031_plan_structure_migration_record.md` | `work/reports/report-0031-plan-structure-migration.md` |
| `records/032_docs_development_structure_record/` | `work/reports/report-0032-docs-development-structure/` |
| `records/033_structure_migration_record/` (incl. `layout_doc_revision.diff`) | `work/reports/report-0033-structure-migration/` |
| `records/034_naming_iteration_record/` | `work/reports/report-0034-naming-iteration/` |
| `records/035_naming_migration_record/` | `work/reports/report-0035-naming-migration/` |
| `records/036_implementation_report_record.md` | `work/reports/report-0036-implementation-report.md` |
| `records/049_work_structure_iteration_record.md` | `work/reports/report-0049-work-structure-iteration.md` |
| `records/README.md` | `work/reports/README.md` |
| `ideas/NNN_<slug>_idea.md` (037…042) | `work/proposals/proposal-0NNN-<kebab-slug>.md` |
| `ideas/README.md` | `work/proposals/README.md` |
| `adr/043_development_tree_reorganization_adr.md` (cited `adr 043`) | `ADRs/0000-development-tree-reorganization.md` (cite `ADR-0000`) |
| `adr/044_content_frozen_records_adr.md` (cited `adr 044`) | `ADRs/0001-content-frozen-records.md` (cite `ADR-0001`) |
| `adr/045_decision_register_and_adrs_adr.md` (cited `adr 045`) | `ADRs/0002-decision-register-and-adrs.md` (cite `ADR-0002`) |
| `adr/046_document_naming_scheme_adr.md` (cited `adr 046`) | `ADRs/0003-document-naming-scheme.md` (cite `ADR-0003`) |
| `adr/047_docs_stack_adr.md` (cited `adr 047`) | `ADRs/0004-docs-stack.md` (cite `ADR-0004`) |
| `adr/048_gridgen_adoption_adr.md` (cited `adr 048`) | `ADRs/0005-gridgen-adoption.md` (cite `ADR-0005`) |
| `adr/README.md` | `ADRs/README.md` |
| `REFERENCES.lock` (repo root) | `development/references/lock.toml` |
| `policies/records_and_liveness.md` | `policies/document_kinds.md` |

## 2c. Remap table (work 0051 — kebab-case everywhere + flat reports)

Old→new for every file renamed by work unit 0051 (commit C1; TD-51.1/51.2, ADR-0007).
Paths are relative to `development/` unless prefixed. The 0004 report folder survives
on disk as the (untracked) artifacts folder beside the flat report file; the 0033
folder survives in git as the artifacts folder holding the tracked sidecar.

| Old (0050 scheme) | New (work 0051) |
|---|---|
| `policies/agent_workflow.md` | `policies/agent-workflow.md` |
| `policies/docs_boundary.md` | `policies/docs-boundary.md` |
| `policies/document_kinds.md` | `policies/document-kinds.md` |
| `policies/naming_conventions.md` | `policies/naming-conventions.md` |
| `policies/reference_mining.md` | `policies/reference-mining.md` |
| `policies/repo_layout.md` | `policies/repo-layout.md` |
| `policies/review_protocol.md` | `policies/review-protocol.md` |
| `policies/verification_gates.md` | `policies/verification-gates.md` |
| `references/icon_fortran.md` | `references/icon-fortran.md` |
| `references/icon_grid_generator.md` | `references/icon-grid-generator.md` |
| `references/icon_tutorial_2025.md` | `references/icon-tutorial-2025.md` |
| `references/ubbiali_thesis.md` | `references/ubbiali-thesis.md` |
| `archive/plan_tree_map.md` | `archive/plan-tree-map.md` |
| `work/reports/report-<NNNN>-<kebab>/STATUS.md` (0001…0014) | `work/reports/report-<NNNN>-<kebab>.md` |
| `work/reports/report-0027-docs-plan/27_docs_plan.md` | `work/reports/report-0027-docs-plan.md` |
| `work/reports/report-0029-plan-structure/29_plan_structure.md` | `work/reports/report-0029-plan-structure.md` |
| `work/reports/report-0032-docs-development-structure/32_docs_development_structure.md` | `work/reports/report-0032-docs-development-structure.md` |
| `work/reports/report-0033-structure-migration/REPORT.md` | `work/reports/report-0033-structure-migration.md` |
| `work/reports/report-0034-naming-iteration/34_naming_iteration.md` | `work/reports/report-0034-naming-iteration.md` |
| `work/reports/report-0035-naming-migration/REPORT.md` | `work/reports/report-0035-naming-migration.md` |
| `work/reports/report-0033-structure-migration/layout_doc_revision.diff` | `work/reports/report-0033-structure-migration/layout-doc-revision.diff` |
| `work/reports/report-0004-coupling-algebra/artifacts/*.png` (untracked) | `work/reports/report-0004-coupling-algebra/*.png` (untracked, plain `mv`) |

## 3. Decision register

### Sign-off items from the 001–014 slice (mirrors IMPLEMENTATION_REPORT §5, verbatim)

| ID | Date | Decision (verbatim from source) | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-S05.1 | 2026-07-09 | Zero-traffic acceptance operationalization (settrace can't see C-level `dict.__getitem__`; tracemalloc protocol) | pending | `development/work/reports/report-0005-vault-plan-t1.md` deviations 4–5 banner; IMPLEMENTATION_REPORT §5 | — |
| TD-S08.1 | 2026-07-10 | `CONSERVATION_RTOL_COLD = 1e-3` (characterized cold-glaciation leak; upstream report follow-up) | pending | `development/work/reports/report-0008-graupel-component.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S09.1 | 2026-07-11 | Tracer negativity `≥ −QMIN`; whole-run `CONSERVATION_RTOL = 1e-11` | pending | `development/work/reports/report-0009-scm-composition.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S10.1 | 2026-07-11 | QMIN atol floor on acceptances 1/7 | pending | `development/work/reports/report-0010-ftier-column-gradients.md` tolerance note; IMPLEMENTATION_REPORT §5 | — |
| TD-S12.1 | 2026-07-11 | vn `atol = 1e-11` on EXCLAIM_APE multi-substep parity (reviewer recommends granting) | pending | `development/work/reports/report-0012-nonhydro-hosting.md` deviation 8; IMPLEMENTATION_REPORT §5 | — |
| TD-S13.1 | 2026-07-12 | `jablonowski_williamson` mandatory `static` kwarg (frozen-signature change); pooch→sha256-manifest swap | pending | `development/work/reports/report-0013-diffusion-jw-l4.md` deviations 6, 11; IMPLEMENTATION_REPORT §5 | — |
| TD-S14.1 | 2026-07-13 | "Bitwise per backend" evidence-backed for gtfn_cpu only (gpu leg never executed) | pending | `development/work/reports/report-0014-plan-through-dycore.md` review-fixes note; IMPLEMENTATION_REPORT §5 | — |

### Decisions from work unit 027 (docs stack) — executed by work unit 028

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-27.1 | 2026-07-13 | Docs stack: Sphinx + MyST-Parser + Napoleon + furo; layout-doc line "`docs/api/` # sphinx + autodoc from py.typed sources" is complied with via MyST (no layout-doc edit required to proceed); MkDocs alternative rejected | signed-off | `development/work/reports/report-0027-docs-plan.md` §3.2 (TD-1) | task-28 merge `cbbec36` |
| TD-27.2 | 2026-07-13 | Docs dependency additions: dev-group lower bounds `sphinx>=8.1`, `myst-parser>=4.0`, `furo>=2025.12.19`; `constraints/cpu-ci.txt` pins sphinx==8.1.3, myst-parser==4.0.1, furo==2025.12.19, docutils==0.21.2 | signed-off | `report-0027-docs-plan.md` §3.3 (TD-2) | task-28 merge `cbbec36` |
| TD-27.3 | 2026-07-13 | Docstring convention: Google-style sections going forward, Napoleon-parsed; existing corpus kept, convert-on-touch; ruff `D` with shrink-only ignore baseline | signed-off | `report-0027-docs-plan.md` §3.4/§4 (TD-3) | task-28 merge `cbbec36` |

### Decisions from work unit 029 (plan-structure proposal)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-29.1 | 2026-07-13 | Zero-move plan structure ratified: `plan/prompts/reports/` stays the single deliverables tree with kind-labelled index; task-27 subdir pattern blessed for document-deliverables (task 29's own location conforms) | superseded(TD-33.1) | `report-0029-plan-structure.md` §4, §7 | task-31 merge `58a51f7` |
| TD-29.2 | 2026-07-13 | Create `development/REGISTRY.md` (this file) + `TD-PENDING:` marker | signed-off | `report-0029-plan-structure.md` §5.1, §7 | task-31 merge `58a51f7` |
| TD-29.3 | 2026-07-13 | N-series allocation rule + forward SPEC/STATUS templates adopted (recorded in `development/archive/plan-tree-map.md`; register + allocation rule in prompts-README) | signed-off | `report-0029-plan-structure.md` §3.2–3.3, §7, §8 items A/C | task-31 merge `58a51f7` |
| TD-29.4 | 2026-07-13 | Extend unexecuted task 24's scope with a thin `CONTRIBUTING.md` at publication time | pending | `report-0029-plan-structure.md` §5, §7 | — |
| TD-29.5 | 2026-07-13 | Generalize `.github/PULL_REQUEST_TEMPLATE.md` line 3 to cover tasks as well as steps | pending | `report-0029-plan-structure.md` §7 | — |
| TD-29.6 | 2026-07-13 | Home for future external-facing drafts beyond tasks 23/24 (`plan/drafts/` vs `reports/<theme>/`) | superseded(TD-33.1) | `report-0029-plan-structure.md` §7 | — |
| TD-29.7 | 2026-07-13 | Apply the layout-doc §4 revision (drafted diff: docs/ tree incl. conf.py/tutorials/glossary/names_registry carve-out/api reword, docs.yml workflow line, v1.2→v1.3 errata, self-listing); absorbs 27 §3.2's additive clarification | superseded(TD-33.4) | `report-0029-plan-structure.md` §6.3 | — |
| TD-29.8 | 2026-07-13 | Root README refresh (drop the stale pre-implementation status; current Contents) | signed-off | `report-0029-plan-structure.md` §7 | task-31 merge `58a51f7` |
| TD-29.9 | 2026-07-13 | No CHANGELOG until the P7 versioning/release step; format (Keep-a-Changelog vs towncrier) decided together with the release tooling then. (ID beyond the proposal's numbered 29.1–29.8: the CHANGELOG verdict in §5 was required but unnumbered.) | signed-off (deferral) | `report-0029-plan-structure.md` §5 | task-31 merge `58a51f7` |
| TD-29.10 | 2026-07-13 | Trunk-owned wording amendments: AGENTS.md Workflow item 6 (extend the STATUS/PR sentence to cover tasks) and the prompts-README invariants paragraph (point sign-off flags at this register) — per proposal §5.1/§7 | pending — trunk-only edits | `report-0029-plan-structure.md` §5.1, §7 | — |

### Decisions from work unit 033 (structure migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-33.1 | 2026-07-14 | `development/` tree reorganization adopted per task-32 evaluation as amended by owner iteration; full migration; `plan/` deleted. **Supersedes TD-29.1** (zero-move) **and TD-29.6** (external-drafts home: resolved as "no dedicated folder") | signed-off | ADR-0000 + `development/work/plans/plan-0033-structure-migration.md` §1 | task-33 merge `10ecafb` |
| TD-33.2 | 2026-07-14 | Content-frozen amendment: "frozen" = content-frozen; mechanical path retargeting confined to link/path strings permitted in sanctioned migration commits, isolated for word-diff verification | signed-off | ADR-0001 | task-33 merge `10ecafb` |
| TD-33.3 | 2026-07-14 | Register renamed/moved to `development/DECISIONS.md`; ledger/ADR no-merge relationship (register = sign-off rows, `adr/` = reasoning; architecture-shaped decisions get both) | signed-off | ADR-0002 | task-33 merge `10ecafb` |
| TD-33.4 | 2026-07-14 | Proposed revision of `docs/architecture/symcon_repo_layout.md` repo tree (diff artifact `development/work/reports/report-0033-structure-migration/layout-doc-revision.diff`); owner applies or rejects. Marks the re-draft of TD-29.7 | signed-off | `development/work/plans/plan-0033-structure-migration.md` §5.13 | owner-applied, trunk commit `f053659` |

### Decisions from work unit 035 (naming migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-35.1 | 2026-07-14 | `NNN_<slug>_<kind>` naming scheme: one global three-digit sequence, one number per work unit shared across its idea/spec/plan/record files, kind suffix = singular folder name; exempt: `policies/*`, all `README.md`, `REGISTRY.md`, `archive/*` contents; history remapped, never renumbered (§2); ADR citation form `adr NNN`; forward branch convention `work/NNN-<slug>` | signed-off | `ADR-0003`; 034 evaluation §3/§9 (`development/work/reports/report-0034-naming-iteration.md`) | work-035 merge `d3257df` |
| TD-35.2 | 2026-07-14 | Repo-layout doc moved to `development/policies/repo_layout.md` (living policy, trunk-gated) and removed from the published site; the canonical trunk-frozen set is `docs/architecture/symcon_architecture.md` alone | signed-off | 034 evaluation §2 | work-035 merge `d3257df` |
| TD-35.3 | 2026-07-14 | `DECISIONS.md` renamed `REGISTRY.md`, absorbing the document-number allocator from `plans/README.md`: one file, two registers (documents + trunk decisions) | signed-off | 034 evaluation §1 | work-035 merge `d3257df` |
| TD-35.4 | 2026-07-14 | F1: `.claude/settings.json` deny glob narrowed `Edit(development/specs/**)` → `Edit(development/specs/*_spec.md)` — spec files stay protected, the living `specs/README.md` becomes editable | signed-off | 035 record §6 F1 | trunk commit `1980f0d` |
| TD-35.5 | 2026-07-14 | F2: output paths in the unexecuted plans 020–025/030 and the idea `Status:` headers restated in the `NNN_<slug>_<kind>` scheme — a sanctioned edit of frozen-at-assignment plans (unconsumed contracts; owner-instructed), same class as the 032 evaluation decision point 10 | signed-off | 035 record §6 F2 | trunk commit `1980f0d` |

### Decisions from work unit 0050 (work-tree migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-50.1 | 2026-07-15 | `development/work/` tree with kind-prefixed names: lifecycle folders `work/{proposals,specs,plans,reports}` (ex-`ideas`, ex-`records`); files `<kind>-<NNNN>-<kebab-slug>`, four digits, **numeric values preserved** from the three-digit ids (never compact-renumbered — the remap is §2b); lifecycle vocabulary proposal → spec → plan → report | signed-off | ADR-0006 | work-0050 merge `fcdb527` |
| TD-50.2 | 2026-07-15 | `ADRs/` independence: own Nygard sequence from 0000 (043–048 → 0000–0005 in order), the deliberate uppercase exception (the repo's only non-lowercase folder), citation form `ADR-NNNN`; supersedes ADR-0003's sequence/suffix clauses | signed-off | ADR-0006 | work-0050 merge `fcdb527` |
| TD-50.3 | 2026-07-15 | `REFERENCES.lock` → `development/references/lock.toml`; the header-title edit sanctioned (append-only binds the `[[ref]]` entries, not the schema comment); entries and their historical `step` ids untouched | signed-off | ADR-0006; 049 evaluation §3 | work-0050 merge `fcdb527` |

### Decisions from work unit 0051 (kebab-case everywhere + flat reports)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-51.1 | 2026-07-15 | Kebab-case for ALL filenames under `development/` — including `policies/`, `references/` cards, and `archive/` contents — never snake or mixed; exceptions: `README.md` (conventional) and `lock.toml` (fixed name); supersedes ADR-0006's kebab/snake-split clause | signed-off | ADR-0007 | work-0051 merge `3af101c` |
| TD-51.2 | 2026-07-15 | Reports are flat files `report-<NNNN>-<kebab>.md`; artifacts (only when they exist) in a sibling folder `report-<NNNN>-<kebab>/` named like the report file minus `.md`; per-folder gitignore convention: a report folder holding ONLY untracked artifacts gets its own explicit `.gitignore` line, folders holding tracked sidecars are not ignored; supersedes ADR-0006's folder-report shape | signed-off | ADR-0007 | work-0051 merge `3af101c` |

### Decisions from work unit 0052 (parallel verification gates)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-52.1 | 2026-07-17 | **`pytest-xdist` NOT adopted — withdrawn on measurement** (owner-instructed 2026-07-17). Proposed as a `dev` lower bound; measured and rejected: it does not help this corpus. Run-to-run variance is ±15 % (worse on the `data` partitions, which are page-cache bound — `EXCLAIM_APE` is 8.7 GB extracted against ~10 GB of cache), and every apparent gain sat inside that noise. `fast`: 2:28 serial vs 2:43 at `-n 10` (means of 4/3 samples — serial *ahead*). `data-noslow`'s 19 % gain, the last justification for the dependency, did not reproduce (6:38 → >10:00, same config, idle host). `pyproject.toml`/`uv.lock` end **byte-identical to main**; nothing to pin, nothing to sign off. Recorded so a future work unit does not re-litigate it blind: **the gate's win is disjoint partitions (Item A), not intra-partition parallelism** | rejected | `report-0052-disjoint-verification-gates.md` §3 D5, §5; spec-0052 Amendment 4 | work-0052 merge `fd3f874` |
| TD-52.3 | 2026-07-17 | **Work unit 0052 renamed `parallel-verification-gates` → `disjoint-verification-gates`** (owner-instructed 2026-07-17). Its proposal/spec/plan were merged to main under the old slug; all four files are renamed and their path strings retargeted in one isolated commit (ADR-0001's content-frozen rule; same class as TD-35.5, an owner-instructed edit of frozen-at-assignment documents). Titles are restated too — the rename's whole point. Rationale: measurement withdrew pytest-xdist and every concurrent schedule (TD-52.1, TD-52.2/Amendments 4–5), leaving Item A (disjoint partitions) as the delivered win, so "parallel" named machinery the work unit no longer contains. Number unchanged; §1 carries the old→new bridge. Branch renamed `work/0052-disjoint-verification-gates` to match | signed-off | `report-0052-disjoint-verification-gates.md` §3 D7 | work-0052 merge `fd3f874` |
| TD-52.2 | 2026-07-17 | **Sanctioned amendment of the frozen `spec-0052`, Amendments 1–5** (owner-instructed 2026-07-16 and 2026-07-17; same class as TD-35.5). Measurement falsified the spec's premise in stages. Amendments 1–2 (2026-07-16): (a) the ≈ 18–22 min target is unreachable — one test, `test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, is 1519 s (25.3 min), 75 % of the `data+slow` partition, and no worker count splits a single test; the target is withdrawn in favour of "materially reduced against the measured serial baseline, figure reported", with retrofitting a target to the achieved figure expressly forbidden. (b) the `data+slow` rationale ("55 static-fields tests each re-running the gt4py factories") is false — `_get_static` is memoized per process, those 55 tests cost ~12 s combined; `data+slow` therefore runs **serially**, measured fastest *and* lowest-RAM (serial 33:04/5.0 GiB vs `-n 2` 33:08/6.4 GiB vs `-n 4` 35:13/9.0 GiB). Amendments 3–5 (2026-07-17): the `-n` calibration did not reproduce on an idle host (±15 % noise floor, page-cache bound), so **pytest-xdist was withdrawn entirely** (TD-52.1 `rejected`); lane concurrency was then built, measured (51.1 min vs 51.9 sequential — nothing, every partition 1.5–3.2× slower, wall-time conserved) and **also withdrawn**, so the gate ships **sequential**. The battery does not parallelize: a single process uses ~1.1 of 16 cores with the host 90 % idle and `wa=0`, and concurrent processes serialize on a resource that remains **unidentified** (the draft's gt4py-lock explanation was checked against the source and is wrong — the lock is per-program, not global). The work unit's delivered win is Item A (disjointness) alone: ~62 → ~50 min, proven by set arithmetic. Amendments marked inline in the spec | signed-off | `report-0052-disjoint-verification-gates.md` §3 D1/D5/D6; spec-0052 amendment banner | work-0052 merge `fd3f874` |

### Decisions from work unit 0053 (project rename symcon → ICON-sc)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-53.1 | 2026-07-17 | **Sanctioned rebrand of the trunk-frozen `docs/architecture/symcon_architecture.md`** (owner-instructed 2026-07-17; same class as TD-35.5 — an owner-instructed edit of a trunk-frozen document). The file is `git mv`'d to `docs/architecture/icon-sc_architecture.md` and its name-token mentions rewritten `symcon` → `ICON-sc` / import examples → `icon_sc`; the tagline ("A sympl-Conformant Python Architecture for the ICON Model") and **all technical content are unchanged**. Version **retained at v1.3** (a pure rebrand implies no technical revision) with a rev-note recording the rebrand. The `Edit(docs/architecture/**)` deny-glob is unchanged and re-protects the renamed file | signed-off | `report-0053-project-rename-icon-sc.md`; `spec-0053-project-rename-icon-sc.md` | work-0053 merge `a2fab5d` |
| TD-53.2 | 2026-07-17 | **Import namespace `symcon` → `icon_sc`; distributions `symcon-{core,icon,bridges}`/`-workspace` → `icon-sc-*`; brand → ICON-sc** (owner-instructed 2026-07-17). `ICON-sc` is not a legal Python identifier, so the import root is `icon_sc` (`icon_sc.core/.icon/.bridges`). PEP 420 namespace-package semantics preserved (no top-level `__init__.py`); import-linter contracts hold 2 kept / 0 broken under the new names; no dependency pin moved (`uv.lock` regenerated, registry (name,version) set identical; `constraints/` untouched) | signed-off | `spec-0053-project-rename-icon-sc.md` Frozen interfaces | work-0053 merge `a2fab5d` |
| TD-53.3 | 2026-07-17 | **Scope boundary — rename the current system, preserve frozen history** (owner-instructed 2026-07-17, "Preserve history"). Renamed: live code/config, living policies, root docs, the published `docs/` site (incl. the architecture doc), reference cards, and the work-unit **specs**. **Exempt** (kept verbatim as historical record): `REGISTRY.md` §2/§2b/§2c remap columns and signed-off `TD-*` wording; frozen `development/work/plans/*` (0001–0052), `reports/*`, `proposals/*`, `ADRs/*`; `references/lock.toml` evidence; the `layout-doc-revision.diff` artifact. Rewriting those would falsify signed-off history and break the remap bridge (e.g. `REGISTRY.md:151` names `symcon_repo_layout.md`, a file that no longer exists). The by-design residual `symcon` hits are enumerated in the report | signed-off | `report-0053-project-rename-icon-sc.md` | work-0053 merge `a2fab5d` |
| TD-53.4 | 2026-07-17 | **Amendments to the TD-53.3 scope** (owner-instructed 2026-07-17). (a) The frozen work-unit **plans** (0001–0052) are also renamed (current-system identifiers only; migration-plan §3 rename tables carry no `symcon`; the historical `symcon_repo_layout.md` is preserved). (b) The living layout policy `development/policies/repo-layout.md` is renamed to `repository-layout.md` (kebab, TD-51.1); the historical `symcon_repo_layout` token is de-branded to `repository-layout` **only in the living policies + current-unit docs**, while every frozen record keeps `symcon_repo_layout.md` verbatim — this §2 remap "Old" column, `TD-33.4`, the migration **plans 0033/0035**, the frozen reports, and `layout-doc-revision.diff` — de-branding the §2 "Old" column would falsify the remap bridge and collide with the new current filename `repository-layout.md` | signed-off | `report-0053-project-rename-icon-sc.md` §3 | work-0053 merge `a2fab5d` |
