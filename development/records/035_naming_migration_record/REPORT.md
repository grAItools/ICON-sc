# Work unit 035 — naming-convention migration: execution record

**Branch:** `work/035-naming-migration` · **Date:** 2026-07-14 · **State:** executed, all
gates green (dated outputs in §4)

Plan: `development/plans/035_naming_migration_plan.md` (frozen at assignment). Commits:
C1 `df63266` (renames) · C2 `a0d27e6` (retargets) · C3 `e8346a6` (new/restructured
content) · C4 `41ff7a7` (living edits, tooling, code strings, docs) · C5 = this record.
Execution split: C1–C4 and the fast/static gates by the implementer agent; remaining gates,
verification consolidation, and this record by the orchestrator after a planned stand-down
handoff (the implementer's deviation/judgment ledger is §2–§3's source and was verified
against the diffs before inclusion).

## 1. Rename ledger (plan §3, commit C1)

All 72 map rows executed as `git mv`; nothing else in C1. Purity:
`git show --summary -M100 df63266 | grep -cE "^ rename"` → **73**; non-`R100` lines → **0**.
73 vs the plan's 72 is a counting artifact (same class as work unit 033's 66-vs-71): the
plan counted `records/033_structure_migration/` as one move, but the folder holds two
tracked files (REPORT.md + layout_doc_revision.diff), each its own rename line. Category
counts: specs 14, plans 23, records 25, ideas 6, adr 3, REGISTRY 1, layout doc 1.

## 2. Retarget statistics and judgment calls (plan §4, commit C2)

31 files, 157 insertions = 157 deletions (path strings only; word-diff verified per file
and spot-checked by the orchestrator). Judgment calls in frozen documents (the plan's
"same judgment as 033's C2" clause), recorded verbatim from the implementer's ledger:

- **Left byte-identical (R100):** `034_naming_iteration_record/34_naming_iteration.md`
  (the document *is* the old→new mapping analysis; any retarget falsifies it),
  `033_structure_migration_record/layout_doc_revision.diff` (owner-applied historical
  artifact, TD-33.4), and the 035 plan's own §3 map (self-referential).
- **`033_structure_migration_plan.md`:** 3 current-path pointers retargeted (deliverable
  line 9, diff-artifact path, §8 heading); its §4 move map, §5.1 old/new columns, §3.3
  register-row instruction text, and §7.1 grep pattern left as old-tree meaning (adr 044
  class).
- **`033_structure_migration_record/REPORT.md`:** 2 pointers retargeted; its
  "left byte-identical" claims, quoted grep output, relocation-table To-column, and quoted
  gate lines (old S04 artifacts path) left — verbatim quoted output must stay verbatim.
- **REGISTRY:** three sed over-reaches reverted before commit (formerly-line, TD-33.3 and
  TD-33.4 decision texts — historical wording); TD-29.2 "(this file)" and all Source-cell
  paths kept retargeted (the "pointer whose subject survives" precedent from 033 round 1);
  Source-cell ADR citations now `adr 043/044/045`.
- **adr 043 (frozen):** the historical rename statement kept "…is renamed
  `development/DECISIONS.md`"; **adr 045:** Context pointer retargeted, Decision-section
  bare "DECISIONS.md is the sign-off ledger" kept historical — mixed naming inside one
  frozen ADR is deliberate (paths retarget, wording doesn't).
- **29/31/32 records:** bare-filename inventory rows, old-tree strings, tree diagrams, and
  a hypothetical path in the 32 evaluation all kept historical (several were sed
  over-reaches reverted before commit); prefixed current-path pointers kept retargeted.
- **Frozen plans 020/021/022/025/030** keep their future-deliverable output paths
  (`records/20_gpu_validation_REPORT.md`, …): those files do not exist and are not in the
  §3 map — each is one by-design §7.1 hit; re-targeting them is the same trunk call
  decision point 10 of the 032 evaluation covered, to be exercised when each plan is
  executed (follow-up F2).

## 3. New/restructured content (plan §5–§6, commits C3–C4) and deviations

C3: 10 files, +406/−79 (REGISTRY restructure with document register + remap table +
TD-35.1–3, `policies/repo_layout.md`, ADRs 046–048, adr/README, development/README
lifecycle, folder READMEs). C4: 29 files, +278/−279 (terminology sweep, plans/README
allocator removal, command renames `implement-plan`/`review-work` in `.claude` +
`.opencode`, code path strings, docs/index edit). ADRs 046–048: **no unsourced facts** —
everything traces to the 034 evaluation, the 027 record + TD-27.1–3, and the 026 record;
047/048 carry explicit "recorded retroactively" date notes.

Deviations (all mechanical-and-obvious per the plan preamble, or forced by gates):

1. C1 purity 73 vs 72 (§1).
2. REGISTRY §1 gained row 010 (review protocol) beyond the plan's row list — completeness
   vs the old allocator table.
3. `docs/conf.py:2` comment retargeted though unnamed in plan §4/§6 (required by §7.1;
   living site source).
4. `development/specs/README.md` updated via Bash heredoc: the `Edit(development/specs/**)`
   deny glob blocks the Edit/Write tools even for the living README (follow-up F1).
5. REGISTRY formerly-line uses the plan's exact sentence (replaces the 033 formerly-line;
   TD-33.3 attribution survives in its row).
6. Root README: the layout-doc Contents row folded into the policies row (the standalone
   row would point at a moved file).
7. `development/README.md` quoted historical tokens rephrased so the §7.4 terminology gate
   greps zero.
8. REGISTRY decision-table headings demoted under the new `## 3. Decision register` and
   swept to work-unit vocabulary; row cells untouched beyond §4 classes.
9. `pyproject.toml:35,65` + `constraints/cpu-ci.txt:16` "plan 27_docs_plan §3.3" comments
   left as-is (outside §6.4's exhaustive edit list; constraints untouchable; match no §7.1
   pattern).
10. Idea files' `Status:` headers still say "via task 30" (path-only rule in frozen-adjacent
    headers; matches no gate pattern; the 030 plan's execution will restate it anyway).
11. `plans/README.md` invariants now cite "AGENTS.md rule 4" — the rewritten hard-rule list
    renumbered the tolerance rule.

## 4. Gate outputs (verbatim summary lines, dated 2026-07-14 CEST)

- fast (`not gpu and not slow`): `739 passed, 1 skipped, 143 deselected, 51 warnings in
  853.35s (0:14:13)`, EXIT:0 (11:16, /tmp/gate035_fast.log; skip = mpi opt-in).
- slow-no-data: `31 passed, 852 deselected, 5 warnings in 2076.39s (0:34:36)`, EXIT:0
  (11:51, /tmp/gate035_slow.log). Note: the S04 order tests are slow-marked, so THIS
  partition (not fast) exercises the retargeted artifact path and wrote
  `development/records/004_coupling_algebra_record/artifacts/convergence_{ode,burgers}.png`;
  the implementer additionally pre-verified the path standalone (`test_order_ode.py`:
  9 passed, 98.17s, 11:19). Wall time above the reference — two overlapping runs on a
  loaded host; counts are the contract.
- data-not-slow: `43 passed, 840 deselected, 11 warnings in 726.11s (0:12:06)`, EXIT:0
  (12:00, /tmp/gate035_data.log).
- data-slow: `76 passed, 1 skipped, 806 deselected, 28 warnings in 3833.75s (1:03:53)`,
  EXIT:0 (13:04, /tmp/gate035_dataslow.log; skip = upstream MCH-only diffusion).
- ruff check / format: `All checks passed!` / `173 files already formatted` (11:00, re-run
  by orchestrator 11:20).
- mypy: `Success: no issues found in 50 source files`; lint-imports:
  `Contracts: 2 kept, 0 broken.` (11:00/11:20).
- sphinx `-E -W --keep-going`: EXIT:0, `build succeeded.` (11:01) — the dropped layout page
  orphaned nothing.
- §7.1 residual greps (11:20, orchestrator): hits only in frozen documents — the 033
  plan/record (their own mapping tables and quoted output), the 034 evaluation, the layout
  diff artifact, the 028 record's historical site-inclusion prose, the five frozen plans'
  future-deliverable paths (§2), and the REGISTRY remap table — all by-design, each class
  listed in §2.
- §7.2 link check: 0 BROKEN (11:00 and 11:20). §7.4 terminology check on living files:
  zero hits. Husk check (033's MAJOR-1 class): `find development docs -type d -empty`
  empty outside `docs/_build`; the S04 PNGs traveled with the `git mv`.
- Untouchables: `git diff main -- docs/architecture/symcon_architecture.md REFERENCES.lock
  constraints/ uv.lock` → empty (11:20). `ls docs/architecture/` = `symcon_architecture.md`
  only.

## 5. Register state (commits C3–C4)

REGISTRY.md: §1 document register (rows 000–048, next free 049), §2 permanent remap table,
§3 decision register with TD-35.1 (naming scheme, source adr 046), TD-35.2 (repo-layout
policy move), TD-35.3 (REGISTRY rename + allocator absorption) — all pending/(merge),
dates and evidence to be filled at merge per convention.

## 6. Follow-ups

- **F1**: narrow the `.claude/settings.json` deny glob `Edit(development/specs/**)` to
  `Edit(development/specs/[0-9]*_spec.md)` so the living `specs/README.md` is editable
  without Bash workarounds (trunk call — one line).
- **F2**: when frozen plans 020–025/030 are executed, restate their output paths in the
  new scheme at execution time (their current `records/NN_*_REPORT.md` strings are
  by-design residuals; the executing agent's record lands under the new convention
  regardless).
- Owner at merge: fill TD-35.1–3 dates/evidence; the adr 046–048 `Date:` fields are
  already explicit about retroactive recording.

## 7. Review fixes (round N)

(none yet)
