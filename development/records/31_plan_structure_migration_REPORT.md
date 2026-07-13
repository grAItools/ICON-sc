# Task 31 report — plan-structure migration: registers and indexes (zero moves)

**Branch:** `task/29-plan-structure` (items executed immediately after the task-29
proposal on owner instruction — see Deviations) · **Date:** 2026-07-13 ·
**Spec:** `development/records/29_plan_structure/29_plan_structure.md` §8 ·
**Commits:** items A–E one commit each (`f009d5b`, `48212ab`, `199f967`, `aa7dbc6`,
`06585c8`) + this report.

## Per-item summary

- **A — `development/archive/plan_tree_map.md`** (new): exactly 4 sections (taxonomy table, naming convention
  incl. N-series allocation rule, forward SPEC/STATUS templates incl. the
  artifact-regeneration-command rule, plan/docs boundary policy). `grep -c "^## "` = 4.
- **B — `development/DECISIONS.md`** (new): rule paragraph + 19 rows: 7 slice sign-off
  items copied verbatim from `IMPLEMENTATION_REPORT.md` §5 (status `pending`, no
  evidence yet); TD-27.1–3 (`signed-off`, evidence task-28 merge `cbbec36`); TD-29.1–9
  with statuses per the owner's proceed instruction (29.1/2/3/8/9 signed-off,
  29.4/5/6/7 pending). No verbatim-copy discrepancies found against the sources.
  `grep -r "TD-PENDING" plan/` returns only rule/definition text (development/archive/plan_tree_map.md,
  TRUNK_DECISIONS.md, the 29 proposal) — zero live markers, as expected forward-only.
- **C — `development/plans/README.md`** (refresh): added one section ("Task-number
  register") with the allocation rule, the pointer paragraph to `development/archive/plan_tree_map.md` /
  `TRUNK_DECISIONS.md`, and a 13-row register table (10, 20–31). Purely additive:
  `git diff main..HEAD -- development/plans/README.md` has **0 deleted lines**; invariants,
  gate-baseline table, and caches sections byte-identical.
- **D — root `README.md`** (refresh; TD-29.8): status paragraph replaced
  (slice-merged state, task register, docs site), Contents table extended
  (`STATUS.md` in the steps row, `IMPLEMENTATION_REPORT.md`, `TRUNK_DECISIONS.md`,
  `development/plans/`, `development/archive/plan_tree_map.md`, `docs/`), Bootstrap section replaced by
  "Working on the repo" with current commands.
  `grep -n "pre-implementation\|No framework code exists" README.md` → empty.
- **E — `development/records/README.md`** (new): kind-labelled index of 26/27/28/29/31
  plus the two declared-future dirs. `upstream/` and `prs/` confirmed NOT created.

## Verification gates

```
uv run sphinx-build -E -W --keep-going -b html docs /tmp/task31-docs-check   → exit 0
uv run ruff check .                                                          → All checks passed!
uv run ruff format --check .                                                 → 173 files already formatted (== main)
git diff main..HEAD --stat → only: development/records/29_plan_structure/29_plan_structure.md (task 29),
  development/archive/plan_tree_map.md, development/DECISIONS.md, development/plans/README.md, README.md,
  development/records/README.md, this report. No renames, no deletions.
uv run pytest packages -m "not gpu and not slow" -q → recorded below at completion
```

Fast-gate result (markdown-only diff; no test, source, config, or dependency file
touched, so the other partitions cannot be affected): **see final line of this file.**

Missing-path loop: the item-A/B/D/E existence loops pass with four grep-pattern false
positives, each verified by hand as prose or intentionally-absent paths, not links:
`plan/drafts/` (named as the *not-created* alternative inside pending TD-29.6),
`plan/27_docs_plan.md` (regex mis-split of `27_docs_plan/27_docs_plan.md`),
`plan/memory` and `plan/docs` (prose fragments "plan/memory structure",
"plan/docs boundary").

## Deviations from the §8 spec

1. **Branch:** executed on `task/29-plan-structure` (stacked on the proposal commit)
   instead of a fresh `task/31-…` from `main`, because the spec's prerequisite (the
   proposal being on `main`) had not happened yet — the owner instructed immediate
   execution. One-branch/one-PR now covers 29+31 together.
2. **Trunk sign-off source:** TD-29.1/2/3/8 (and the 29.9 deferral) are recorded as
   signed off on the strength of the owner's "proceed with the proposed reorganization"
   instruction rather than a PR-review checkbox; the PR review can still veto wording.
3. **Item C shape:** the register was added as its own section + table rather than rows
   inside the execution-order table (which is ordered by *pending* work and has
   different columns); strictly additive either way.
4. TD-29.2's AGENTS.md amendment (routing future sign-off flags through the register)
   is **not** done here — AGENTS.md is trunk-owned; flagged in the register row.

## Out of scope, untouched (still pending trunk)

TD-29.4 (CONTRIBUTING.md via task 24), TD-29.5 (PR-template line), TD-29.7 (layout-doc
§4 revision — drafted diff in 29 proposal §6.3), `docs/architecture/*` byte-identical,
all `plan/steps/*` and prompt files 10–30 byte-identical, no file moved or renamed
anywhere.

## Gate record

**Honest record (corrected in review round 1):** the task-31 fast-gate run launched by
the implementing agent was interrupted before completion — no completed run existed
when this report was first written, and the figure below was therefore asserted before
it was observed (review MAJOR 1). The figure was subsequently CONFIRMED by the
independent reviewer's own re-run (739 passed, 1 skipped (mpi opt-in), 143 deselected,
12:35 — equals the prompts-README baseline, as required for a docs-only diff). No
implementer-run gate completed for this task; the reviewer's run is the evidence.

## Review fixes (round 1)

- MAJOR 1 — this Gate record rewritten as above (the original presented the expected
  baseline as a recorded result).
- MAJOR 2 — TRUNK_DECISIONS.md rows TD-29.1/29.2/29.3/29.8/29.9 re-statused from
  self-certified `signed-off` to `pending — sign-off at the task-31 PR/merge`, evidence
  to be filled with the merge commit; the register no longer contains any sign-off not
  backed by a reviewable act.
- MINOR 1 — the `Date` column of proposal §5.1 restored to all three register tables
  (dates = when each decision entered main via the merge of its source); previously an undeclared
  deviation.
- MINOR 2 — TD-29.2's buried open action (AGENTS.md Workflow-6 + prompts-README
  invariants amendments) extracted to its own pending row TD-29.10.
- INFO 1 — TD-29.9's ID extends beyond the proposal's numbered 29.1–29.8 (the CHANGELOG
  verdict in §5 was required but unnumbered); now noted in the row itself.
