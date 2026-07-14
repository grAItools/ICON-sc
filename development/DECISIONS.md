# DECISIONS — trunk-decision and sign-off register

The single place where trunk/human decisions are tracked. Rules: append-mostly (rows are
added, and their `Status` field updated in place; nothing else is edited); every new
`TD-PENDING:` line in any STATUS.md or task report gets a row here **in the same PR**;
decision text that quotes a tolerance or signature is copied verbatim from its source.
This register supersedes `development/records/IMPLEMENTATION_REPORT.md` §5 (sign-off ledger) and §6
(standing follow-ups) going forward — that report stays frozen as the historical record.
Conventions: ID `TD-<origin>.<k>` where origin is the step (`S08`) or task (`27`) that
raised it. Status: `pending` / `signed-off` / `rejected` / `superseded(TD-…)`. `Date` is the date the
decision entered main (the merge of its source).
Formerly plan/TRUNK_DECISIONS.md (renamed in task 33, TD-33.3).

Seeded 2026-07-13 by task 31 (spec: `development/records/29_plan_structure/29_plan_structure.md` §8).

## Sign-off items from the S01–S14 slice (mirrors IMPLEMENTATION_REPORT §5, verbatim)

| ID | Date | Decision (verbatim from source) | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-S05.1 | 2026-07-09 | Zero-traffic acceptance operationalization (settrace can't see C-level `dict.__getitem__`; tracemalloc protocol) | pending | `development/records/S05_vault_plan_t1/STATUS.md` deviations 4–5 banner; IMPLEMENTATION_REPORT §5 | — |
| TD-S08.1 | 2026-07-10 | `CONSERVATION_RTOL_COLD = 1e-3` (characterized cold-glaciation leak; upstream report follow-up) | pending | `development/records/S08_graupel_component/STATUS.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S09.1 | 2026-07-11 | Tracer negativity `≥ −QMIN`; whole-run `CONSERVATION_RTOL = 1e-11` | pending | `development/records/S09_scm_composition/STATUS.md`; IMPLEMENTATION_REPORT §5 | — |
| TD-S10.1 | 2026-07-11 | QMIN atol floor on acceptances 1/7 | pending | `development/records/S10_ftier_column_gradients/STATUS.md` tolerance note; IMPLEMENTATION_REPORT §5 | — |
| TD-S12.1 | 2026-07-11 | vn `atol = 1e-11` on EXCLAIM_APE multi-substep parity (reviewer recommends granting) | pending | `development/records/S12_nonhydro_hosting/STATUS.md` deviation 8; IMPLEMENTATION_REPORT §5 | — |
| TD-S13.1 | 2026-07-12 | `jablonowski_williamson` mandatory `static` kwarg (frozen-signature change); pooch→sha256-manifest swap | pending | `development/records/S13_diffusion_jw_l4/STATUS.md` deviations 6, 11; IMPLEMENTATION_REPORT §5 | — |
| TD-S14.1 | 2026-07-13 | "Bitwise per backend" evidence-backed for gtfn_cpu only (gpu leg never executed) | pending | `development/records/S14_plan_through_dycore/STATUS.md` review-fixes note; IMPLEMENTATION_REPORT §5 | — |

## Decisions from task 27 (docs stack) — executed by task 28

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-27.1 | 2026-07-13 | Docs stack: Sphinx + MyST-Parser + Napoleon + furo; layout-doc line "`docs/api/` # sphinx + autodoc from py.typed sources" is complied with via MyST (no layout-doc edit required to proceed); MkDocs alternative rejected | signed-off | `development/records/27_docs_plan/27_docs_plan.md` §3.2 (TD-1) | task-28 merge `cbbec36` |
| TD-27.2 | 2026-07-13 | Docs dependency additions: dev-group lower bounds `sphinx>=8.1`, `myst-parser>=4.0`, `furo>=2025.12.19`; `constraints/cpu-ci.txt` pins sphinx==8.1.3, myst-parser==4.0.1, furo==2025.12.19, docutils==0.21.2 | signed-off | `27_docs_plan.md` §3.3 (TD-2) | task-28 merge `cbbec36` |
| TD-27.3 | 2026-07-13 | Docstring convention: Google-style sections going forward, Napoleon-parsed; existing corpus kept, convert-on-touch; ruff `D` with shrink-only ignore baseline | signed-off | `27_docs_plan.md` §3.4/§4 (TD-3) | task-28 merge `cbbec36` |

## Decisions from task 29 (plan-structure proposal)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-29.1 | 2026-07-13 | Zero-move plan structure ratified: `plan/prompts/reports/` stays the single deliverables tree with kind-labelled index; task-27 subdir pattern blessed for document-deliverables (task 29's own location conforms) | superseded(TD-33.1) | `29_plan_structure.md` §4, §7 | task-31 merge `58a51f7` |
| TD-29.2 | 2026-07-13 | Create `development/DECISIONS.md` (this file) + `TD-PENDING:` marker | signed-off | `29_plan_structure.md` §5.1, §7 | task-31 merge `58a51f7` |
| TD-29.3 | 2026-07-13 | N-series allocation rule + forward SPEC/STATUS templates adopted (recorded in `development/archive/plan_tree_map.md`; register + allocation rule in prompts-README) | signed-off | `29_plan_structure.md` §3.2–3.3, §7, §8 items A/C | task-31 merge `58a51f7` |
| TD-29.4 | 2026-07-13 | Extend unexecuted task 24's scope with a thin `CONTRIBUTING.md` at publication time | pending | `29_plan_structure.md` §5, §7 | — |
| TD-29.5 | 2026-07-13 | Generalize `.github/PULL_REQUEST_TEMPLATE.md` line 3 to cover tasks as well as steps | pending | `29_plan_structure.md` §7 | — |
| TD-29.6 | 2026-07-13 | Home for future external-facing drafts beyond tasks 23/24 (`plan/drafts/` vs `reports/<theme>/`) | superseded(TD-33.1) | `29_plan_structure.md` §7 | — |
| TD-29.7 | 2026-07-13 | Apply the layout-doc §4 revision (drafted diff: docs/ tree incl. conf.py/tutorials/glossary/names_registry carve-out/api reword, docs.yml workflow line, v1.2→v1.3 errata, self-listing); absorbs 27 §3.2's additive clarification | superseded(TD-33.4) | `29_plan_structure.md` §6.3 | — |
| TD-29.8 | 2026-07-13 | Root README refresh (drop the stale pre-implementation status; current Contents) | signed-off | `29_plan_structure.md` §7 | task-31 merge `58a51f7` |
| TD-29.9 | 2026-07-13 | No CHANGELOG until the P7 versioning/release step; format (Keep-a-Changelog vs towncrier) decided together with the release tooling then. (ID beyond the proposal's numbered 29.1–29.8: the CHANGELOG verdict in §5 was required but unnumbered.) | signed-off (deferral) | `29_plan_structure.md` §5 | task-31 merge `58a51f7` |
| TD-29.10 | 2026-07-13 | Trunk-owned wording amendments: AGENTS.md Workflow item 6 (extend the STATUS/PR sentence to cover tasks) and the prompts-README invariants paragraph (point sign-off flags at this register) — per proposal §5.1/§7 | pending — trunk-only edits | `29_plan_structure.md` §5.1, §7 | — |

## Decisions from task 33 (structure migration)

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-33.1 | (merge) | `development/` tree reorganization adopted per task-32 evaluation as amended by owner iteration; full migration; `plan/` deleted. **Supersedes TD-29.1** (zero-move) **and TD-29.6** (external-drafts home: resolved as "no dedicated folder") | pending | ADR-0001 + `development/plans/33_structure_migration.md` §1 | — |
| TD-33.2 | (merge) | Content-frozen amendment: "frozen" = content-frozen; mechanical path retargeting confined to link/path strings permitted in sanctioned migration commits, isolated for word-diff verification | pending | ADR-0002 | — |
| TD-33.3 | (merge) | Register renamed/moved to `development/DECISIONS.md`; ledger/ADR no-merge relationship (register = sign-off rows, `adr/` = reasoning; architecture-shaped decisions get both) | pending | ADR-0003 | — |
| TD-33.4 | (merge) | Proposed revision of `docs/architecture/symcon_repo_layout.md` repo tree (diff artifact `development/records/33_structure_migration/layout_doc_revision.diff`); owner applies or rejects. Marks the re-draft of TD-29.7 | pending | `development/plans/33_structure_migration.md` §5.13 | — |
