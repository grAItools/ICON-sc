# 0003 — The decision register and ADRs are two instruments, not merged

**Status:** accepted · **Date:** 2026-07-14

## Context

The repo has a living trunk-decision/sign-off register (`development/DECISIONS.md`,
formerly `plan/TRUNK_DECISIONS.md`) whose rows track pending/signed-off human
decisions via the `TD-PENDING:` marker contract. The reorganization (ADR-0001)
introduces `adr/` for Nygard-style architecture decision records. The overlap
question: merge them, or keep both?

## Decision

Keep both; no merge (TD-33.3). `DECISIONS.md` is the **sign-off ledger**: one row
per decision (ID, date, decision text, status, source, evidence), statuses flipped
in place, and the grep contract that every `TD-PENDING:` line in any record has an
open row. `adr/` holds the **reasoning** for architecture-shaped decisions:
context, decision, consequences, alternatives — frozen once accepted (only the
`Status:` field may later change, e.g. to superseded). An architecture-shaped
decision gets **both**: an ADR for the reasoning and a register row for the
sign-off, with the row's Source column pointing at the ADR.

## Consequences

- The register stays the single greppable place answering "what is pending and who
  signed off"; ADRs stay the readable place answering "why is it this way".
- Small operational decisions (tolerances, pins, wording amendments) get only a
  register row; writing an ADR for them is noise.
- ADR numbering (`NNNN-<kebab-title>.md`) is independent of the S/N series.

## Alternatives considered

- **Register only:** rows are one line each; the reasoning for structural decisions
  does not fit and ends up scattered across task reports.
- **ADRs only:** loses the ledger semantics — statuses, `TD-PENDING:` grep
  contract, and per-row evidence of the merge that decided it.
