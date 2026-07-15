# ADRs/ — architecture decision records

Nygard-format records, `NNNN-<kebab-title>.md`, **own sequence from 0000** (independent
of the work ids in `development/REGISTRY.md` §1; next free: **0007**): Context ·
Decision · Consequences · Alternatives considered. Frozen once accepted; only the
`Status:` field may change afterwards (e.g. `superseded-by-NNNN`). Cite ADRs as
`ADR-NNNN`. The former `NNN_<slug>_adr.md` files 043–048 were remapped **in order** to
0000–0005 by work unit 0050 (ADR-0006; remap table: `development/REGISTRY.md` §2b);
historical `adr NNN` citations in frozen documents translate the same way, and the
pre-035 `ADR-000N` citations translate via §2 then §2b. Headings inside the six moved
files keep their historical numbers (frozen content); this index is the living map.

| # | Title | Status |
|---|---|---|
| 0000 | Reorganize the repo process memory into a top-level `development/` tree | accepted |
| 0001 | "Frozen" means content-frozen; sanctioned mechanical path retargeting | accepted |
| 0002 | The decision register and ADRs are two instruments, not merged | accepted |
| 0003 | The `NNN_<slug>_<kind>` document naming scheme | accepted; sequence/suffix clauses superseded-by-0006 (number-sharing and exemption clauses stand) |
| 0004 | Documentation stack: Sphinx + MyST + Napoleon + furo (retroactive) | accepted |
| 0005 | icon-grid-generator as archive-independent fixture source (retroactive) | accepted |
| 0006 | The `work/` tree and kind-prefixed document names | accepted |

**When to write an ADR vs only a register row** (rule of thumb from ADR-0002): if the
decision shapes structure — of the code, the repo, or the process — and someone will
later ask *why*, write an ADR and add a `development/REGISTRY.md` row whose Source
points at it. If the decision is a one-line operational fact (a tolerance grant, a
pin, a wording amendment), a register row alone is enough.
