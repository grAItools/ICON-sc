# Work unit 035 — naming-convention migration (`NNN_<slug>_<kind>`, REGISTRY, layout-doc policy)

**Branch:** `work/035-naming-migration` (this plan is committed on it; execution continues on
the same branch — one PR). First document born under the convention it implements.

**Deliverable:** the migration executed per this plan + the record
`development/work/reports/report-0035-naming-migration.md`.

This plan is frozen at assignment. It implements the owner-accepted evaluation
`development/records/34_naming_iteration/34_naming_iteration.md` (all §9 recommendations
confirmed 2026-07-14). Where this plan conflicts with reality, stop, record the discrepancy
in your report, and resolve only what is mechanical and obvious.

---

## 1. The agreed decisions (binding)

1. **Naming scheme** for lifecycle documents in `development/`: `NNN_<slug>_<kind>.md`
   (or `NNN_<slug>_<kind>/` for multi-file), NNN = three-digit global sequence, one number
   per work unit shared across its idea/spec/plan/record, kind suffix = singular folder
   name (`idea`, `spec`, `plan`, `record`, `adr`). **Exempt:** `policies/*` (snake_case,
   unnumbered), all `README.md`, `REGISTRY.md`, `archive/*` contents.
2. **`DECISIONS.md` → `REGISTRY.md`**, absorbing the document-number allocator from
   `plans/README.md`: one file, two registers (documents + trunk decisions).
3. **`docs/architecture/symcon_repo_layout.md` → `development/policies/repo_layout.md`**,
   restructured as a living policy, removed from the published site.
4. **Terminology sweep** (living files + tooling only): "step"/"task"/"prompt" vocabulary →
   kind vocabulary ("work unit NNN", spec/plan/record). Frozen records keep historical
   wording (ADR-0002 content-frozen rule); only path strings change there.
5. **Forward branch convention**: `work/NNN-<slug>` (this branch is the first).
6. **Three new ADRs**: the naming scheme itself + two retroactive (docs stack, gridgen).

## 2. Hard rules (restated; violations = stop and report)

- Verify `git branch --show-current` = `work/035-naming-migration` before every commit.
  Never commit to `main`. Never `git push`. Commits end with the `Co-Authored-By:` trailer.
- **No data files, no pin changes, no tolerance changes.** `REFERENCES.lock` is untouched
  (its historical `step` ids like "S08" stay; the REGISTRY remap table is the bridge).
- `docs/architecture/symcon_architecture.md` is never edited. The layout doc is the ONLY
  file leaving `docs/architecture/` (sanctioned trunk decision TD-35.2). Note: the Edit
  deny-glob covers `docs/architecture/**`, so perform the move with `git mv` + write the
  new policy file fresh (Bash/Write on the new path only; never Edit the old path).
- Frozen documents (everything in `specs/`, S-series and 020–033 files in `plans/`,
  everything in `records/` except this work unit's own record, `ideas/*`, existing
  `adr/*`, `archive/*`) receive **only** path-string retargeting — no wording changes.
- `packages/` edits are limited to the path-string updates in §6.4. Full gate battery
  before the PR; never use `-x`/`--ignore`/`-k`/marker edits to pass.

## 3. The rename map (commit C1 — `git mv` only)

72 renames. S-series slugs are the existing folder/file slugs; verify each `git mv` target
against this table.

**specs/ (14):** `S01_repo_scaffold.md → 001_repo_scaffold_spec.md`,
`S02_core_state_contracts.md → 002_core_state_contracts_spec.md`,
`S03_component_abi_t0.md → 003_component_abi_t0_spec.md`,
`S04_coupling_algebra.md → 004_coupling_algebra_spec.md`,
`S05_vault_plan_t1.md → 005_vault_plan_t1_spec.md`,
`S06_vertical_grid_thermo.md → 006_vertical_grid_thermo_spec.md`,
`S07_satad_component.md → 007_satad_component_spec.md`,
`S08_graupel_component.md → 008_graupel_component_spec.md`,
`S09_scm_composition.md → 009_scm_composition_spec.md`,
`S10_ftier_column_gradients.md → 010_ftier_column_gradients_spec.md`,
`S11_icon_grid_metrics.md → 011_icon_grid_metrics_spec.md`,
`S12_nonhydro_hosting.md → 012_nonhydro_hosting_spec.md`,
`S13_diffusion_jw_l4.md → 013_diffusion_jw_l4_spec.md`,
`S14_plan_through_dycore.md → 014_plan_through_dycore_spec.md`.

**plans/ (23):** the same 14 S-series slugs with `_plan.md`; plus
`20_gpu_validation.md → 020_gpu_validation_plan.md`,
`21_ci_hardening.md → 021_ci_hardening_plan.md`,
`22_plan_hash_config_digest.md → 022_plan_hash_config_digest_plan.md`,
`23_upstream_reports.md → 023_upstream_reports_plan.md`,
`24_pr_publication.md → 024_pr_publication_plan.md`,
`25_cf_multistage_t1.md → 025_cf_multistage_t1_plan.md`,
`28_docs_implementation.md → 028_docs_implementation_plan.md`,
`30_author_phase_specs.md → 030_author_phase_specs_plan.md`,
`33_structure_migration.md → 033_structure_migration_plan.md`.

**records/ (24):** `00_OVERVIEW.md → 000_overview_record.md`; the 14 S-series folders →
`001…014_<slug>_record/` (inner files unchanged);
`26_gridgen_integration_REPORT.md → 026_gridgen_integration_record.md`,
`27_docs_plan/ → 027_docs_plan_record/`,
`28_docs_implementation_REPORT.md → 028_docs_implementation_record.md`,
`29_plan_structure/ → 029_plan_structure_record/`,
`31_plan_structure_migration_REPORT.md → 031_plan_structure_migration_record.md`,
`32_docs_development_structure/ → 032_docs_development_structure_record/`,
`33_structure_migration/ → 033_structure_migration_record/`,
`34_naming_iteration/ → 034_naming_iteration_record/`,
`IMPLEMENTATION_REPORT.md → 036_implementation_report_record.md`.

**ideas/ (6):** `P2_distributed.md → 037_p2_distributed_idea.md`,
`P3_full_physics.md → 038_p3_full_physics_idea.md`,
`P4_ingestion_realdata.md → 039_p4_ingestion_realdata_idea.md`,
`P5_tiers_t2_t3.md → 040_p5_tiers_t2_t3_idea.md`,
`P6_differentiable_distributed_da.md → 041_p6_differentiable_distributed_da_idea.md`,
`P7_presets_docs_anemoi.md → 042_p7_presets_docs_anemoi_idea.md`.

**adr/ (3):** `0001-development-tree-reorganization.md → 043_development_tree_reorganization_adr.md`,
`0002-content-frozen-records.md → 044_content_frozen_records_adr.md`,
`0003-decision-register-and-adrs.md → 045_decision_register_and_adrs_adr.md`.

**root of development/ (1):** `DECISIONS.md → REGISTRY.md`.

**docs/ (1):** `git mv docs/architecture/symcon_repo_layout.md development/policies/repo_layout.md`
(content restructure happens in C3, not here).

Commit C1; verify: `git show --summary -M100 HEAD | grep -cE "^ rename"` = 72 and no
non-`R100` lines in `git show -M100 --name-status --format="" HEAD`.

## 4. Path retargeting (commit C2 — path strings only)

Apply left→right, longest prefix first, to every `.md`/`.diff` under `development/` and the
living root files. Old→new for every C1 rename (the §3 table *is* the mapping), noting:

- `development/DECISIONS.md` → `development/REGISTRY.md` (and bare `DECISIONS.md` where it
  names the file).
- `docs/architecture/symcon_repo_layout.md` → `development/policies/repo_layout.md`.
- `ADR-0001`/`ADR-0002`/`ADR-0003` **as citations in LIVING files** → `adr 043`/`adr 044`/
  `adr 045` (new citation form). In frozen records these tokens are wording, not paths —
  leave them; the remap table translates.
- Never touch: `symcon/core/plan/`, `plan/ops.py`, plan-hash cache paths, `REFERENCES.lock`,
  `docs/architecture/symcon_architecture.md`, prose words ("the plan", "step" as wording in
  frozen files), and the §3 table inside THIS plan (self-referential, like 033's).
- The self-exemptions from 033 carry forward: `plans/033_structure_migration_plan.md` keeps
  its old-tree tables verbatim except where a string names a file that C1 just renamed
  *as a current path* — apply the same judgment 033's C2 applied, and list ambiguous
  leftovers in the report.

Verify purity (word-diff = path strings only), then commit C2.

## 5. New and restructured content (commit C3)

1. **`development/policies/repo_layout.md`** — restructure the moved layout doc into the
   policies format: one-line scope sentence; keep the §repo-tree (including the
   `development/` node from TD-33.4), packaging/namespace rules, import-boundary contracts,
   typing/caching conventions; DROP the "trunk-frozen companion to v1.3" framing (it is a
   living policy now, trunk-gated like the others); keep all technical content — this is a
   reformat, not a rewrite; do not invent or delete rules.
2. **`development/REGISTRY.md`** — retitle H1
   `# REGISTRY — document numbers and trunk decisions`; add under the header rules:
   `Formerly DECISIONS.md (renamed in work unit 035, TD-35.3); before that plan/TRUNK_DECISIONS.md.`
   New §1 **Document register**: move the allocator table from `plans/README.md` here,
   restated in the new scheme — columns `NNN | slug | kinds | status`; rows: 000 overview
   (record), 001–014 (spec+plan+record each, executed), 020–025/028/030 (plan, pending),
   021 etc. per current statuses, 026/027/029/031/032/034 (record, executed), 033 (plan+
   record, executed), 035 (plan+record, this unit), 036 (record), 037–042 (idea,
   accepted-roadmap), 043–048 (adr, accepted), next free = 049. Allocation rules verbatim
   (at assignment, monotonic, no reuse, no backfill — gaps 015–019 stay open). New §2
   **Remap table**: the complete §3 old→new map (permanent; the bridge for historical
   names and `REFERENCES.lock` ids). Decision tables follow unchanged, plus new rows:
   - **TD-35.1** — `NNN_<slug>_<kind>` scheme + global sequence + number-per-work-unit +
     exemptions, per 034 evaluation §3/§9. Source: `adr 046`. pending/(merge).
   - **TD-35.2** — repo-layout doc moved to `policies/repo_layout.md`, unpublished; the
     canonical set is now `symcon_architecture.md` alone. Source: 034 evaluation §2.
   - **TD-35.3** — REGISTRY rename + allocator absorption. Source: 034 evaluation §1.
3. **Three ADRs** (Nygard sections, ≤60 lines, facts from the named sources only):
   - `adr/046_document_naming_scheme_adr.md` — from 034 evaluation §3 (+ its decision
     points 3/5): global sequence, shared work-unit number, kind suffixes, exemptions,
     remap-not-renumber-history, ADR citation form `adr NNN`. Alternatives: per-kind
     sequences, per-document numbers, literal-always numbering.
   - `adr/047_docs_stack_adr.md` — from `records/027_docs_plan_record/27_docs_plan.md`
     and the TD-27.1–3 rows: Sphinx 8.1.3 + MyST + Napoleon + furo, docutils pin,
     Pages-artifact deploy, Google-style docstrings, convert-on-touch. Alternatives
     considered per the 027 record (MkDocs et al.).
   - `adr/048_gridgen_adoption_adr.md` — from `records/026_gridgen_integration_record.md`:
     icon-grid-generator as archive-independent fixture source; **not-for-parity
     boundary**; version-keyed cache; quarantine in `symcon.icon.testing`; version bumps
     are trunk decisions.
4. **`development/README.md`** — add: the naming convention (≤6 lines); the lifecycle
   (idea → spec → plan → record, with one-line kind definitions and liveness); the
   cross-cutting instruments (policies, adr, REGISTRY); `archive/` purpose (superseded/
   irrelevant documents kept for historical reference — dead, never authoritative).
5. **`adr/README.md`** — reindex for the renamed + new ADRs and the `adr NNN` citation
   form; note the 0001–0003 → 043–045 remap. **Folder READMEs** (specs/ideas/plans/
   records) — update naming examples to the new scheme.

## 6. Living-file edits and tooling (commit C4)

1. **`plans/README.md`** — remove the allocator table (now REGISTRY §1, leave a pointer);
   keep the how-to-use instructions; terminology sweep; execution-order table renamed to
   the new filenames.
2. **Terminology sweep** over living files ONLY: `AGENTS.md`, `CLAUDE.md`, root
   `README.md`, `.github/PULL_REQUEST_TEMPLATE.md`, all `development/policies/*.md`,
   `development/README.md`, folder READMEs, `REGISTRY.md` headers/columns. Replace
   step/task/prompt vocabulary with work-unit/kind vocabulary; update the authority-order
   sentence to `docs/architecture/symcon_architecture.md (v1.3) > development/specs/NNN_*_spec.md
   > development/plans/NNN_*_plan.md`; branch convention → `work/NNN-<slug>` in
   `agent_workflow.md` + `naming_conventions.md` (which also gets the full scheme +
   exemptions, replacing the S/P/N-series section — history explained via the remap
   table). Frozen files: wording untouched.
3. **Command files**: `git mv .claude/commands/implement-step.md .claude/commands/implement-plan.md`
   (same for `.opencode/command/`), `review-step.md → review-work.md` in both; rewrite
   contents for the new paths and argument (`$ARGUMENTS` = `NNN_<slug>`): spec at
   `development/specs/$ARGUMENTS_spec.md`, plan at `development/plans/$ARGUMENTS_plan.md`,
   record at `development/records/$ARGUMENTS_record/`. Update `CLAUDE.md`'s
   `/implement-step` line.
4. **Code path strings** (the only `packages/`/`benchmarks/` edits):
   `packages/symcon-core/tests/test_order_ode.py` (docstring line ~9 + path line ~101) and
   `test_order_burgers.py` (~87): `records/S04_coupling_algebra/artifacts` →
   `records/004_coupling_algebra_record/artifacts`; `benchmarks/s05_dispatch.py:4` and
   `benchmarks/dispatch_overhead/jw_step.py:4` docstrings → the renamed record paths.
   `.gitignore`'s `development/records/*/artifacts/` still matches — no change.
5. **`docs/index.md`** — remove toctree entry `architecture/symcon_repo_layout` (line ~73);
   rewrite the line-47/48 sentence to link only the architecture document, with the layout
   policy mentioned in plain prose (no link — docs-boundary policy).

## 7. Commit sequence and gates

| Commit | Content | Purity |
|---|---|---|
| C1 | 72 `git mv` renames (§3) | all R100, count = 72 |
| C2 | path retargets (§4) | word-diff = path strings only |
| C3 | new/restructured content (§5) | named files only |
| C4 | living edits + tooling + code strings + docs/index (§6) | named files only |
| C5 | record + review-round fixes | — |

Gates (all must pass; baselines in `development/policies/verification-gates.md`, unchanged:
739/1 · 31 · 43 · 76/1 · ruff clean/173 files · mypy 50 · lint-imports 2 ·
sphinx `-E -W --keep-going` exit 0). Long pytest runs: detached background with
`EXIT:$?` sentinel logs under `/tmp/`, poll actively — never end a turn waiting for a
notification that will not come. Additional checks:

1. Residual grep — each must return nothing outside this plan, the REGISTRY remap table,
   and frozen wording (list every by-design hit in the record):
   `grep -rnE "development/(specs|plans)/S[0-9]{2}_" . --exclude-dir=.git`;
   `grep -rnE "records/(S[0-9]{2}_|00_OVERVIEW|IMPLEMENTATION_REPORT|[0-9]{2}_[a-z])" . --exclude-dir=.git`
   (two-digit prefixes must be gone as paths);
   `grep -rn "DECISIONS.md" . --exclude-dir=.git` (only formerly-lines/frozen prose);
   `grep -rn "symcon_repo_layout" . --exclude-dir=.git` (only frozen prose + remap);
   `grep -rnE "ideas/P[2-7]_|adr/000[1-3]" . --exclude-dir=.git`.
2. The task-33 link checker (in `033_structure_migration_plan.md` §7.2) re-run: 0 BROKEN.
3. `ls docs/architecture/` = `symcon_architecture.md` only; `docs/_build` sphinx green
   (the dropped page must not orphan any reference — `-W` catches it).
4. Terminology check on living files:
   `grep -rniE "\b(step S[0-9]|task [0-9]{2}|prompt)\b" AGENTS.md CLAUDE.md README.md development/policies/ development/README.md .github/PULL_REQUEST_TEMPLATE.md`
   → zero hits (kind vocabulary only). Frozen files excluded by construction.
5. `git diff main -- docs/architecture/symcon_architecture.md REFERENCES.lock constraints/ uv.lock` empty.

## 8. Record — `development/work/reports/report-0035-naming-migration.md`

Per the STATUS template: rename ledger (72 confirmed), retarget statistics + judgment
calls, REGISTRY restructure summary, gate outputs verbatim and dated, deviations,
follow-ups. Any §7.1 by-design hit gets one line each.

## 9. Review checklist (fresh reviewer; protocol `development/policies/review-protocol.md`)

1. C1 purity (72 R100) and C2 purity (word-diff spot-check ≥5 frozen files — wording
   change in frozen content is MAJOR; also verify ADR-000N → `adr 04N` citations changed
   ONLY in living files).
2. Frozen integrity: ≥3 specs + 2 records byte-identical modulo path strings.
3. `repo_layout.md` policy: content-complete vs the old doc (`git diff` old blob → new
   file must show reformat + framing drop only, no rule lost or invented); docs/index
   edits correct; sphinx green.
4. REGISTRY: document register rows complete and statuses correct vs the old allocator
   table; remap table complete vs §3; TD-35.1–3 present pending; no other row cells
   changed beyond §4 path strings.
5. ADRs 046–048: every fact traced to the named source records (unsourced fact = MAJOR);
   README index consistent.
6. Re-run §7 checks 1–5 and the full gate battery (or log-verify long partitions against
   dated sentinel logs if inputs unchanged — state which).
7. Report honesty; deviations verified individually.

Verdict `approve` / `request-changes` with MAJOR/MINOR/INFO + file:line evidence.
