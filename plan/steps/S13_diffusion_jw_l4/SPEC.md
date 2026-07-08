# S13 — Horizontal diffusion + Jablonowski–Williamson (L4)

**Lane:** B · **Depends on:** S12 · **Unblocks:** S14

## Goal
`HorizontalDiffusion(Stepper)` (icon4py diffusion granule) and the JW baroclinic-wave initializer; the composed dry model (dycore + diffusion) reproduces the JW evolution against an icon4py-driver reference run — ladder L4 for the slice.

## In scope
`symcon/icon/components/diffusion.py` (savepoint-verified like S12) · `symcon/icon/ingest/idealized.py` (`jablonowski_williamson(grid, vgrid, cfg)` initial state; reference: ICON `mo_nh_testcases`/DCMIP formulas and icon4py's driver initializer — delegate to the latter if importable) · `examples/02_jw_baroclinic.py` (dycore + diffusion loop, NetCDF output, no physics; bus slots zero) · `validation/L4_idealized/test_jw.py`.

## Acceptance criteria
1. Diffusion savepoint parity at icon4py tolerances (marker `data`).
2. JW initial state matches icon4py's initializer output to 1e-12 where delegation is possible; else matches the published analytic formulas on sampled points to 1e-10.
3. **L4:** 9-day run at the datatest grid's resolution vs a reference trajectory produced by the pinned icon4py driver on the same grid/config (agent generates + caches the reference via pooch): surface-pressure field rtol ≤ 1e-6 at day 1 and within a documented growth envelope at day 9 (chaotic divergence acknowledged: compare against the reference with the L∞/L2 tolerance schedule icon4py's own driver tests use; adopt theirs verbatim and cite).
4. Symmetry check: with the JW perturbation disabled, zonal symmetry of surface pressure preserved to 1e-10 over 12 h (classic dycore smoke).
5. `examples/02` CI smoke at reduced length (6 h).
