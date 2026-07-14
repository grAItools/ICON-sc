# S11 — STATUS

**Branch:** `step/S11-icon-grid-metrics` · **State:** implemented, gates green (see §4)

## 1. What was built

`symcon/icon/grid/{reader,grid,geometry,metrics,interpolation}.py` — the §3.1/§3.2
horizontal grid stack on real ICON grid files, per the wrap-don't-rewrite precedent
(PLAN item 1: delegate to pinned icon4py wherever its API is not driver-entangled).

- **`reader.py`** — pure-numpy/netCDF4 ICON grid-file reader (`read_grid_file(path) ->
  GridFileData`), no gt4py imports (PLAN pitfall: reusable in P4 tooling). Variable
  names, `(sparse, horizontal)` transposition and the 1-based→0-based normalization
  (invalid `-1` preserved) transcribed from icon4py `gridfile.py`/`grid_manager.py`.
  Actionable `GridFileError`s name the file and the missing/mis-shaped
  variable/attribute/dimension; `refin_ctrl` defaults to zeros when absent
  (`has_refin_ctrl` records which).
- **`grid.py`** — `from_file(path, ctx) -> IconGrid` (frozen) delegating to icon4py's
  `GridManager` (derived diamond/butterfly connectivities, start/end indices,
  single-node decomposition). One storage, two views: `grid.connectivities` (read-only
  numpy int32 index arrays, `-1` invalid) and `grid.offset_providers` (the gt4py
  mapping incl. `Koff`, consumed directly by gt4py programs). `refin_ctrl` retained
  (§10 nesting provision). Declared public donor accessors for lane B:
  `icon4py_grid`, `icon4py_geometry`, `decomposition_info`, `gt4py_backend`.
- **`geometry.py`** — `grid.geometry.<named field>` (frozen): `cell_area`, `dual_area`,
  `edge_area`, `edge_length`, `dual_edge_length`, `vertex_vertex_length`,
  `tangent_orientation`, `coriolis_parameter` as cached read-only numpy fp64, computed
  lazily by icon4py `GridGeometry` on the grid's backend.
- **`metrics.py` / `interpolation.py`** — `metrics(grid, vgrid)` and
  `interpolation(grid)` (frozen) wrapping icon4py `MetricsFieldsFactory` /
  `InterpolationFieldsFactory`; outputs land as **read-only DataArrays** with registry
  names, canonical units, dims/location and `grid_uuid` provenance, returned in a
  read-only mapping. The field tables `METRICS_FIELDS` (38) / `INTERPOLATION_FIELDS`
  (16) are exactly the S12/S13 consumption set mined from icon4py
  `dycore_states.{MetricStateNonHydro,InterpolationState}` +
  `diffusion_states.{DiffusionMetricState,DiffusionInterpolationState}`
  (REFERENCES.lock `icon4py-dycore-diffusion-static-state`) — the S12 SPEC names S11
  as the coordination point for this list.
- **`names.py`** — registry extended by 47 `icon:` rows (metrics + interpolation
  statics); `docs/names_registry.md` regenerated via `tools/names_audit.py`.
- **`testing.py`** — datatest bridge re-exports `metrics_savepoint`,
  `interpolation_savepoint`, `topography_savepoint`; new `download_grid_file()`
  helper (grid files download independently of experiment archives).
- **S06 additive extensions (declared here, defaults preserve behavior):**
  `SleveConfig` gains the SLEVE decay knobs `decay_scale_1/decay_scale_2/
  decay_exponent` (mo_sleve_nml; consumed by the metrics factory's terrain-following
  surface computation); `VerticalGrid.__init__` gains keyword-only
  `config: SleveConfig | None` (full namelist for ingested tables); the S07-flagged
  `_i4_grid` friend access becomes the public `VerticalGrid.icon4py_grid` property
  (S11 is its first out-of-module consumer — the sanctioned fix).
- **deps:** `netcdf4>=1.6` declared for symcon-icon (already in the resolved lock via
  symcon-core; a declaration, not a bump — uv.lock diff is that entry only).

## 2. Acceptance criteria → tests

1. **Reader round-trip** — `tests/test_grid_reader.py` (12 unit tests on synthetic
   NetCDF: counts/dims/dtypes, 0-based normalization with `-1` kept, actionable
   errors for missing file / non-NetCDF / missing dim / missing variable / missing
   uuid / bad shape) + `tests/test_icon_grid_datatest.py` (real grids: counts vs file
   dims, uuid preserved through the wrapper, Euler-characteristic sanity, coordinate
   shapes).
2. **Connectivity cross-check** — `test_icon_grid_datatest.py`: the pure reader's
   index tables vs icon4py's grid object for the same file (independent paths meet
   bitwise), on both grids; derived connectivities present.
3. **Metrics/interpolation parity** — `tests/test_static_fields_datatest.py`
   (markers `data`+`slow`): 36 metrics cases + `nflat_gradp` + 16 interpolation
   cases on **EXCLAIM_APE**, each at icon4py's own per-field tolerances. Provenance:
   most rows from their v0.2.0 factory tests (REFERENCES.lock
   `icon4py-grid-metrics-tests`); six fields have no upstream factory test
   (rho_ref_mc, theta_ref_ic, d_exner_dz_ref_ic, theta_ref_me, rho_ref_me,
   wgtfac_e) and use the tolerances of icon4py's test_reference_atmosphere.py /
   test_metric_fields.py instead — the strict dallclose default rtol=1e-12/atol=0
   (rho_ref_me: rtol=1e-10) — REFERENCES.lock `icon4py-refatm-metric-field-tests`.
   Boundary-zone slicing (`LATERAL_BOUNDARY_LEVEL_2` starts for
   zdiff/vertoffset_gradp, geofac_rot, RBF coefficients) mirrors upstream exactly.
   A closure test asserts the parity tables cover every produced field and that all
   outputs are read-only, registry-named, uuid-stamped DataArrays.
4. **Offset providers** — `test_icon_grid_datatest.py`: trivial gt4py `neighbor_sum`
   over C2E with `grid.offset_providers` vs a numpy gather-sum, on embedded +
   gtfn_cpu (+ gpu-marked gtfn_gpu leg, skips cleanly without a device).
5. **refin_ctrl** — regional grid: boundary zones populated (`limited_area=True`);
   global grid: see deviation D3; absent-variable default unit-tested synthetically.

## 3. Deviations & decisions

- **D1 — Parity experiment is EXCLAIM_APE, not JW.** The SPEC asks for "the global
  grid used by icon4py's JW/driver datatest": that grid is
  `icon_grid_0013_R02B04_R`, shared by `Experiments.JW` and
  `Experiments.EXCLAIM_APE`. Parity runs on EXCLAIM_APE because it is the experiment
  icon4py's own metrics/interpolation factory tests validate against, with published
  per-field tolerances (JW has none upstream — using it would have meant inventing
  tolerances, i.e. tolerance creep). Same horizontal grid either way; S13's JW work
  reuses the grid file already cached here.
- **D2 — Factories run on gtfn_cpu in the parity test.** icon4py marks several
  metric fields `embedded_remap_error` (wgtfac_c, pg_exdist, zdiff_gradp, zd_*) —
  the embedded backend cannot produce them upstream either. The `metrics()` /
  `interpolation()` surfaces themselves are backend-agnostic (backend comes from the
  grid's `ctx`).
- **D3 — Acceptance 5 wording vs reality.** The global `icon_grid_0013_R02B04_R`
  file *does* carry `refin_c/e/v_ctrl` (constant nest-parent values ≤ 0, no boundary
  zones ⇒ `limited_area=False`). "Absent-but-defaulted" is implemented and tested on
  a synthetic file without the variables (`test_refin_ctrl_absent_but_defaulted`);
  the real-grid test asserts what is actually in the file. No SPEC contradiction in
  substance — refin_ctrl is retained and absence is defaulted — recorded here
  because the acceptance text guessed the global file lacks the variables.
- **D4 — Units for solver-internal statics.** icon4py/ICON declare no units for the
  coefficient fields (`units=""` in their metadata). The registry rows use "1" for
  weight/mask-like coefficients and physically fixed units where the defining
  formula is unambiguous (`m` for distances zdiff_gradp/pg_exdist/pos_on_tplane_e,
  `m-1`/`m-2` for geometric-derivative factors, K / kg m-3 for the reference-state
  family, consistent with the existing S06 rows). Documented per row in `names.py`.
- **D5 — `from_file` takes `num_levels` (keyword-only, default 1) and
  `keep_skip_values` (keyword-only, default True).** icon4py bundles the vertical
  size with the horizontal grid object (`GridConfig.vertical_size`; their TODO
  acknowledges the coupling). A grid file knows nothing vertical, so the symcon
  surface takes it as an optional keyword; `metrics()` validates
  `grid.num_levels == vgrid.nlev` with an actionable message. `keep_skip_values`
  mirrors icon4py's GridManager knob (True — the geometry/factory convention —
  preserves raw `-1` neighbors; False lets gt4py replace them for stencils that
  compute over boundary temporaries). Both declared additive extensions of the
  frozen `from_file(path, ctx)` signature.
- **D8 — `grid.connectivities` copies; `grid.offset_providers` aliases.** §3.1 says
  "two forms from one storage": the offset-provider mapping aliases the wrapped
  icon4py connectivity storage (zero-copy into gt4py programs), while the raw numpy
  view is a one-time read-only *copy* — a deliberate immutability trade-off so
  numpy/JAX consumers cannot mutate the tables the gt4py programs execute over
  (one ~O(n_edges·sparse) int32 copy per grid, cached).
- **D6 — Registry short names `geofac_grg_x/_y`, `pos_on_tplane_e_x/_y`.** ICON
  stores single arrays with a trailing 1:2 slab; the S06 registry enforces unique
  ICON short names, so the slabs get suffixed names (matching icon4py's own
  savepoint/factory split).
- **D7 — `interpolation()`/`metrics()` accept icon4py config objects** (`config=`,
  `interpolation_config=`; `None` → ICON namelist defaults). Transcribing
  `MetricsConfig`/`InterpolationConfig` into symcon dataclasses (S08-style) was
  deliberately skipped: S12 owns the symcon-facing config surface for the solver;
  duplicating the factory knobs here would create a second source of truth.
- **RBF cell coefficients** (`rbf_vec_coeff_c1/c2`) are not produced: not consumed
  by S12/S13 states. Follow-up F2.

## 4. Gates (2026-07-11)

- `uv run pytest packages -m "not gpu and not slow" -q` — **667 passed, 1 skipped
  (mpi marker), 113 deselected**
- `uv run pytest packages -m "slow and not gpu" -q` — **85 passed, 696 deselected**
  (includes the 55-test S11 parity module)
- `uv run pytest packages/symcon-icon -m data -q` — **92 passed, 11 skipped (all
  gpu-legs without a CUDA device), 257 deselected**. New archives downloaded (all
  via icon4py's datatest machinery into `~/.cache/symcon/icon4py-testdata`, nothing
  in git): grid files `icon_grid_0013_R02B04_R.nc` (15 MB) and
  `mch_ch_R04B09_DOM01.nc` (13 MB); serialized experiment
  `mpitask1_exclaim_ape_R02B04_v04.tar.gz` (**4.0 GB compressed / 8.7 GB
  extracted**).
- `ruff check` + `ruff format --check .` — clean (151 files)
- `mypy --strict -p symcon.core` — clean, 50 files (S11 code lives in symcon-icon)
- `lint-imports` — 2 contracts kept, 0 broken
- New test files in isolation: test_grid_reader.py **12 passed**;
  test_icon_grid_datatest.py **14 passed, 2 gpu-skipped**;
  test_static_fields_datatest.py **55 passed**.

## 5. Follow-ups

- **F1:** `GridGeometry` computes lengths/normals from coordinates; the file-sourced
  values (edge_length, …) pass through today. When ExtPar/topography ingestion (P4)
  lands, decide whether symcon re-exposes icon4py's recomputed or file values for
  LAM grids with the known generator quirks (icon4py TODOs in grid_manager.py).
- **F2:** add `rbf_vec_coeff_c1/c2` (cell RBF) when the `WindReconstruction`
  diagnostic (§3.3) is implemented — the factory already provides them.
- **F3:** distributed construction (decomposer ≠ single-node) is P5; `from_file`
  currently hard-codes icon4py's single-node path.
- **F4:** metrics() recomputes the interpolation factory internally; if S12 wants to
  share one instance across both calls, add a keyword to pass a prebuilt factory
  (cheap: registration is lazy, fields are computed once per factory instance).

## 6. Review fixes (round 1)

- **MAJOR 1 (tolerance loosening, misattributed provenance):** six metrics parity
  rows (rho_ref_mc, theta_ref_ic, d_exner_dz_ref_ic, theta_ref_me, rho_ref_me,
  wgtfac_e) had been given atol=1e-9/1e-10 (wgtfac_e rtol=1e-9) and attributed to
  upstream factory tests that do not exist for them — an undeclared loosening.
  Tightened to the tolerances of their actual upstream tests
  (test_reference_atmosphere.py l.91/149/186/232-233, test_metric_fields.py l.367):
  the strict dallclose default rtol=1e-12/atol=0, rho_ref_me rtol=1e-10. All six
  green at the tightened tolerances on gtfn_cpu/EXCLAIM_APE. Provenance corrected
  in the test docstring, §2.3 above, and REFERENCES.lock (appended corrective entry
  `icon4py-refatm-metric-field-tests`; the ledger is append-only).
- **MINOR 2:** `keep_skip_values` extension of `from_file` declared in D5.
- **MINOR 3:** `_check` now passes `equal_nan=False` to `assert_allclose`
  (upstream dallclose semantics; co-located NaNs fail).
- **MINOR 4:** §1 row count corrected 48 → 47.
- **INFO:** D8 added — connectivities-copy vs offset-providers-alias trade-off.
