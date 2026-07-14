# adr/ — architecture decision records

Nygard-format records (`NNNN-<kebab-title>.md`): Context · Decision · Consequences ·
Alternatives considered. Frozen once accepted; only the `Status:` field may change
afterwards (e.g. `superseded by NNNN`).

| # | Title | Status |
|---|---|---|
| 0001 | Reorganize the repo process memory into a top-level `development/` tree | accepted |
| 0002 | "Frozen" means content-frozen; sanctioned mechanical path retargeting | accepted |
| 0003 | The decision register and ADRs are two instruments, not merged | accepted |

**When to write an ADR vs only a register row** (rule of thumb from ADR-0003): if the
decision shapes structure — of the code, the repo, or the process — and someone will
later ask *why*, write an ADR and add a `development/DECISIONS.md` row whose Source
points at it. If the decision is a one-line operational fact (a tolerance grant, a
pin, a wording amendment), a register row alone is enough.
