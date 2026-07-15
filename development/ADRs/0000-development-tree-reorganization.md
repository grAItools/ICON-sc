# 0001 — Reorganize the repo process memory into a top-level `development/` tree

**Status:** accepted · **Date:** 2026-07-14

## Context

The S01–S14 slice and the post-slice tasks accumulated their process memory under
`plan/` (steps, prompts, outlines, reports, registers) with `docs/` carrying the
published Sphinx site. Task 29 ratified a zero-move structure (TD-29.1); task 32
re-evaluated a full reorganization proposed by the owner and, as amended by owner
iteration, the decision is a kind-sorted tree. Two constraints shaped it: `docs/`
must stay a pure Sphinx site source, and the repo's frozen records must stay
auditable (history via git, not via frozen-in-place paths).

## Decision

All development memory moves to a top-level `development/` tree — not under `docs/`;
no `docs/user/` nesting; no `conf.py` `exclude_patterns` change. Kind-folders:
`policies/` (living rules), `adr/` (architecture decision records), `ideas/`
(future proposals, including the migrated phase outlines P2–P7), `specs/` and
`plans/` (S01–S14 + future, one ID per work unit), `records/` (STATUS files, task
reports, `IMPLEMENTATION_REPORT.md`, frozen at merge), `archive/` (no-longer-relevant
documents), `references/` (per-source cards + gitignored `local/`). The migration is
full: every document moves to its kind-folder by `git mv` (history preserved,
`git log --follow`); `plan/` is deleted; documents with no ongoing relevance go to
`development/archive/`. `drafts/` is dropped — external-facing texts are their task's
records. `plan/TRUNK_DECISIONS.md` is renamed `development/DECISIONS.md` and lives at
the `development/` root as the only living file at that level (renaming it
`STATUS.md` was rejected: it would collide with the fourteen per-step `STATUS.md`
records).

## Consequences

- `docs/` is untouched except two one-line path edits (`index.md` prose, `conf.py`
  comment); the site never links into `development/` (see `policies/docs-boundary.md`).
- ~90 inbound path references (living docs, test code, tooling globs) are retargeted;
  frozen records receive mechanical path retargeting only (ADR-0002).
- Future IDs continue the S-series/N-series; spec, plan, and record of one work unit
  share one ID; the task-number register survives as `development/plans/README.md`
  with its allocation rules unchanged.

## Alternatives considered

- **Zero-move** (TD-29.1, task 29): superseded — kept paths stable but left the
  kind-taxonomy implicit in one folder's conventions.
- **Freeze-in-place archive** (task-32 recommendation: `plan/` becomes a read-only
  archive with a banner): overridden by the owner — history lives in git, not in
  frozen paths; a split tree ("new here, old there") makes every future reader pay
  for the migration that was avoided.
- **`docs/development/` nesting** (owner's first proposal): rejected in iteration —
  requires Sphinx exclusions and blurs the published/internal boundary.
