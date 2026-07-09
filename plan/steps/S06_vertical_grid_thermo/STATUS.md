# S06 — STATUS

**Branch:** `step/S06-vertical-grid-thermo` · **State:** implemented, all gates green.

## What was built

- `symcon/icon/_constants.py` — flat ICON constants module (the layout-§5
  shared-constants precedent). Every value transcribed from pinned ICON Fortran
  (`mo_physical_constants.f90`; `h_scal_bg`/`t0sl_bg`/`del_t_bg` from
  `mo_vertical_grid.f90` module PARAMETERs, where ICON actually defines them); each
  constant cites its Fortran symbol; derived constants reproduce the Fortran
  derivation expression operation-for-operation (bitwise equality).
- `symcon/icon/thermo.py` — array-namespace-generic (array_api_compat) thermo
  relations: `exner_from_pressure` / `pressure_from_exner` (cpd path),
  `exner_from_rho_thetav` (cvd path, `EXP(rd_o_cvd*LOG(...))` verbatim — both paths
  exposed and named per the PLAN pitfall), `virtual_temperature`,
  `virtual_potential_temperature`, `temperature_from_thetav_exner` (ICON `diag_temp`
  verbatim). Frozen signatures per SPEC; pure operators/xp calls only, so S10 can
  import them unchanged for JAX.
- `symcon/icon/grid/vertical.py` — frozen `VerticalGrid(vct_a, vct_b, nlev)` +
  `SleveConfig` + `compute_vct_a_and_vct_b`. Per PLAN item 1 the implementation
  *reuses* icon4py's `VerticalGrid`/`get_vct_a_and_vct_b` internally (numpy-speaking
  adapter; index semantics `nflatlev`/`nrdmax`/`kstart_moist` therefore identical to
  the donor by construction, and cross-checked in tests). Reference-atmosphere
  helpers (`reference_temperature/pressure/exner/potential_temperature/rho`)
  implemented in symcon (array-generic) from the `mo_vertical_grid.f90` formulas.
- `symcon/icon/names.py` — registry seed (36 rows): the 18 S02 core rows re-asserted
  (consistency-checked, not re-registered), plus `pres_ifc`/`temp_ifc`,
  `altitude`(+interface variant, CF: altitude = height above geoid for
  `z_mc`/`z_ifc`), `icon:ddqz_z_{full,half}`, reference-state rows
  (`icon:{exner,theta,rho}_ref_mc`), and the tendency-bus slots `icon:ddt_temp`,
  `icon:ddt_q[vcirsg]`, `icon:ddt_exner_phy`, `icon:ddt_temperature_slow` (S09's
  slot, seeded here per "tendency-bus slot names for temperature"). Frozen
  `QUANTITIES` mapping.
- `symcon/icon/testing.py` — column builders `isothermal_column` (barometric
  formula) and `moist_test_column(profile_id)` (`reference_dry` / `reference_moist`
  on the ICON reference atmosphere), returning valid symcon states (make_dataarray,
  canonical units, `(cell, height[/height_interface])`); icon4py datatest fixture
  bridge (re-exports `grid_savepoint` & friends, defaults the experiment to GAUSS3D
  and the download cache to `~/.cache/symcon/icon4py-testdata`), degrading to skip
  when `symcon-icon[datatest]` is not installed.
- `tools/names_audit.py` + generated `docs/names_registry.md` (committed; test
  regenerates and byte-compares).
- Tests: `packages/symcon-icon/tests/` — thermo round-trips (acceptance 1),
  committed Fortran byte-compare table (acceptance 2), icon4py cross-checks via
  embedded field operators (acceptance 3), vertical-grid unit tests + GAUSS3D
  grid-savepoint reproduction under marker `data` (acceptance 4), registry/docs
  tests (acceptance 5), column-builder validity/consistency tests.

## Acceptance criteria

1. **Round-trips to 1e-12** — green (`test_thermo.py`; rtol=1e-12, atol=0 over a
   dense p∈[1e3,1.08e5] Pa × T∈[180,330] K × qv∈[0,0.035] × qc∈[0,0.02] grid).
2. **Constants byte-compare vs pinned Fortran** — green
   (`test_constants_fortran.py`; table committed with file:line provenance,
   `==` comparisons).
3. **icon4py cross-check to 1e-12** — green (`test_icon4py_crosscheck.py`):
   constants byte-compare; θv/T diagnosis vs `_diagnose_virtual_temperature_and_
   temperature` (embedded); reference atmosphere vs
   `_compute_reference_atmosphere_cell_fields` (embedded). *Recorded justification:*
   the pinned icon4py exposes **no standalone p↔exner helper** (the conversion only
   appears fused inside larger stencils), so that pair is verified against the ICON
   Fortran formulas in `test_thermo.py` instead.
4. **Grid savepoint to 1e-12 (marker `data`)** — green, run locally
   (`test_vertical_grid_datatest.py`): GAUSS3D (`exclaim_gauss3d`, 57 MB archive —
   smallest available; APE/R04B09/JW are 4–7 GB). Both directions: SLEVE-computed
   table vs serialized `vct_a`/`vct_b`, and ingested savepoint table reproducing
   interface heights + `nflatlev`.
5. **Registry** — green (`test_names.py`): every seeded quantity passes S02
   registration validation; `icon:` locals collide with nothing; docs table
   generated and committed, byte-compared on regeneration.

## Deviations & decisions (none silently resolved)

- **S02 already seeded 18 of the "first ~40" rows** (SPEC S06 says the seed lives in
  `symcon/icon/names.py`; S02 landed a core seed in `symcon.core.state.names`, which
  is frozen). Resolution: `symcon.icon.names` re-asserts those rows (import-time
  consistency check raising on drift) and registers the remainder; `QUANTITIES` is
  the full union table. Not a contradiction with the architecture doc, but the split
  ownership is worth a trunk look.
- **Tendency-slot naming:** SPEC asks for `icon:ddt_*` for temperature/qx. Chosen:
  `icon:ddt_temp`, `icon:ddt_q[vcirsg]` (ICON `prm_nwp_tend` family naming), plus
  `icon:ddt_exner_phy` (ICON `t_nh_diag`, the cvd-based isochoric coupling slot the
  PLAN pitfall points at) and `icon:ddt_temperature_slow` (S09 SPEC's slot name,
  registered here so S09's component can declare it).
- **`vn` GRIB2 column:** all `grib2` entries are `None` for now — the SPEC lists the
  column for ingestion only (§7.2, P4); populating it is deferred to the ingestion
  phase rather than inventing triplets from memory.
- **Dependencies added (not pins changed):** `symcon-icon` gained
  `array-api-compat>=1.4` and `numpy` (both already in the resolved set) and an
  optional extra `datatest` (icon4py-testing + the icon4py packages its
  `datatest_utils` imports at import time, incl. `icon4py-standalone-driver`); the
  workspace dev group references `symcon-icon[datatest]`. All icon4py members
  resolve to 0.2.0, exactly the S01 pinned set (`constraints/cpu-ci.txt` already
  listed `icon4py-testing==0.2.0`). No gt4py/icon4py version changed.
- **Moist-profile humidity constants** (`qv0=0.01`, `hq=2500 m`) are a *synthetic
  test fixture*, documented as such in the docstring — the SPEC's scientific-fidelity
  rule covers physical constants/algorithms (all mined); a test humidity magnitude
  has no ICON ground truth to mine. The thermodynamics applied to it is ICON's.
- **ICON Fortran source:** `gitlab.dwd.de` does not resolve from this host; used the
  canonical public mirror `gitlab.dkrz.de/icon/icon-model` (icon-model.org's
  published location), tag `icon-2026.04-public`, commit `8597da45` — recorded in
  REFERENCES.lock. icon4py (v0.2.0) and this ICON release agree on every constant
  used here; no icon4py-vs-Fortran disagreement to record. (Noted for later steps:
  icon4py's `SPECIFIC_HEAT_CAPACITY_ICE = 2108.0` has no exact match in this ICON
  release (`ci = 2106.0` in the sea-ice section); S06 does not use it — flag for
  S07/S08 if the granules need it.)

## Follow-ups

- S07/S08: the `data`-marked pattern (fixture bridge + GAUSS3D default) is ready for
  the satad/graupel savepoint parity tests; those will likely need larger archives.
- Gate policy for `data` tests in CI (57 MB download on first run; cached under
  `~/.cache/symcon/icon4py-testdata`) is a trunk decision; locally they are part of
  `-m "not gpu"` and pass.
- `serialbox4py` import emits a numpy binary-compat `RuntimeWarning` (built against
  an older numpy C-API than the resolved numpy). Harmless today; worth watching at
  the next pin refresh.
- The GRIB2 column and remaining ~P3 registry rows (radiation, turbulence, surface)
  arrive with their components.

## Gates (final run)

- `uv run pytest packages -m "not gpu" -q` — **453 passed, 1 skipped (mpi), 4
  deselected (gpu)**; data tests included and green (GAUSS3D cached).
- `uv run pytest packages/symcon-icon -m data -q` — **2 passed** (run once locally,
  network fetch exercised).
- `uv run ruff check .` / `uv run ruff format --check .` — clean (106 files).
- `uv run mypy --strict -p symcon.core` — clean (43 files); bonus:
  `uv run mypy -p symcon.icon` clean (7 files, non-gate).
- `uv run lint-imports` — 2 contracts kept, 0 broken.

## Artifacts

- `docs/names_registry.md` (generated registry table, committed).
- REFERENCES.lock: two new S06 entries (icon4py v0.2.0 mining scope; icon-fortran
  DKRZ mirror `8597da45`).

## Review fixes (round 1)

- **MINOR-2 (fixed)** — `symcon.icon.testing` no longer mutates process env as an
  unconditional import side effect: the `ICON4PY_TEST_DATA_PATH` setdefault now runs only
  when `icon4py.model.testing` is importable (i.e. the `symcon-icon[datatest]` extra is
  installed), where it is required before icon4py's config module reads the env.
- **MINOR-1 (declared)** — follow-up: the `names.py` re-assert consistency check compares
  `units` and `icon_name` only; extend it to `cf_name` (and the GRIB2 triplet when that
  column is populated) so core-seed drift in those columns cannot pass silently.
- **INFO-3 (fixed)** — `pressure_from_exner` docstring now cites the plain-form source
  (`mo_nh_vert_extrap_utils.f90:754`) and notes the fused surface-pressure variant's
  location separately.
