# validation/L4_idealized — JW baroclinic wave (architecture §9, L4; S13)

The composed dry model (S12 `NonhydroSolver` + S13 `HorizontalDiffusion`, the
`icon_sc.icon.presets.build_jw` preset) against a reference trajectory produced by the
**pinned icon4py driver** (`icon4py.model.driver.icon4py_driver.TimeLoop` at v0.2.0)
on the same grid/config (the `exclaim_nh35_tri_jws` datatest experiment: global
R02B04, 35 levels, Δt = 300 s, 5 dynamics substeps, archive-namelist provenance).

## Workflow

1. `uv run python validation/L4_idealized/make_reference.py` — generates and caches
   the 9-day reference trajectory **plus its ε-perturbed twin** (initial `vn`
   shifted by 1e-13 m/s — the probtest idea at minimum viable scale, PLAN S13
   item 4) under `~/.cache/icon-sc/l4_reference/` (override:
   `SYMCON_L4_CACHE`). Checkpoints every 6 h: surface-pressure field, vn L2/L∞,
   850 hPa vertex-vorticity field. sha256 checksums + full config provenance land in
   `manifest.json`. **Never run in CI** (hours of compute; AGENTS.md) — the test
   skips with instructions when the cache is absent.
2. `uv run pytest validation/L4_idealized/test_jw.py -m "data and slow"` — runs the
   9-day ICON-sc trajectory (also hours) and compares:
   - config congruence: preset provenance == reference provenance (PLAN pitfall);
   - day 1: surface pressure `rtol ≤ 1e-6` (SPEC acceptance 3);
   - day 9 (and all checkpoints): within the documented growth envelope derived
     from the twin pair (no upstream tolerance schedule exists beyond one timestep
     at this grid — REFERENCES.lock `icon4py-driver-jw-tests`);
   - zonal-symmetry smoke (SPEC acceptance 4): perturbation off, 12 h, surface
     pressure constant within latitude rings to 1e-10 relative.

Artifacts (plots/norms) land in `validation/L4_idealized/artifacts/` (gitignored).
No data in git: the reference lives in the local cache, keyed by checksum.
