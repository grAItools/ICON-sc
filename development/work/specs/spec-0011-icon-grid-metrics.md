# S11 — ICON horizontal grid, geometry, metrics/interpolation factories (lane B start)

**Lane:** B · **Depends on:** S02, S03 · **Unblocks:** S12 · **Parallel with:** S04–S10

## Goal
The §3 grid layer on real ICON grid files: `IconGrid` (connectivities in raw + offset-provider form, geometry, refin_ctrl retained), and `MetricsFactory`/`InterpolationFactory` producing the static-state fields the dycore needs — verified against icon4py's serialized metrics/interpolation savepoints.

## In scope
`icon_sc/icon/grid/{reader,grid,geometry,metrics,interpolation}.py`. `reader` ingests ICON grid NetCDF (uuidOfHGrid, cell/edge/vertex counts, C2E/E2V/V2E/C2E2C/E2C2V/…, primal/dual geometry, refin_ctrl). `IconGrid` exposes connectivity both as index arrays and as the gt4py offset-provider mapping consumed by `ingress.gt4py`. Factories wrap/delegate to pinned icon4py `common` metrics & interpolation field computations wherever they exist; outputs land as read-only static-state DataArrays with registry names. Grid selection for the slice: the global grid used by icon4py's JW/driver datatest (discover; likely a small R02B04-class global grid) plus one regional test grid for reader coverage.

## Frozen interfaces
`icon_grid.from_file(path, ctx) -> IconGrid`; `grid.offset_providers`; `grid.geometry.<named fields>`; `metrics(grid, vgrid) -> Mapping[str, DataArray]`; `interpolation(grid) -> Mapping[str, DataArray]`; all static fields registered in `names.py` (extend the S06 seed).

## Acceptance criteria
1. Reader round-trip: counts, dims, and dtypes correct on both grids; uuid preserved; malformed-file errors are actionable.
2. Connectivity cross-check vs icon4py's grid object for the same file: identical index arrays (accounting for their 0/1-based normalization).
3. **Metrics/interpolation parity:** every produced static field matches the corresponding icon4py serialized savepoint to icon4py's own test tolerances (marker `data`; list of fields = what S12/S13 consume, enumerated in the test).
4. Offset providers accepted by a trivial gt4py neighbor-sum program on both backends.
5. `refin_ctrl` present on the regional grid; absent-but-defaulted on the global one.
