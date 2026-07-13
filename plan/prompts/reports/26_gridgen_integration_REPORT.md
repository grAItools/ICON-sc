# Task 26 report — icon-grid-generator adoption

**Branch:** `task/26-gridgen-integration` · **Date:** 2026-07-13
**Upstream:** icon-grid-generator v0.3.2 (PyPI), repo SHA `2e8aa97a…`
(BSD-3-Clause, Oliver Fuhrer/MeteoSwiss). REFERENCES.lock entry
`icon-grid-generator` (appended at evaluation time, commit `2dddc29`).

## What was adopted, and the boundary

Generated grids serve as **archive-independent test fixtures**: reader/factory
smoke tests, future convergence ladders (L7/P7), torus experiments, and P2
partitioning fixtures. They are **excluded from all savepoint-parity work** —
generated grids are ICON-convention but not numerically equivalent to official
DWD gridgen output (own spring optimization; upstream verifies invariants, not
DWD equivalence). This boundary is stated in the extra's pyproject comment, the
helper docstrings, and the test-module docstring.

## Changes

1. `constraints/cpu-ci.txt`: `icon-grid-generator==0.3.2` — an addition to the
   pinned set (S10 jax precedent), not a bump of anything existing. uv.lock diff
   is that single package.
2. `packages/symcon-icon/pyproject.toml`: new optional extra
   `gridgen = ["icon-grid-generator>=0.3.2"]` (lower bound; test-tier only).
   Root dev group installs `symcon-icon[gridgen]`.
3. `symcon.icon.testing.generated_grid_file(spec, cache_dir=None)` and
   `generated_grid(spec, ctx=None, num_levels=35, cache_dir=None)` — the single
   quarantine point for the dependency (S07 gt4py-ingress precedent). Cache:
   `~/.cache/symcon/generated-grids/igg-<version>-<spec>.nc`, write-then-rename;
   safe because generation is fully deterministic (verified: uuid5 AND bitwise
   topology/coordinates across independent generations). Missing package →
   loud `ModuleNotFoundError` naming the extra; tests `importorskip`.
4. `packages/symcon-icon/tests/test_generated_grid.py` — the compatibility
   contract (5 tests): reader round-trip incl. the S11 0-based/-1 normalization
   and uuid presence; bitwise generation determinism; IconGrid offset providers
   (C2E/C2V/E2C/C2E2C/E2C2E/Koff) + global refin_ctrl semantics; metrics(38) +
   interpolation(16) all-finite on gtfn_cpu (slow-marked — first run per grid
   size compiles gtfn variants) with a gpu-marked gtfn_gpu leg (skips cleanly
   without a device; unvalidated on hardware like all gpu legs — task 20).

## Evidence base (pre-adoption probes; the tests reproduce all of it — after the
## review round-1 fix, including coordinate determinism)

- Generated R2B2 (1280 cells / 1920 edges / 642 vertices) loads through
  `read_grid_file` and `from_file` (icon4py GridManager path).
- All 38 metrics + 16 interpolation factory fields all-finite on gtfn_cpu
  (embedded fails inside icon4py's factories — upstream `embedded_remap_error`,
  identical on official grids; documented in the helper docstring).
- Determinism: two independent generations bitwise-equal (uuid, connectivity
  tables, vertex coordinates).

## Gate results

- New file: 4 passed (3 fast + 1 slow gtfn_cpu), 1 gpu-deselected; fast legs
  <1 s each (generation ~seconds, then cached).
- `ruff check` / `ruff format --check` clean (172 files);
  `mypy --strict -p symcon.core` clean (50 files); `lint-imports` 2 kept.
- Full fast gate on the branch: **739 passed, 1 skipped (mpi)** — the new baseline
  (736 + 3 fast tests). Observed 17:24 wall on a loaded host; the S14-era spread on
  this machine is 14:08 (idle, warm) to 18:30 (cold cache) — the 3 new tests
  contribute <1 s. `slow and not gpu and not data` baseline becomes 30 → 31 (the
  gtfn_cpu factory test).

## Follow-ups

- Upstream contribution candidate: an icon4py-GridManager round-trip test for
  their suite (they verify invariants only; our probes are the integration
  evidence their CI lacks).
- When P7 cuts the L7 convergence-ladder step, `generated_grid_file` specs
  R2B2→R2B5 replace sourcing four official files; the SPEC should cite the
  not-for-parity boundary from this report.
- Version bumps of icon-grid-generator are trunk decisions (alpha-status
  upstream; the version-keyed cache makes bumps safe against stale files).
