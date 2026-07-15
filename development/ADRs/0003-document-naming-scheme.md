# 046 — The `NNN_<slug>_<kind>` document naming scheme

**Status:** accepted; sequence/suffix clauses superseded-by-0006 (number-sharing and exemption clauses stand) · **Date:** 2026-07-14

## Context

After the `development/` reorganization (adr 043) the tree still carried four naming
series (S-series steps, P-series outlines, two-digit N-series tasks, four-digit kebab
ADRs), plus `DECISIONS.md` sitting next to a folder of decision records. The owner
asked for one convention; the evaluation is work unit 034
(`development/work/reports/report-0034-naming-iteration/34_naming_iteration.md` §3, decision
points 3 and 5 of §9, confirmed by the owner).

## Decision

Lifecycle documents in `development/` are named `NNN_<slug>_<kind>.md`, or
`NNN_<slug>_<kind>/` for multi-file deliverables (inner files keep their names —
frozen files are moved, never renamed-and-reworded):

- **One global sequence.** NNN = allocation order in the document register
  (`REGISTRY.md` §1), three digits, zero-padded, numbering consecutively across kinds.
- **One number per work unit, shared across its lifecycle files.** A feature's idea,
  spec, plan, and record all carry the same NNN with different kind suffixes;
  single-kind documents simply consume one number.
- **Kind suffix = singular of the folder name**: `idea`, `spec`, `plan`, `record`,
  `adr`.
- **Exemptions:** `policies/*` stay unnumbered snake_case (living, topical, looked up
  by subject, no meaningful order; numbering the most-cited filenames buys nothing and
  costs churn); also exempt: `README.md` files, `REGISTRY.md`, and `archive/` contents
  (documents arrive there under their dying names).
- **Remap, never renumber history.** Existing numbers are preserved where they exist;
  previously-unnumbered or scheme-colliding documents got fresh numbers at migration
  (work unit 035). The full old→new table is a permanent section of `REGISTRY.md`
  (§2) — the bridge for historical names and `development/references/lock.toml` step ids, which stay as
  written. Gaps (015–019) stay open forever, consistent with the never-backfill rule.
- **ADR citation form:** `adr NNN` (ADR-0001/0002/0003 → `adr 043`/`adr 044`/
  `adr 045`; historical `ADR-000N` wording in frozen records translates via the remap
  table).

## Consequences

- Register rows, branches (`work/NNN-<slug>`), and lifecycle files of one work unit
  line up by number; the kind is visible in the filename.
- Every rename of the existing corpus is mechanical path retargeting under the
  content-frozen rule (adr 044); frozen wording ("step S08", "task 26") stays and is
  translated by the remap table.
- The allocator moved with the rename `DECISIONS.md` → `REGISTRY.md` (TD-35.3): one
  file registers both document numbers and trunk decisions.

## Alternatives considered

- **Per-kind sequences** (specs and plans numbered independently): breaks the join
  that makes one work unit's files line up — rejected.
- **A fresh number per document**: would give one feature four unrelated numbers —
  rejected (034 §3.2).
- **Literal "always" numbering** (policies and READMEs too): migration cost is small
  but numbering buys nothing for subject-lookup files and churns the most-cited
  filenames — exemptions adopted instead (034 §3, decision point 3b).
