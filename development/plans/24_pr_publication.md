# Task 24 — Prepare the one-PR-per-step publication (drafting; a human pushes)

**Branch:** `task/24-pr-publication` (from `main`) for the drafted files. **You do
NOT push, do NOT open PRs, do NOT create remotes** — you produce the PR bodies and
an exact push/PR command script for the human to review and execute.

## Context

All 14 step branches (`step/S01-repo-scaffold` … `step/S14-plan-through-dycore`)
exist locally, each already merged into local `main` in DAG order (merge ledger:
`development/records/IMPLEMENTATION_REPORT.md` §2). AGENTS.md requires one PR per step. Seven
steps carry HUMAN SIGN-OFF items (report §5) that must be visible in their PR
bodies. `origin/main` is at the pre-slice commit; the PR template, if any, lives in
`.github/` (check for `PULL_REQUEST_TEMPLATE`; if present, its structure is
mandatory for the bodies you draft).

## Procedure

1. Read `development/records/IMPLEMENTATION_REPORT.md` fully (§2 merge ledger, §5 sign-off ledger)
   and `AGENTS.md` (workflow item 6: STATUS contents; PR-per-step).
2. For each step S01–S14, draft `development/records/prs/SXX_pr_body.md`:
   - Title: `SXX: <one-line what>` (take it from the merge commit subject).
   - Sections: **What** (from the step STATUS "What was built", compressed to
     ≤10 bullets); **Verification** (the step's gate numbers from its STATUS,
     verbatim — do not re-derive); **Deviations needing acknowledgment** (from
     STATUS deviations; for the seven sign-off steps, a prominent
     `## ⚠ HUMAN SIGN-OFF REQUIRED` section quoting the exact flagged item);
     **Review history** (rounds and what the review caught — one line per round,
     from the report §2 table + STATUS "Review fixes" sections);
     **References** (the REFERENCES.lock entry ids the step added).
   - End the body with the standard footer:
     `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
3. Draft `development/records/prs/publish.sh` — NOT executable by you; a
   plain-text script the human runs. It must: push each `step/SXX-*` branch; open
   each PR **based on the previous step's branch** (S01 against the default
   branch; SXX against `step/S(XX-1)-...`) so each PR shows only its own diff —
   EXCEPT document the alternative (all against main, largest-diff-last) as a
   commented option; use `gh pr create --base ... --head ... --title ... --body-file ...`.
   Order: S01→S14. Include `set -euo pipefail` and an echo before each action.
4. Cross-check each drafted body against its STATUS: every sign-off item from
   report §5 MUST appear in the corresponding body. Build a checklist table in
   `development/records/prs/INDEX.md` (step | branch | base | sign-off items |
   body file) for the human.

## What NOT to do

- No `git push`, no `gh pr create`, no `gh auth` — drafting only.
- Do not summarize away tolerance-related sign-off items; quote them exactly.
- Do not reorder or rebase any branch. Do not "fix up" branch history.

## Acceptance criteria

1. 14 body files + `publish.sh` + `INDEX.md` committed under
   `development/records/prs/`.
2. Every §5 sign-off item appears verbatim-quoted in exactly the right body.
3. `publish.sh` is internally consistent (each `--head` branch exists — verify with
   `git branch --list 'step/*'`; each `--body-file` path exists).
4. Nothing outside `development/records/prs/` touched; fast gate baseline
   unchanged (run it once as a formality).

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Pick 3 steps at random (MUST include one of S08/S12/S13 — the tolerance-heavy
  ones) and diff their PR body claims against the actual STATUS files; any number
  or sign-off item that differs is a MAJOR finding.
- Verify `publish.sh` branch names against `git branch --list 'step/*'` output and
  body-file paths against `ls`; dry-parse it with `bash -n`.
- Confirm all 7 sign-off steps (S05, S08, S09, S10, S12, S13, S14 — per report §5)
  have the ⚠ section and the other 7 do not have a spurious one.
