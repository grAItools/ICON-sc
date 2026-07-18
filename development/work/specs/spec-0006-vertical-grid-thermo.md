# S06 — ICON vertical grid, thermodynamics, registry seed (lane A start)

**Lane:** A · **Depends on:** S02, S03 · **Unblocks:** S07, S08 · **Parallel with:** S04/S05, lane B

## Goal
Everything a physics column needs and nothing more: the ICON vertical grid, the exner/θv/T/p thermodynamic relations exactly as ICON defines them, the first ~40 entries of the variable registry, and column-state construction helpers.

## In scope
`icon_sc/icon/grid/vertical.py` (`VerticalGrid`: vct_a/vct_b ingestion or SLEVE computation; nlev, interface/full levels; reference-state helpers) · `icon_sc/icon/names.py` (registry seed: prognostics ρ, vn(placeholder), w, exner, θv; tracers qv qc qi qr qs qg; diagnostics T, p, p_ifc, u, v; tendency-bus slot names `icon:ddt_*` for temperature/qx; all with canonical units + ICON short names + CF names where they exist) · `icon_sc/icon/thermo.py` (exner↔p, θv↔T with moisture, ICON constants rd/cpd/cvd/p0ref etc. from a single `_constants.py` sourced from ICON `mo_physical_constants`) · `icon_sc/icon/testing.py` (column-state builders: `isothermal_column`, `moist_test_column(profile_id)`; icon4py-datatest fixture bridge).

## Frozen interfaces
`VerticalGrid(vct_a, vct_b, nlev)`; `thermo.exner_from_pressure`, `pressure_from_exner`, `virtual_potential_temperature`, `temperature_from_thetav_exner` (array-namespace generic: numpy/cupy in, same out); `icon_names.QUANTITIES` table; column builders returning valid ICON-sc states.

## Acceptance criteria
1. Thermo round-trips: p→exner→p and (T,qv)→θv→T identity to 1e-12 fp64 across a realistic (p, T, qv) grid.
2. Constants byte-compare against values extracted from pinned ICON Fortran `mo_physical_constants.f90` (agent extracts and commits the comparison table into the test).
3. Where the pinned icon4py exposes equivalent thermo helpers, cross-check ICON-sc results to 1e-12 (skip with recorded justification if not exposed).
4. `VerticalGrid` reproduces the vertical coordinate table of one icon4py datatest grid savepoint to 1e-12 (marker `data`).
5. Registry: every seeded quantity passes S02 registration validation; `icon:` names collide with nothing; a docs table is generated from the registry (name ↔ ICON ↔ CF ↔ units) and committed.
