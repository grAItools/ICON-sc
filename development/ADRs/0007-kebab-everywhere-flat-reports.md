# 0007 — Kebab-case everywhere; flat reports with sibling artifact folders

**Status:** accepted · **Date:** 2026-07-15 (owner mandate 2026-07-15, direct
instruction — no evaluation round)

## Context

ADR-0006 kept a deliberate case split: kebab-case for the numbered documents in
`work/` and `ADRs/`, snake_case for `policies/*` (and, by exemption, the reference
cards and archive contents kept their snake names). Reports could be folders
(`report-NNNN-<kebab>/` with inner `STATUS.md`, `REPORT.md`, or a named design
document), so the same kind had two shapes and inner filenames carried no work id.
The owner mandated one rule for both.

## Decision

- **Kebab-case for ALL filenames under `development/`** — including `policies/`,
  `references/` cards, and `archive/` contents — never snake or mixed. Exceptions:
  `README.md` everywhere (conventional, not snake) and `lock.toml` (a fixed name).
- **Reports are files**: `report-<NNNN>-<kebab>.md`, always. The former folder-form
  reports (14 `STATUS.md` folders, the named design documents, the two `REPORT.md`
  execution reports) are flattened to that shape, content byte-identical.
- **Artifacts live in a sibling folder** `report-<NNNN>-<kebab>/` next to the report
  file — named exactly like the report file minus `.md`, and existing ONLY when the
  report has extra artifacts (tracked sidecars or untracked generated files). A
  report folder holding only untracked artifacts gets its own explicit `.gitignore`
  line; folders holding tracked sidecars are not ignored.
- This **supersedes ADR-0006's kebab/snake-split clause and its folder-report
  shape**; all other ADR-0006 clauses (the `work/` tree, id allocation, `ADRs/`
  independence, the lock move) stand. Historical names resolve via the
  `development/REGISTRY.md` remap tables (§2c for this migration).

## Consequences

- Every filename under `development/` is predictable from one rule; the report kind
  has one shape and its id is always in the filename.
- Frozen documents keep their wording; only path strings were retargeted (ADR-0001).
- The blanket `development/work/reports/*/artifacts/` gitignore glob dies with the
  `artifacts/` subfolder convention; ignoring is per-folder and explicit.

## Alternatives considered

- **Status quo** (mixed kebab/snake, folder-form reports) — rejected by owner
  mandate.
- **Folder-per-report** (uniform `report-NNNN-<kebab>/` for every report) — rejected
  by owner mandate: most reports are single files; the folder adds a level and hides
  the document behind an unnumbered inner name.
