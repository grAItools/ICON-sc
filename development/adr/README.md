# adr/ — architecture decision records

Nygard-format records (`NNN_<slug>_adr.md`, numbers from the global sequence in
`development/REGISTRY.md` §1): Context · Decision · Consequences · Alternatives
considered. Frozen once accepted; only the `Status:` field may change afterwards
(e.g. `superseded by adr NNN`). Cite ADRs as `adr NNN`. The former
`NNNN-<kebab-title>` files 0001–0003 were renumbered 043–045 in work unit 035
(remap table: `development/REGISTRY.md` §2); historical `ADR-000N` citations in
frozen records translate the same way.

| # | Title | Status |
|---|---|---|
| 043 | Reorganize the repo process memory into a top-level `development/` tree | accepted |
| 044 | "Frozen" means content-frozen; sanctioned mechanical path retargeting | accepted |
| 045 | The decision register and ADRs are two instruments, not merged | accepted |
| 046 | The `NNN_<slug>_<kind>` document naming scheme | accepted |
| 047 | Documentation stack: Sphinx + MyST + Napoleon + furo (retroactive) | accepted |
| 048 | icon-grid-generator as archive-independent fixture source (retroactive) | accepted |

**When to write an ADR vs only a register row** (rule of thumb from adr 045): if the
decision shapes structure — of the code, the repo, or the process — and someone will
later ask *why*, write an ADR and add a `development/REGISTRY.md` row whose Source
points at it. If the decision is a one-line operational fact (a tolerance grant, a
pin, a wording amendment), a register row alone is enough.
