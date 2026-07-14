# REGISTRY — document numbers and trunk decisions

One file, two registers: the document-number register (§1, with the permanent old→new
remap table in §2) and the trunk-decision/sign-off register (§3). Rules for the
decision register: append-mostly (rows are added, and their `Status` field updated in
place; nothing else is edited); every new `TD-PENDING:` line in any record gets a row
here **in the same PR**; decision text that quotes a tolerance or signature is copied
verbatim from its source. This register supersedes
`development/records/036_implementation_report_record.md` §5 (sign-off ledger) and §6
(standing follow-ups) going forward — that report stays frozen as the historical record.
Conventions: ID `TD-<origin>.<k>` where origin is the work unit (`S08`, `27`, `35`) that
raised it. Status: `pending` / `signed-off` / `rejected` / `superseded(TD-…)`. `Date` is the date the
decision entered main (the merge of its source).
Formerly DECISIONS.md (renamed in work unit 035, TD-35.3); before that
plan/TRUNK_DECISIONS.md.

Seeded 2026-07-13 by work unit 031 (spec: `development/records/029_plan_structure_record/29_plan_structure.md` §8).

## 1. Document register (the single allocator)

A number is allocated by adding a row here **at assignment**, even when the plan text
is delivered ad hoc and never committed (the row says so). Numbers are strictly
monotonic, never reused; gaps are never backfilled — 015–019 stay open forever. On a
collision, the first-registered number wins and the latecomer takes the next free one.
One number per work unit, shared by its idea/spec/plan/record files
(`NNN_<slug>_<kind>`, TD-35.1, adr 046); single-kind documents consume one number.
**Next free number: 049.**

| NNN | slug | kinds | status |
|---|---|---|---|
| 000 | overview | record | executed (S01–S14 slice overview, frozen) |
| 001 | repo_scaffold | spec + plan + record | executed |
| 002 | core_state_contracts | spec + plan + record | executed |
| 003 | component_abi_t0 | spec + plan + record | executed |
| 004 | coupling_algebra | spec + plan + record | executed |
| 005 | vault_plan_t1 | spec + plan + record | executed |
| 006 | vertical_grid_thermo | spec + plan + record | executed |
| 007 | satad_component | spec + plan + record | executed |
| 008 | graupel_component | spec + plan + record | executed |
| 009 | scm_composition | spec + plan + record | executed |
| 010 | ftier_column_gradients | spec + plan + record | executed |
| 011 | icon_grid_metrics | spec + plan + record | executed |
| 012 | nonhydro_hosting | spec + plan + record | executed |
| 013 | diffusion_jw_l4 | spec + plan + record | executed |
| 014 | plan_through_dycore | spec + plan + record | executed |
| 020 | gpu_validation | plan | pending |
| 021 | ci_hardening | plan | pending |
| 022 | plan_hash_config_digest | plan | pending |
| 023 | upstream_reports | plan | pending |
| 024 | pr_publication | plan | pending |
| 025 | cf_multistage_t1 | plan | pending |
| 026 | gridgen_integration | record | executed (plan ad hoc, not committed) |
| 027 | docs_plan | record | executed (plan ad hoc, not committed) |
| 028 | docs_implementation | plan + record | executed |
| 029 | plan_structure | record | executed (plan ad hoc, not committed) |
| 030 | author_phase_specs | plan | pending |
| 031 | plan_structure_migration | record | executed (plan: 029 record §8) |
| 032 | docs_development_structure | record | executed (plan ad hoc, not committed) |
| 033 | structure_migration | plan + record | executed |
| 034 | naming_iteration | record | executed (plan ad hoc, not committed) |
| 035 | naming_migration | plan + record | this work unit |
| 036 | implementation_report | record | executed (S01–S14 slice process record, frozen) |
| 037 | p2_distributed | idea | accepted-roadmap |
| 038 | p3_full_physics | idea | accepted-roadmap |
| 039 | p4_ingestion_realdata | idea | accepted-roadmap |
| 040 | p5_tiers_t2_t3 | idea | accepted-roadmap |
| 041 | p6_differentiable_distributed_da | idea | accepted-roadmap |
| 042 | p7_presets_docs_anemoi | idea | accepted-roadmap |
| 043 | development_tree_reorganization | adr | accepted |
| 044 | content_frozen_records | adr | accepted |
| 045 | decision_register_and_adrs | adr | accepted |
| 046 | document_naming_scheme | adr | accepted |
| 047 | docs_stack | adr | accepted |
| 048 | gridgen_adoption | adr | accepted |

Numbers 000–014 are the remapped S-series work units. The old N-series number 10
(the review protocol) is superseded by this remap: the protocol is a policy
(`policies/review_protocol.md`), unnumbered and exempt from the scheme. Numbers 015–019
were never allocated and stay open per the never-backfill rule.

## 2. Remap table (permanent — the bridge for historical names and `REFERENCES.lock` ids)

Old→new for every file renamed by work unit 035 (commit C1). Historical wording in
frozen records ("step S08", "task 26", `ADR-0002`, old paths) translates via this
table; `REFERENCES.lock` step ids ("S08") stay as written and resolve here.

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

## 3. Decision register

### Sign-off items from the 001–014 slice (mirrors IMPLEMENTATION_REPORT §5, verbatim)

| ID | Date | Decision (verbatim from source) | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-S05.1 | 2026-07-09 | Zero-traffic acceptance operationalization (settrace can't see C-level `dict.__getitem__`; tracemalloc protocol) | pending | `development/records/005_vault_plan_t1_record/STATUS.md` deviations 4–5 banner; IMPLEMENTATION_REPORT §5 | — |
| TD-S08.1 | 2026-07-10 | `CONSERVATION_RTOL_COLD = 1e-3` (characterized cold-glaciation leak; upstream report follow-up) | pending | `development/records/008_graupel_component_record/STATUS.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S09.1 | 2026-07-11 | Tracer negativity `≥ −QMIN`; whole-run `CONSERVATION_RTOL = 1e-11` | pending | `development/records/009_scm_composition_record/STATUS.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S10.1 | 2026-07-11 | QMIN atol floor on acceptances 1/7 | pending | `development/records/010_ftier_column_gradients_record/STATUS.md` tolerance note; IMPLEMENTATION_REPORT §5 | — |
| TD-S12.1 | 2026-07-11 | vn `atol = 1e-11` on EXCLAIM_APE multi-substep parity (reviewer recommends granting) | pending | `development/records/012_nonhydro_hosting_record/STATUS.md` deviation 8; IMPLEMENTATION_REPORT §5 | — |
| TD-S13.1 | 2026-07-12 | `jablonowski_williamson` mandatory `static` kwarg (frozen-signature change); pooch→sha256-manifest swap | pending | `development/records/013_diffusion_jw_l4_record/STATUS.md` deviations 6, 11; IMPLEMENTATION_REPORT §5 | — |
| TD-S14.1 | 2026-07-13 | "Bitwise per backend" evidence-backed for gtfn_cpu only (gpu leg never executed) | pending | `development/records/014_plan_through_dycore_record/STATUS.md` review-fixes note; IMPLEMENTATION_REPORT §5 | — |

### Decisions from work unit 027 (docs stack) — executed by work unit 028

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-27.1 | 2026-07-13 | Docs stack: Sphinx + MyST-Parser + Napoleon + furo; layout-doc line "`docs/api/` # sphinx + autodoc from py.typed sources" is complied with via MyST (no layout-doc edit required to proceed); MkDocs alternative rejected | signed-off | `development/records/027_docs_plan_record/27_docs_plan.md` §3.2 (TD-1) | task-28 merge `cbbec36` |
| TD-27.2 | 2026-07-13 | Docs dependency additions: dev-group lower bounds `sphinx>=8.1`, `myst-parser>=4.0`, `furo>=2025.12.19`; `constraints/cpu-ci.txt` pins sphinx==8.1.3, myst-parser==4.0.1, furo==2025.12.19, docutils==0.21.2 | signed-off | `27_docs_plan.md` §3.3 (TD-2) | task-28 merge `cbbec36` |
| TD-27.3 | 2026-07-13 | Docstring convention: Google-style sections going forward, Napoleon-parsed; existing corpus kept, convert-on-touch; ruff `D` with shrink-only ignore baseline | signed-off | `27_docs_plan.md` §3.4/§4 (TD-3) | task-28 merge `cbbec36` |

### Decisions from work unit 029 (plan-structure proposal)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-29.1 | 2026-07-13 | Zero-move plan structure ratified: `plan/prompts/reports/` stays the single deliverables tree with kind-labelled index; task-27 subdir pattern blessed for document-deliverables (task 29's own location conforms) | superseded(TD-33.1) | `29_plan_structure.md` §4, §7 | task-31 merge `58a51f7` |
| TD-29.2 | 2026-07-13 | Create `development/REGISTRY.md` (this file) + `TD-PENDING:` marker | signed-off | `29_plan_structure.md` §5.1, §7 | task-31 merge `58a51f7` |
| TD-29.3 | 2026-07-13 | N-series allocation rule + forward SPEC/STATUS templates adopted (recorded in `development/archive/plan_tree_map.md`; register + allocation rule in prompts-README) | signed-off | `29_plan_structure.md` §3.2–3.3, §7, §8 items A/C | task-31 merge `58a51f7` |
| TD-29.4 | 2026-07-13 | Extend unexecuted task 24's scope with a thin `CONTRIBUTING.md` at publication time | pending | `29_plan_structure.md` §5, §7 | — |
| TD-29.5 | 2026-07-13 | Generalize `.github/PULL_REQUEST_TEMPLATE.md` line 3 to cover tasks as well as steps | pending | `29_plan_structure.md` §7 | — |
| TD-29.6 | 2026-07-13 | Home for future external-facing drafts beyond tasks 23/24 (`plan/drafts/` vs `reports/<theme>/`) | superseded(TD-33.1) | `29_plan_structure.md` §7 | — |
| TD-29.7 | 2026-07-13 | Apply the layout-doc §4 revision (drafted diff: docs/ tree incl. conf.py/tutorials/glossary/names_registry carve-out/api reword, docs.yml workflow line, v1.2→v1.3 errata, self-listing); absorbs 27 §3.2's additive clarification | superseded(TD-33.4) | `29_plan_structure.md` §6.3 | — |
| TD-29.8 | 2026-07-13 | Root README refresh (drop the stale pre-implementation status; current Contents) | signed-off | `29_plan_structure.md` §7 | task-31 merge `58a51f7` |
| TD-29.9 | 2026-07-13 | No CHANGELOG until the P7 versioning/release step; format (Keep-a-Changelog vs towncrier) decided together with the release tooling then. (ID beyond the proposal's numbered 29.1–29.8: the CHANGELOG verdict in §5 was required but unnumbered.) | signed-off (deferral) | `29_plan_structure.md` §5 | task-31 merge `58a51f7` |
| TD-29.10 | 2026-07-13 | Trunk-owned wording amendments: AGENTS.md Workflow item 6 (extend the STATUS/PR sentence to cover tasks) and the prompts-README invariants paragraph (point sign-off flags at this register) — per proposal §5.1/§7 | pending — trunk-only edits | `29_plan_structure.md` §5.1, §7 | — |

### Decisions from work unit 033 (structure migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-33.1 | 2026-07-14 | `development/` tree reorganization adopted per task-32 evaluation as amended by owner iteration; full migration; `plan/` deleted. **Supersedes TD-29.1** (zero-move) **and TD-29.6** (external-drafts home: resolved as "no dedicated folder") | signed-off | adr 043 + `development/plans/033_structure_migration_plan.md` §1 | task-33 merge `10ecafb` |
| TD-33.2 | 2026-07-14 | Content-frozen amendment: "frozen" = content-frozen; mechanical path retargeting confined to link/path strings permitted in sanctioned migration commits, isolated for word-diff verification | signed-off | adr 044 | task-33 merge `10ecafb` |
| TD-33.3 | 2026-07-14 | Register renamed/moved to `development/DECISIONS.md`; ledger/ADR no-merge relationship (register = sign-off rows, `adr/` = reasoning; architecture-shaped decisions get both) | signed-off | adr 045 | task-33 merge `10ecafb` |
| TD-33.4 | 2026-07-14 | Proposed revision of `docs/architecture/symcon_repo_layout.md` repo tree (diff artifact `development/records/033_structure_migration_record/layout_doc_revision.diff`); owner applies or rejects. Marks the re-draft of TD-29.7 | signed-off | `development/plans/033_structure_migration_plan.md` §5.13 | owner-applied, trunk commit `f053659` |

### Decisions from work unit 035 (naming migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-35.1 | 2026-07-14 | `NNN_<slug>_<kind>` naming scheme: one global three-digit sequence, one number per work unit shared across its idea/spec/plan/record files, kind suffix = singular folder name; exempt: `policies/*`, all `README.md`, `REGISTRY.md`, `archive/*` contents; history remapped, never renumbered (§2); ADR citation form `adr NNN`; forward branch convention `work/NNN-<slug>` | signed-off | `adr 046`; 034 evaluation §3/§9 (`development/records/034_naming_iteration_record/34_naming_iteration.md`) | work-035 merge `d3257df` |
| TD-35.2 | 2026-07-14 | Repo-layout doc moved to `development/policies/repo_layout.md` (living policy, trunk-gated) and removed from the published site; the canonical trunk-frozen set is `docs/architecture/symcon_architecture.md` alone | signed-off | 034 evaluation §2 | work-035 merge `d3257df` |
| TD-35.3 | 2026-07-14 | `DECISIONS.md` renamed `REGISTRY.md`, absorbing the document-number allocator from `plans/README.md`: one file, two registers (documents + trunk decisions) | signed-off | 034 evaluation §1 | work-035 merge `d3257df` |
| TD-35.4 | 2026-07-14 | F1: `.claude/settings.json` deny glob narrowed `Edit(development/specs/**)` → `Edit(development/specs/*_spec.md)` — spec files stay protected, the living `specs/README.md` becomes editable | signed-off | 035 record §6 F1 | trunk commit `1980f0d` |
| TD-35.5 | 2026-07-14 | F2: output paths in the unexecuted plans 020–025/030 and the idea `Status:` headers restated in the `NNN_<slug>_<kind>` scheme — a sanctioned edit of frozen-at-assignment plans (unconsumed contracts; owner-instructed), same class as the 032 evaluation decision point 10 | signed-off | 035 record §6 F2 | trunk commit `1980f0d` |
