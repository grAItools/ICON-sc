# 048 — icon-grid-generator as archive-independent fixture source (retroactive)

**Status:** accepted · **Date:** 2026-07-14 (decision 2026-07-13, work unit 026;
recorded retroactively by work unit 035)

## Context

Grid-dependent tests needed ICON grid files; sourcing every fixture from the official
archives couples the test tier to external data logistics. Work unit 026 evaluated and
adopted the icon-grid-generator package (v0.3.2 PyPI, repo SHA `2e8aa97a…`,
BSD-3-Clause, Oliver Fuhrer/MeteoSwiss); the evidence and boundary are recorded in
`development/work/reports/report-0026-gridgen-integration.md`.

## Decision

- **Generated grids are archive-independent test fixtures** — reader/factory smoke
  tests, future convergence ladders (L7/P7), torus experiments, P2 partitioning
  fixtures.
- **Not-for-parity boundary:** generated grids are ICON-convention but **not**
  numerically equivalent to official DWD gridgen output (own spring optimization;
  upstream verifies invariants, not DWD equivalence). They are excluded from all
  savepoint-parity work. The boundary is stated in the extra's pyproject comment, the
  helper docstrings, and the test-module docstring.
- **Quarantine in `symcon.icon.testing`:** `generated_grid_file(spec, cache_dir=None)`
  and `generated_grid(spec, ctx=None, num_levels=35, cache_dir=None)` are the single
  quarantine point for the dependency; the package is an optional extra
  (`symcon-icon[gridgen]`, lower bound `>=0.3.2`; exact pin in
  `constraints/cpu-ci.txt`). Missing package → loud `ModuleNotFoundError` naming the
  extra; tests `importorskip`.
- **Version-keyed cache:** `~/.cache/symcon/generated-grids/igg-<version>-<spec>.nc`,
  write-then-rename — safe because generation is fully deterministic (verified: uuid5
  AND bitwise topology/coordinates across independent generations).
- **Version bumps are trunk decisions** (alpha-status upstream; the version-keyed
  cache makes bumps safe against stale files).

## Consequences

- The not-for-parity boundary constrains every future validation/convergence work
  unit: parity work keeps using official/serialized references; generated grids serve
  everything else (P7's ladder cites the boundary).
- When the L7 convergence ladder is cut, `generated_grid_file` specs R2B2→R2B5 replace
  sourcing four official files.
- Upstream contribution candidate stays open: an icon4py-GridManager round-trip test
  for their suite (they verify invariants only).

## Alternatives considered

- **Official-archive fixtures only:** keeps every grid-dependent test coupled to
  external data logistics; rejected by adoption.
- **Using generated grids for savepoint parity too:** rejected outright — the grids
  are not numerically equivalent to the official output; hence the explicit boundary.
