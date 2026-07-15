# 0006 — The `work/` tree and kind-prefixed document names

**Status:** accepted; kebab/snake split and folder-report shape superseded-by-0007 (all other clauses stand) · **Date:** 2026-07-15 (owner confirmation 2026-07-14; evaluation: work unit 049)

## Context

After the 035 naming migration the lifecycle folders (`ideas/`, `specs/`, `plans/`,
`records/`) still sat flat under `development/` next to the cross-cutting instruments,
ADR numbering was tied to the global document sequence (043–048), and the provenance
ledger `REFERENCES.lock` sat at the repo root away from `references/`. The owner
proposed a `work/` grouping with kind-prefixed names, an independent `ADRs/` sequence,
and the lock move; work unit 049 evaluated all three points
(`development/work/reports/report-0049-work-structure-iteration.md` §§1–4,
owner-confirmed 2026-07-14).

## Decision

- **Lifecycle folders group under `development/work/{proposals,specs,plans,reports}`**
  (ex-`ideas`, unchanged, unchanged, ex-`records`). Files are named
  `<kind>-<NNNN>-<kebab-slug>.md`, four digits, **numeric values preserved** from the
  existing ids (000→0000, 001–014→0001–0014, 020–036→0020–0036, 037–042→0037–0042,
  049→0049); slugs converted snake→kebab. Multi-file reports keep the folder form
  `report-NNNN-<kebab>/` (inner files unchanged). The lifecycle vocabulary becomes
  proposal → spec → plan → report.
- **One number per work unit, shared across its files** (restated from ADR-0003 — that
  clause stands), matching across the `work/` subfolders. The work-id sequence is
  independent of everything outside `work/`; gaps (0015–0019) stay open per the
  never-backfill rule.
- **`adr/` → `ADRs/`** — a deliberate exception for an initialism, recorded as the
  repo's *only* non-lowercase folder — with Nygard names `NNNN-<kebab-title>.md` and an
  **own sequence from 0000**: the existing six remap in order (043→0000, 044→0001,
  045→0002, 046→0003, 047→0004, 048→0005); this ADR is 0006. Citation form `ADR-NNNN`.
  This supersedes ADR-0003's global-sequence and kind-suffix clauses; its
  number-sharing clause and the `policies/*`/`README.md`/`REGISTRY.md`/`archive/*`
  exemptions stand.
- **`REFERENCES.lock` → `development/references/lock.toml`** (the file parses as valid
  TOML, 51 `[[ref]]` entries — verified in the 049 evaluation). Only the header title
  line changes; `[[ref]]` entries and their historical `step` ids stay as written and
  resolve via the `REGISTRY.md` remap tables.
- **`policies/records_and_liveness.md` → `policies/document_kinds.md`** (rename +
  vocabulary sweep). Policies stay snake_case and unnumbered; kebab is for `work/` and
  `ADRs/` only.
- **`REGISTRY.md`, `development/README.md`, folder READMEs, and reference cards stay in
  place**, contents updated. **`archive/` stays at the `development/` root** — it must
  accept dead documents of any kind, not only work documents.

## Consequences

- Historical name resolution is a two-hop bridge: `REGISTRY.md` §2 (old → 035 names)
  then §2b (035 names → `work/` names), e.g. `S08` → `008_graupel_component_spec.md` →
  `spec-0008-graupel-component.md`. Never renumber history.
- Frozen documents keep their wording; only path strings were retargeted (ADR-0001).
- Forward branch convention: `work/NNNN-<kebab>`.

## Alternatives considered

- **Compact renumber from 0000** (049 §2 reading a): every work unit gets its third id
  in three days and the remap chain re-keys to *different* numbers — rejected.
- **ADRs keeping 043+**: a fossil of the dead global sequence once every kind numbers
  independently — rejected (049 §1).
