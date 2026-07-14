# 0002 — "Frozen" means content-frozen; sanctioned mechanical path retargeting

**Status:** accepted · **Date:** 2026-07-14

## Context

SPECs, PLANs, STATUS files, executed prompts and reports are frozen records: never
retro-edited, so their claims stay auditable. A full-migration reorganization
(ADR-0001) moves every one of them, which breaks every path string they contain.
Leaving the strings stale makes every frozen pointer a dead end; editing freely
destroys the record guarantee.

## Decision

"Frozen" is amended to **content-frozen** (owner-confirmed, TD-33.2): mechanical
path retargeting, confined to link/path strings, is permitted in a **sanctioned
migration commit**. Such commits are isolated — moves in one commit, retargets in
another — so `git diff --word-diff` on the retarget commit shows path strings only
and "content unchanged" is verifiable by diff. Header-line **additions** above a
frozen document's original text (never edits within it) may be sanctioned
case-by-case by the migration plan that owns the commit (task 33 sanctioned two:
the `Status:` header above each migrated outline, and the supersede note above
`archive/plan_tree_map.md`).

## Consequences

- Frozen records keep working as pointers after any future move; reviewers verify
  frozenness by word-diffing the sanctioned commit rather than trusting prose.
- Wording, formatting, or content changes in a frozen document remain violations,
  including inside a sanctioned commit.
- Path strings whose meaning is the old tree itself (a move map's "from" column, a
  verification claim that files did not move) are left as written and listed in the
  migration report — retargeting them would falsify the record.

## Alternatives considered

- **Strict freeze (no edits ever):** leaves dead pointers throughout the corpus
  after any move; readers must reconstruct the mapping by hand.
- **Free editing of records:** destroys auditability; rejected outright by the
  standing working agreement.
