# S08 — STATUS

## What was built

- **`symcon/icon/components/fast/microphysics.py`**: `Microphysics(Stepper, Factory)` +
  `Graupel(Microphysics)` wrapping the icon4py single-moment six-class graupel granule
  (microphysics package, pinned v0.2.0; REFERENCES.lock `icon4py-graupel`), the gt4py
  port of ICON's `gscp_graupel.f90` (real path discovered:
  `src/granules/microphysics_1mom_schemes/`, REFERENCES.lock `icon-fortran-graupel`).
  - **Scheme selection by registry name** (SPEC in-scope): `Microphysics` is an S02
    `Factory` registry root; concrete schemes subclass it and register under their
    `name` class attribute. `Microphysics(grid, cfg, ctx, scheme="graupel")` (the
    architecture-§4.3 usage), `Microphysics.factory("graupel", ...)` and direct
    `Graupel(...)` construction are all equivalent; unknown names raise `KeyError`
    listing the known names. `"graupel"` is the only registered scheme.
  - Frozen-ctor shape mirrors S07: `(grid_or_column, cfg, ctx)` with the S06
    `VerticalGrid` **column path** (trivial pointwise icon4py host grid built lazily
    per horizontal extent) or the `(icon4py_grid, icon4py_vertical_grid)` **host-grid
    path** (the L2 datatest, running exactly as icon4py's own integration test).
  - `array_call` = zero-copy gt4py views of the boundary buffers → `granule.run(...)`
    *as icon4py's test invokes it* → `x_new = x + (dx/dt)·Δt` into the caller's output
    buffers (icon4py's own verification arithmetic). The sedimentation/level-loop
    structure (one forward K-scan carrying `rhoq{r,s,g,i}v_old_kup`/`vnew_*`, plus the
    two flux programs) is the granule's own — untouched (SPEC in-scope clause).
    Private tendency and precipitation-flux fields are zeroed per call (exact zero
    tendency above `kstart_moist`; no stale fluxes on repeat calls). dz is copied per
    call into a granule-owned metric field (T0 buffers are not pointer-stable, so
    aliasing once at bind would be unsound).
  - Contracts: in `air_temperature`/`air_pressure`/`air_density`/six tracers/
    `icon:qnc`/`icon:ddqz_z_full`; out T + six tracers with `differentiable: "native"`
    declared (JAX core lands in S10); diagnostics = the four grid-scale surface
    precipitation rates `icon:{rain,snow,ice,graupel}_gsp_rate` (ground-level values
    of the granule's flux fields — what icon4py's test compares to the exit
    savepoints). "dz from VerticalGrid via static-state input" (SPEC): the S06 column
    builders already put `icon:ddqz_z_full` in the state; the datatest takes it from
    the metrics savepoint. `coupling_constraints.admissible_operators =
    {"sequential_update_splitting"}` (tutorial §3.7.2 fast-physics chain).
  - `GraupelConfig`: field-for-field transcription of icon4py's
    `SingleMomentSixClassIconGraupelConfig` (defaults = ICON namelist defaults);
    `from_icon4py`/`to_icon4py` round-trip so the datatest consumes
    `experiment.config.graupel` — the exact namelist configuration the serialized
    data was produced with (PLAN pitfall; verified against the WK archive's
    `NAMELIST_ICON_output_atm.json`: every graupel-relevant value equals the
    icon4py default, incl. `ithermo_water=0` → constant latent heats).
- **`symcon/icon/components/fast/graupel_constants.py`**: the per-scheme
  shared-constants module (§8.6 single source of numerical truth; S10's functional
  core extends it): `GRAUPEL_QMIN = 1e-15` (== icon4py `MicrophysicsConstants.QMIN`
  == ICON `zqmin`, asserted by test) and `CLOUD_NUM = 200e6 /m3` (ICON
  `gscp_data.f90` default fed to the granule as `qnc` when `icpl_aero_gscp=0`;
  icon4py has no counterpart constant — used by the symcon test columns).
- **`symcon/icon/components/fast/_column_grid.py`**: the trivial pointwise icon4py
  host grid, hoisted out of `satad.py` now that the second consumer landed (the S07
  STATUS follow-up); satad imports it, behavior identical.
- **Registry rows** (`symcon.icon.names`, additive; docs table regenerated):
  `icon:qnc` (m-3, ICON `qnc`/`cloud_num`) and `icon:{rain,snow,ice,graupel}_gsp_rate`
  (kg m-2 s-1, ICON `prm_nwp_diag` naming, `mo_nwp_phy_types.f90:277-280`).
- **gt4py persistent build cache** (`symcon.core.testing.plugin.pytest_configure`):
  gt4py's compiled-program cache defaults to SESSION lifetime, so every test process
  recompiled its gtfn programs — for the graupel K-scan ~2 minutes per (grid-size,
  nlev) variant, which made the suite unusable. The plugin now `setdefault`s
  `GT4PY_BUILD_CACHE_LIFETIME=persistent` + `GT4PY_BUILD_CACHE_DIR=~/.cache/symcon/gt4py`
  before collection (before `gt4py.next.config` reads the env; explicit user/CI
  overrides win). Warm-cache component-test file: 18 s.

## Acceptance criteria → tests

1. **L2 parity** — `packages/symcon-icon/tests/test_graupel_datatest.py` (marker
   `data`): WEISMAN_KLEMP_TORUS microphysics-init/exit savepoints (only archive
   carrying them; the S06 GAUSS3D default is overridden), 3 dates ×
   {embedded, gtfn_cpu, gtfn_gpu (`gpu`-marked)} = 9 cases, at icon4py's own
   tolerances (provenance comments at the constants): temperature `rtol=1e-12`
   (dallclose defaults), six tracers `atol=1e-12`, surface precipitation rates
   `atol=9e-11` — fields *and* the four rate diagnostics are compared. The 6 CPU
   cases pass locally; the 3 gtfn_gpu cases skip cleanly without a CUDA device.
2. **Conservation + negativity** — hypothesis-generated admissible columns
   (bounded qv scaling 0.1–3 on the ICON reference atmosphere; condensate seeds
   qc ≤ 3e-3, qi/qr/qs/qg ≤ 1e-3), budget
   `Σq·rho·dz + total_ground_flux·Δt = const`:
   - mixed-phase/warm regime (condensate at T > 233 K): closes to fp round-off,
     contract `rtol=1e-13` (observed ≤ 3e-17);
   - any-column bound (condensate everywhere, incl. supercooled qc at T ≤ 233 K):
     documented `rtol=1e-5` (observed ≤ 4e-6) — see *Deviations/findings*;
   - negativity: no tracer < −QMIN (= −1e-15) on any tested column (observed
     ≥ −2.2e-19).
3. **Performance smoke** — `test_perf_smoke_gtfn_cpu_vs_embedded` (`slow` marker):
   gtfn_cpu ≥ 5× embedded on a 10 000-column batch (nlev=5 to keep the embedded
   reference affordable — gt4py embedded executes the K-scan per column in Python
   at ~25 ms/column; observed ratio ≫ 100×, tripwire passes with orders of margin).
4. **Structure mirror** — `test_graupel_component.py` mirrors
   `test_satad_component.py` section-for-section (fig-1 standalone, kstart_moist
   no-op, out= path, zero-copy ingress, coupling constraints + SUS/PS composition,
   wrong-level-count, config transcription); graupel-specific replacements: the
   fixed-point/idempotence test (satad-only physics) is replaced by the
   conservation pair, and scheme-registry + scheme-constants tests are added.

## Deviations / disagreements / findings

- **S06 ci flag resolved for S08** (`SPECIFIC_HEAT_CAPACITY_ICE` 2108.0 vs ICON
  Fortran `ci=2106.0`): graupel *does* reference `cpi` — but only inside the
  temperature-dependent latent-heat-of-sublimation branch
  (`graupel_stencils.py:233`, Kirchhoff form `lh_s + (cp_v − cpi)(T − tmelt) − rv·T`;
  ICON `mo_thdyn_functions.f90:291` identical with ci=2106). That branch is dead
  code under `use_constant_latent_heat=True` (`ithermo_water=0`), which is both the
  icon4py default and the WK serialized-data configuration — so the 2-J/kg/K
  disagreement is **not exercised by any verification data**. It becomes live only
  if a user sets `use_constant_latent_heat=False`; recorded here per AGENTS.md
  (icon4py remains the verification target).
- **Water-budget leak in the cold glaciation corner** (found by the hypothesis
  test): supercooled cloud water seeded at T ≲ 233 K near the top of the moist
  domain gains total water — up to ~4e-6 of the column water path in one Δt=30 s
  step (e.g. uniform qc=1.95e-3: +1.6e-4 kg/m²). Localized by probing: a *single*
  seeded level closes exactly; pairs of cold levels near the domain top do not —
  the fresh-ice glaciation + ice-sedimentation interplay across levels in the
  granule's scan. This is granule behavior (symcon adds only the `x + dx/dt·Δt`
  arithmetic, which cannot create mass; warm/mixed-phase columns close to 1e-17).
  Encoded as a *documented* any-column tolerance (`CONSERVATION_RTOL_COLD=1e-5`)
  next to the strict round-off contract for the admissible mixed-phase regime —
  not a loosening of a SPEC tolerance (the SPEC delegates to "scheme-documented
  tolerance"); worth an upstream icon4py issue (follow-up).
- **ICON Fortran vs icon4py**: `gscp_graupel.f90` at icon-2026.04-public takes
  `l_cv` as an input (the NWP interface passes `.TRUE.` — isochoric `cvd` heating,
  matching icon4py's hardcoded `RCVD`); ground precip rate
  `prr_gsp = 0.5·(qr·rho·vnew + flux_kup)` matches icon4py's
  `icon_graupel_flux_at_ground` exactly. The Fortran granule additionally exposes
  options icon4py removed as always-true/duplicated (`lsedi_ice`, `lstickeff`,
  `lred_depgrow`, `lpres_pri`, `ldiag_*tend`) — none configurable in the wrap.
- **`Microphysics` property contracts are class-level** (S03 machinery): with only
  the graupel scheme registered this is exact; a future second scheme with a
  different field list declares its own ClassVar contracts on its subclass (the
  registry dispatch in `__new__` already returns the subclass, so contracts follow
  the scheme). No machinery change needed now.
- **`total_precipitation_flux` not exposed**: at v0.2.0 the granule computes it
  only under `do_latent_heat_nudging=True` (else exact zeros), so a diagnostic
  would be misleading; the four per-species rates are exposed instead (their sum
  is the total).
- **Friend access to `VerticalGrid._i4_grid`** carried over from S07 (public
  accessor still proposed for trunk).
- Test-state builders put `icon:qnc` into the state locally
  (`_with_qnc`/datatest `_upload`) rather than extending the frozen S06
  `moist_test_column` output; S09's SCM composition should decide where qnc
  canonically lives (follow-up).

## Follow-ups

- S10: the `native` functional core (JAX) for graupel sharing
  `graupel_constants.py`; extend that module with whatever constants the core
  needs (currently only the symcon-consumed pair, by design).
- Upstream: report the cold-corner water-budget leak to icon4py (and check
  whether ICON Fortran reproduces it — likely, given the identical structure).
- Expose the icon4py vertical adapter publicly on `symcon.icon.grid.VerticalGrid`
  (S07 carry-over).
- The `data` tier now costs ~8 minutes locally (three embedded graupel cases at
  ~3.2 min each — the WK grid K-scan per column in Python). If the tier keeps
  growing, consider trimming embedded to one date and keeping all dates on
  gtfn_cpu (SPEC change → trunk decision, not taken here).
- First-ever gtfn compile of the graupel scan is ~2 min per (grid, nlev) variant;
  now amortized by the persistent cache (`~/.cache/symcon/gt4py`). Watch cache
  size growth as more gt4py components accumulate.

## Artifacts / gate results (local)

- `uv run pytest packages -m "not gpu" -q` — **515 passed, 1 skipped** (mpi
  opt-in), 25 deselected (data/gpu), 10:29 (includes the `slow` 10k-column perf
  smoke and warm-cache gtfn compiles).
- `uv run pytest packages/symcon-icon -m data -q` — **20 passed, 9 skipped**
  (all gpu legs: 3 graupel + 6 satad, "no CUDA device available"), 116
  deselected, 8:40. Graupel contributes 6 new CPU L2 cases; satad (12) and
  vertical-grid (2) datatests unchanged.
- New test files in isolation: `test_graupel_component.py` — 18 passed,
  5 skipped (gpu), 2:19; `test_graupel_datatest.py` — 6 passed, 3 skipped
  ("no CUDA device available"), 11:37.
- `uv run ruff check .` / `uv run ruff format --check .` — clean.
- `uv run mypy --strict -p symcon.core` — clean (45 files).
- `uv run lint-imports` — 2 contracts kept.
- No data files in git; WK archive reused from the S07 cache.
