# icon_grid_generator

**Source:** https://github.com/ofuhrer/icon-grid-generator (Oliver Fuhrer/MeteoSwiss)
**Pinned:** v0.3.2 (`2e8aa97a9833203ee2bda0ec2fbe235ed3ff2e80`, PyPI-published);
`icon-grid-generator==0.3.2` in `constraints/cpu-ci.txt` (task 26).
**License:** BSD-3

## Role in the project

Pure-numpy ICON-style grid generator for synthetic-grid tests, convergence ladders,
torus experiments, and LAM/P2 fixtures (task 26). Generated grids load through the
symcon grid stack (GridManager path) with offset providers, metrics, and
interpolation factory fields computing all-finite.

## Gotchas

- **NOT numerically equivalent to official DWD gridgen output** (own spring
  iterations; upstream verification is invariant-based) — unusable for
  savepoint-parity work; `constraints/cpu-ci.txt` carries the same warning.

## Consultation ledger

`grep -n 'id = "icon-grid-generator' development/references/lock.toml` — one `[[ref]]` entry per
consultation.
