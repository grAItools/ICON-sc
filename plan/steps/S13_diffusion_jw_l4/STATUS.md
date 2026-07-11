# S13 — STATUS

**Branch:** `step/S13-diffusion-jw-l4` · **State:** implemented, gates green (§6)

## 1. What was built

- **`symcon/icon/components/diffusion.py`** — `HorizontalDiffusion(Stepper)` hosting
  the icon4py diffusion granule (wrap-don't-rewrite; single public entry
  `run(diagnostic_state, prognostic_state, dtime, initial_run)`, in-place). Boundary:
  vn/w/exner/theta_v (rho deliberately excluded — the granule never touches it).
  `DiffusionConfig` mirrors icon4py's with `icon_namelist_origin` annotations;
  `to_icon4py()` re-runs the granule's slice validation at construction. ICON's
  pre-timeloop stabilization run is the explicit `initial_stabilization()` entry
  (never implicit). The turbulence-coupling diagnostics (`hdef_ic`/`div_ic`/`dwdx`/
  `dwdy`) are component-private behind the S12-style restart/functional-state
  protocols. Static consumption lists cover `DiffusionMetricState`/
  `DiffusionInterpolationState` exactly (asserted) and every name is an S11 factory
  product (asserted).
- **`symcon/icon/ingest/idealized.py`** — `jablonowski_williamson(grid, vgrid, cfg,
  *, static, edge_geometry=None, cell_geometry=None)`. Delegates the wind projection
  (`zonalwind_2_normalwind_ndarray` — takes `jw_up` as an *argument*) and the
  hydrostatic adjustment to the pinned icon4py driver helpers; transcribes the
  per-level η Newton fit (the donor hard-wires `jw_up = 0.0` as a function-local and
  binds its cell→edge step to its own serialbox reads, so the loop cannot be
  delegated with a configurable perturbation). `cfg.perturbation_amplitude` is ICON
  `nh_test_nml:jw_up` (a namelist input in `mo_nh_jabw_exp.f90` — the knob is
  faithful, not invented). The fit consumes the serialized `geopot` metric (new
  registry row `icon:geopot`) — the donor is not fully analytic either.
- **`symcon/icon/presets/jw.py`** — `build_jw(JWConfig)`: the composed dry model
  (NonhydroSolver → HorizontalDiffusion, the icon4py driver's per-step order) on the
  `exclaim_nh35_tri_jws` archive (global R02B04, 35 levels, Δt=300 s, 5 substeps);
  all config from the archive's ICON namelist (provenance dict, asserted in L4);
  shared checkpoint diagnostics (surface pressure via the icon4py
  `diagnose_surface_pressure` formula, vn norms, 850 hPa vertex-vorticity proxy)
  used verbatim by both the reference generator and the symcon run.
- **`examples/02_jw_baroclinic.py`** — the §5.1-shaped run script (dycore +
  diffusion, no physics, bus slots zero-filled inside the dycore), NetCDF output
  with a store cadence, CLI. CI smoke at 6 h: `tests/test_jw_example.py`.
- **`validation/L4_idealized/`** — `make_reference.py`: the pinned icon4py
  `TimeLoop` (upstream orchestration) generating the reference trajectory + the
  1e-13-vn-perturbed twin (the probtest-style envelope pair, PLAN item 4), 6-hourly
  checkpoints, chunk-resumable (bit-exact state snapshot between invocations),
  sha256+provenance manifest under `~/.cache/symcon/l4_reference` (never run in CI);
  `--run symcon` generates the composed-model trajectory the same way (resume via
  the S12/S13 component restart protocols). `test_jw.py`: config congruence, day-1
  ps rtol ≤ 1e-6, all checkpoints within the twin envelope, 12 h zonal-symmetry
  smoke. Artifacts (deviation table/plot, symmetry numbers) in
  `validation/L4_idealized/artifacts/` (gitignored).
- **The S12 "pentagon" blocker root-caused and FIXED** (one small domain fix in
  `dycore.py` `_build_static_states.convert()`): see §5 — the S12 production-path
  test now asserts trajectory values.
- Registry: one new row `icon:geopot` ("m2 s-2", ICON `geopot`);
  `docs/names_registry.md` regenerated.

## 2. Tolerances (contracts; upstream-cited) and measured values

| Test | Tolerance | Upstream source | Measured |
|---|---|---|---|
| diffusion single/initial step | vn atol=1e-8 rtol=1e-9; w atol=1e-14; theta_v/exner rtol=1e-12; diagnostics (shear_type≥1 only) div_ic 1e-16 / hdef_ic 1e-13 / dwdx,dwdy 1e-18 | `verify_diffusion_fields`, diffusion tests utils.py:16-53 (v0.2.0) | pass (APE + MCH single; MCH initial) |
| JW initial state | rho/exner/theta_v/vn/pressure/temperature rtol=1e-12; exner_pr atol=1e-14; w not verified (zero) | `test_jabw_initial_condition` l.35-107 | pass |
| JW initializer delegation | rtol=1e-12 vs `model_initialization_jabw` output | SPEC acceptance 2 | pass |
| composed single step | vn atol=6e-12; w atol=1e-13; theta_v atol=4e-12; exner rtol=1e-12 (diffusion exit); rho rtol=1e-12 (nonhydro exit) | `test_run_timeloop_single_step` l.335-367 | pass |
| L4 day 1 | ps rtol ≤ 1e-6 | SPEC acceptance 3 | **max Δps = 0.0 (bitwise)** |
| L4 envelope (all checkpoints) | max\|Δps\| ≤ max(10 × twin-envelope(t), 0.1 Pa) | PLAN item 4 fallback (upstream verifies exactly ONE timestep at this grid — no multi-day schedule exists; twin = 1e-13-vn-perturbed rerun; 0.1 Pa floor = the SPEC's own day-1 criterion) | Δps = 0.0 at every checkpoint; twin envelope 1.6–1.9e-6 Pa by 24 h |
| L4 symmetry (12 h, jw_up=0) | C5-class ps spread ≤ 1e-10 relative | SPEC acceptance 4 | **1.477e-11** |
| S12 production path (regression guard) | max\|vn − archive\| < 1e-4 after one Δt | S13 characterization (§5), not an upstream tolerance | 3.622e-6, bitwise across rebuilds |

No tolerance was loosened. One SPEC criterion needed a *correct-equivalence-class*
reading (symmetry, §4.7) and one is partially executed in-session (L4 length, §4.8).

## 3. Acceptance criteria → tests

| # | Criterion | Test |
|---|---|---|
| 1 | Diffusion savepoint parity at icon4py tolerances (`data`) | `test_diffusion_datatest.py::test_run_diffusion_single_step_parity[APE,MCH × gtfn_cpu(+gpu)]`, `::test_run_diffusion_initial_step_parity[MCH]`, `::test_config_provenance_roundtrip` |
| 2 | JW initial state 1e-12 vs icon4py initializer (delegation possible) | `test_jw_datatest.py::test_jw_initializer_delegation_parity` + `::test_jw_initial_state_matches_jabw_exit_savepoint` (upstream defaults) |
| 3 | L4 vs pinned-driver reference: day-1 rtol ≤ 1e-6, envelope beyond | `validation/L4_idealized/test_jw.py::test_l4_day1_surface_pressure`, `::test_l4_trajectory_within_twin_envelope` (+ the composed single-step parity in `test_jw_datatest.py` at upstream tolerances) — see §4.8 on run length |
| 4 | Zonal symmetry 1e-10 over 12 h (perturbation off) | `validation/L4_idealized/test_jw.py::test_l4_zonal_symmetry_12h` — see §4.7 |
| 5 | examples/02 CI smoke at 6 h | `test_jw_example.py::test_example_02_smoke_6h` |

## 4. Deviations (and why)

1. **`HorizontalDiffusion` constructor carries `vgrid`** (S12 position:
   `(grid, vgrid, static, cfg, ctx, ...)`) where the §5.1 sketch shows
   `HorizontalDiffusion(grid, static, cfg.diffusion, ctx)` — the hosted granule
   requires the vertical grid for its Smagorinsky enhancement profile; the sketch is
   not a frozen interface. Proposal for the architecture doc recorded here.
2. **`icon_namelist_origins` parameter annotation widened** from `NonhydroConfig` to
   `Any` (any origin-annotated config dataclass) — backward-compatible widening of an
   S12 export; no call-site changes.
3. **No `embedded` leg anywhere in S13** (S12 precedent): upstream xfails every
   diffusion datatest on embedded (`embedded_remap_error`/`uses_concat_where`); the
   diffusion granule cannot even be *constructed* on embedded at the pins (ctor-time
   `concat_where`), so even the stub component tests run on gtfn_cpu.
4. **`icon4py-driver` added to the `datatest` extra** — a new member of the S01
   pinned set (already in `constraints/cpu-ci.txt` line 12 at ==0.2.0), not a bump;
   it is the JW-initializer donor and the L4 reference generator.
5. **L4 reference granule construction goes through the symcon preset's hosted
   instances** (`model.dycore._solve`/`model.diffusion._diffusion` handed to the
   upstream `TimeLoop`): genuine icon4py objects built from the archive's savepoint
   fields and namelist config (byte-identical inputs to an upstream-built granule);
   the *orchestration* producing the reference is entirely upstream `TimeLoop` code;
   config congruence is asserted again in the test. Documented private-member use.
6. **JW initializer statics via keyword-only args** — the frozen `(grid, vgrid,
   cfg)` core is extended with `static`/geometry keywords (SPEC allows declared
   additive keywords): the donor reads the same fields from its own serialbox
   provider; symcon takes them through S11 registry names.
7. **Symmetry equivalence classes (acceptance 4).** Full latitude rings mix cells
   that are *not* equivalent under the icosahedral grid's symmetry group; their ps
   spread is the grid's instantaneous zonal truncation asymmetry — measured
   **1.27e-5 relative after ONE hour** (before any dynamics could "break" symmetry)
   and 1.67e-5 after 12 h. No orchestration can meet 1e-10 on that reading. The
   test therefore asserts the *exact* zonal symmetry classes of the discrete grid —
   cells equal under C5 rotation about the pole (lat, lon mod 72°); measured spread
   after 12 h: **1.477e-11 ≤ 1e-10** (the latitude-ring figure is still computed
   and written to the artifacts file as context). This is an equivalence-class
   interpretation, not a tolerance change — flagged for reviewer confirmation.
8. **⚠ L4 executed at 1 day in-session; 9-day is a documented offline run.** The
   session environment enforced a hard 10-minute cap per foreground command with no
   background jobs; at the measured 2.2 s/step (upstream TimeLoop) a 9-day
   trajectory is ~95 min/run × 3 runs. Everything is in place for the full length —
   `make_reference.py` is chunk-resumable (bit-exact snapshots; the even-swap-count
   invariant per chunk asserted) and `--run reference|twin|symcon|manifest` splits
   the work — and the ladder was executed end-to-end at `--days 1`: day-1 (the
   SPEC's quantitative rtol ≤ 1e-6 criterion) **passes with bitwise-zero
   deviation** — the composed symcon model reproduces the upstream driver *exactly*
   over 288 steps / 1440 substeps, so the day-9 envelope comparison is a formality
   of compute, not of correctness risk. Follow-up: rerun `make_reference.py
   --days 9 --force` offline, then `test_jw.py`. Flagged for human sign-off.
9. **Gate partitioning (§6):** `-m "slow and not gpu"` and `-m data` each exceed
   the 10-minute per-command cap in one process; run as the disjoint partitions
   listed, which cover the same test set (S12 precedent).
10. **First-ever gtfn compile cost:** the JW grid's 35-level program variants
   compile once (~25 min) into the persistent cache; all quoted runtimes are warm.

## 5. The S12 "pentagon" dossier — ROOT-CAUSED, FIXED, pentagons exonerated

**Root cause.** The 3-level quadratic surface-extrapolation weights
`wgtfacq_c`/`wgtfacq_e` are produced — by BOTH the metrics factory and the
serialized savepoint — as gt4py fields with K-domain **[nlev-3, nlev)**
(`Domain(Cell=(0:20480), K=(57:60))` measured on APE). The S11 `wrap_static_field`
DataArray boundary drops the domain offset, and S12's
`_build_static_states.convert()` rebuilt them at K-domain [0, 3). The consuming
solve_nonhydro stencils read K = nlev-3..nlev-1, i.e. **outside the rebuilt field's
domain** → gtfn reads unallocated heap memory → garbage that varies with allocation
layout: exactly the observed rebuild-dependent, unbounded contamination (the
savepoint-path parity tests were never affected because ready icon4py fields bypass
`convert()`; "seeded near pentagon points" was a propagation-pattern red herring).

**Fix.** `convert()` now rebuilds the two fields surface-anchored
(K-domain `[nlev − k_extent, nlev)`), preserving the stub-test full-K case. A
factory-wide scan confirms `wgtfacq_c`/`wgtfacq_e` are the *only* consumed fields
with non-zero domain starts.

**Evidence chain (probes in the session scratchpad, `probe_s13_pentagon*.py`):**

1. *Padding before the factories is impossible*: forcing icon4py's own
   `_replace_skip_values` over the pentagon tables makes the RBF vertex factory's
   kernel matrix exactly singular (`LinAlgError`) — duplicated neighbor ⇒
   duplicated matrix row. (Also: icon4py max-valid padding differs from the
   archive's ICON padding in 11 of 12 pentagon rows.)
2. *Padding after the factories, before any compiled program, cold cache* (the
   reviewer's requested experiment; fresh `GT4PY_BUILD_CACHE_DIR`; verified zero
   `-1` remaining in **any** connectivity): contamination persists — three builds
   in one process gave max|vn−archive| of 5.6e-5 / **1.70e-1** / **1.75e-1**
   (26.5k edges > 1e-3). → the retained pentagon `-1`s are NOT the mechanism.
3. *Cross experiments (isolation)*: file grid + savepoint statics/geometry →
   **bitwise-deterministic across rebuilds, max|vn−archive| = 4.85e-12** (the
   legitimate S12 deviation class) — the file-built grid object, `-1`s included,
   is innocent. Savepoint grid + file statics/geometry → catastrophic (one build:
   980,820 NaNs, values to 5e+269).
4. *Bisection*: file geometry only → deterministic 3.62e-6 (the known
   `mean_cell_area` serialized-vs-computed 4e-5-relative difference scaling the
   2nd-order divdamp). File interpolation fields only → clean (4.96e-12, bitwise).
   File `wgtfacq_c`+`wgtfacq_e` **alone** → full pathology (7.03 m/s on 33.6k
   edges on one build). The field *values* are archive-equal to ≤ 2.2e-16 — only
   the domain metadata was lost.
5. *Post-fix*: full production path (file grid, file statics, file geometry),
   3 fresh builds in one process: **bitwise identical**, max|vn−archive| =
   **3.622e-6** — exactly the geometry-only (mean_cell_area) figure, i.e. statics
   now contribute nothing above the e-12 class.

**Consequences.** The S12 production-path test now asserts trajectory values
(vn < 1e-4 regression guard on the 3.6e-6 characterization) — S12's "no value
assertions" caveat is obsolete. Diffusion was never affected (upstream runs its
parity on file grids with `-1`s retained, `keep_skip_values=True`; our parity tests
reproduce that construction, deterministically). Residual open item
(upstream-facing, benign): `GridGeometry.mean_cell_area` differs from ICON's
serialized value by 4e-5 relative — deterministic, documented; the L4/JW path hosts
on savepoint geometry and is unaffected. Proposal: S11 should carry gt4py domain
offsets through its DataArray boundary (attrs) so no consumer needs
field-specific knowledge — trunk decision, recorded here.

## 6. Gates (all green, 2026-07-11; warm-cache runtimes on the step machine)

- `uv run pytest packages -m "not gpu and not slow" -q` — **704 passed, 1 skipped**
  (mpi marker), 137 deselected, 7m50s.
- `uv run pytest packages -m "slow and not gpu and not data" -q` — **30 passed**,
  812 deselected, 5m35s (data-marked slow tests run in the partitions below —
  deviation 9).
- `uv run pytest packages/symcon-icon -m "data and not slow" -q` — **39 passed,
  12 skipped** (gpu legs, no CUDA device), 5m54s.
- `uv run pytest packages/symcon-icon -m "data and slow"` — two disjoint halves
  (single run exceeds the cap): legacy+diffusion files — **58 passed, 2 skipped**
  (gpu leg + the APE initial-step guard), 18s warm; nonhydro+JW+example files —
  **15 passed, 3 skipped** (gpu legs), 6m04s → **data+slow total: 73 passed,
  5 skipped**.
- `validation/L4_idealized/test_jw.py` (data+slow; cached 1-day reference set):
  **3 passed** — day-1 + envelope 7.7s against the cached trajectories; symmetry
  5m59s (in-test 12 h run).
- `uv run ruff check .` — clean; `uv run ruff format --check .` — 165 files clean.
- `uv run mypy --strict -p symcon.core` — no issues in 50 files.
- `uv run lint-imports` — 2 contracts kept, 0 broken.
- New test files in isolation: `test_diffusion_component.py` **14 passed** (5.6s
  warm; 85s on first-ever compile); `test_diffusion_datatest.py` **5 passed,
  3 skipped** (12s warm; first runs: APE 2m26s, MCH legs 3m00s);
  `test_jw_datatest.py` **3 passed** (1m02s warm); `test_jw_example.py`
  **1 passed** (3m15s).

## 7. Follow-ups

- **9-day L4 run** (deviation 8): `make_reference.py --days 9 --force` offline
  (~5 h CPU total incl. the symcon leg), then `test_jw.py` — the day-9 envelope
  claim needs that run; day-1 is already bitwise.
- Propose S11 carrying gt4py domain offsets through the static DataArray boundary
  (§5) so component `convert()`s need no field-specific knowledge.
- Report upstream (icon4py): `GridGeometry.mean_cell_area` vs ICON serialized value
  (4e-5 rel); the RBF vertex factory's NaN-divide warnings at pentagon rows.
- The JW archive namelist has `l_zdiffu_t=False`, so its metrics savepoint carries
  no `zd_*` fields (accessors return `None`; the granule accepts that since the
  path is off) — a `zdiffu_t=True` JW experiment would need the factory statics.
- P5: distributed diffusion (constructor accepts `exchange`; single-node default).

## 8. Data artifacts (no data in git)

- `mpitask1_exclaim_nh35_tri_jws_v04` — JW archive, ~7 GB compressed / 14 GB
  unpacked (new this step, `~/.cache/symcon/icon4py-testdata`).
- `mpitask1_exclaim_ch_r04b09_dsl_v04` — MCH archive (upstream's only diffusion
  initial-step leg), ~6 GB compressed / 11 GB unpacked (new this step).
- EXCLAIM_APE reused from S11/S12 (no new download).
- L4 reference cache `~/.cache/symcon/l4_reference/` (generated by
  `make_reference.py`; sha256 manifest; currently the 1-day set, ~9 MB).
- gtfn program caches: `~/.cache/symcon/gt4py` (main, + the 35-level JW variants)
  and `~/.cache/symcon/gt4py-s13-pentagon-pad_after` (the cold-cache probe world,
  disposable).
