# S07 — STATUS

## What was built

- **`symcon/core/ingress/gt4py.py`** (new package `symcon.core.ingress`): the S07
  backend object. `Backend` bundles the gt4py program processor (`None` = embedded,
  the gt4py/icon4py convention), the buffer allocator, the zero-copy
  `as_field(dims, buffer)` ingress and the offset-provider hook (empty mapping for the
  column). Frozen interface `make_backend(name) -> Backend` maps the S03 strings
  (`embedded`/`gtfn_cpu`/`gtfn_gpu`); `resolve_backend(str | Backend)` is the
  component-side convenience. Exported from `symcon.core` as `Backend`/`make_backend`.
- **`ComputeContext` extension** (sanctioned by SPEC S07 "extend the ComputeContext
  backend from opaque string to a small backend object"): `backend` now accepts
  `str | Backend`; a `Backend` contributes its own allocator; new `backend_name`
  property. The S03 opaque-string path is byte-for-byte unchanged (covered by
  the pre-existing suite plus `test_compute_context_string_path_unchanged`).
- **`symcon/icon/components/fast/satad.py`**: `SaturationAdjustment(Stepper)` wrapping
  the icon4py saturation-adjustment granule (microphysics package, pinned v0.2.0) —
  the T-based formulation (`temperature`/`qv`/`qc`/`rho`), chosen because it is the
  variant with serialized ICON reference data (PLAN pitfall; choice recorded in
  REFERENCES.lock `icon4py-satad`/`icon4py-muphys-satad`). cvd bookkeeping confirmed
  against `mo_satad.f90` (`lwdocvd = L_v(T)/cvd`) — no cpd conversion anywhere.
  - Frozen ctor `SaturationAdjustment(grid_or_column, cfg, ctx)`; `grid_or_column` is
    the S06 `VerticalGrid` (column path: a trivial pointwise icon4py grid is built
    lazily around the horizontal extent discovered from the state) or an
    `(icon4py_grid, icon4py_vertical_grid)` pair (host-grid path, used by the L2
    datatest to run exactly as icon4py's own integration test).
  - `array_call` = zero-copy gt4py views of the boundary buffers → `granule.run(...)`
    *as icon4py's test invokes it* → `x_new = x + (dx/dt)·Δt` into the caller's output
    buffers (icon4py's own verification arithmetic). Private tendency fields are
    zeroed per call so levels above `kstart_moist` (and halo-excluded cells) come out
    exactly unchanged.
  - Contracts: in `air_temperature`/`specific_humidity`/`specific_cloud_content`/
    `air_density`, out the first three adjusted; `differentiable: "custom"` declared
    on the outputs (rules deferred to S10). `coupling_constraints.admissible_operators
    = {"sequential_update_splitting"}` per tutorial §3.7.2 (satad appears twice in the
    fast-physics SUS chain; REFERENCES.lock `icon-tutorial-2025`).
  - `SaturationAdjustmentConfig(max_iter=10, tolerance=1e-3)` transcribed from icon4py.
- **Dependencies** (no pin changes): `icon4py-atmosphere-microphysics>=0.2.0` added to
  `symcon-icon` (already a member of the pinned 0.2.0 set via the datatest extra; the
  component makes it a runtime dependency). `symcon-core` gains an optional
  `gt4py` extra (`gt4py>=1.1.10`, the exact pin lives in `constraints/`); the ingress
  module imports gt4py lazily, so symcon-core still works without it.

## Acceptance criteria → tests

1. **L2 parity** — `packages/symcon-icon/tests/test_satad_datatest.py` (marker
   `data`): WEISMAN_KLEMP_TORUS satad-init/satad-exit savepoints (the only archive
   carrying them; GAUSS3D has none, so the S06 default experiment is overridden for
   this file), 2 locations × 3 dates × {embedded, gtfn_cpu} = 12 cases, at icon4py's
   own tolerances `rtol=1e-12` (dallclose default), `atol=1e-13` (their explicit
   argument) — provenance comments at the constants. All 12 pass locally.
2. **Zero-copy** — `test_ingress_gt4py.py::test_as_field_is_zero_copy_{numpy,cupy}`
   (`field.ndarray is buf`; cupy under `gpu` marker) plus the component-path identity
   check in `test_satad_component.py`.
3. **Fixed point** — `test_fixed_point_idempotence` (atol contract 1e-12; observed
   ≤ 1e-19 on all three fields).
4. **Standalone Fig.-1** — `test_standalone_fig1_pattern` on the S06
   `moist_test_column` (qv boosted ×3 to force supersaturation), embedded + gtfn_cpu
   (+ gtfn_gpu under `gpu`).
5. **out= path** — `test_out_path`: caller-provided DataArrays come back identically
   (object and buffer identity) with values equal to the allocate path.

Additional: L0 physics checks against the *mined* closures (total-water conservation;
qv_adjusted = qsat_rho(T_adjusted) on condensing points; latent-heat/cvd energy
closure), kstart_moist no-op check, SUS-accepts/parallel-splitting-rejects
constraint test, config-transcription test.

## Deviations / disagreements

- **ICON Fortran vs icon4py** (recorded per AGENTS.md; icon4py serialized data is the
  verification target): `mo_satad.f90` at icon-2026.04-public adds a parameterized
  supersaturation factor (`tune_supsat_limfac`, default path `supsatfac = 1`) and
  takes `w` as an input; the icon4py v0.2.0 granule has neither. With the default
  namelist both reduce to the same algorithm; the symcon component follows icon4py
  (no `w` input). Also: ICON caps the Newton loop silently at `maxiter`; icon4py
  raises `ConvergenceError` — the component lets that exception propagate.
- **S06 flag on `SPECIFIC_HEAT_CAPACITY_ICE` (2108.0 vs Fortran ci=2106.0)**: checked —
  satad uses no ice heat capacity anywhere (no `cpi` term in the granule or in
  `mo_satad.f90`), so the disagreement does not touch S07. It remains live for S08
  (graupel).
- **`gtx.as_field` is not zero-copy** (architecture §2.3 sketches it as the ingress):
  gt4py 1.1.10 deliberately always allocates in `as_field` ("we do not support a
  'copy' argument…"). `Backend.as_field` therefore wraps buffers through the
  singledispatch `gt4py.next.common._field`, which aliases (verified by test).
  Private-API risk: flagged as follow-up.
- **Friend access to `VerticalGrid._i4_grid`**: the column path needs the icon4py
  vertical-params adapter the S06 grid already holds. S06 interfaces are frozen, so
  instead of adding a public accessor the component (same distribution) reads the
  private attribute with a comment. Proposal for trunk: expose it as a public
  read-only property on `VerticalGrid` in a later step.
- The datatest state builder copies savepoint fields into fresh numpy buffers
  (`ascontiguousarray`) — that is *state construction* (like the S06 builders), not
  component ingress; the component path itself stays zero-copy.

## Follow-ups

- S10: actual `custom` differentiation rules for the satad fixed point
  (implicit-function treatment, architecture §8.6).
- Replace `gt4py.next.common._field` with a public zero-copy constructor if/when
  gt4py grows one (re-check at any gt4py bump — trunk decision anyway).
- Expose the icon4py vertical adapter publicly on `symcon.icon.grid.VerticalGrid`.
- The trivial pointwise host grid (`_column_icon4py_grid`) is satad-local for now;
  S08 (graupel — also pointwise per column) will likely want it shared; hoist to a
  common module when the second consumer lands.
- gtfn_cpu first-call compile of the 4 granule programs costs ~20 s per fresh gt4py
  cache; acceptable for the gate, worth persistent-cache attention when more gt4py
  components accumulate.

## Artifacts / gate results (local)

- `uv run pytest packages -m "not gpu" -q` — **491 passed, 1 skipped** (mpi opt-in),
  11 deselected (data/gpu), 89.7 s.
- `uv run pytest packages/symcon-icon -m data -q` — **14 passed** (12 new satad L2
  cases + 2 S06 vertical-grid), 34.9 s. WK-torus archive (~1.6 GB) downloaded once
  into `~/.cache/symcon/icon4py-testdata` via icon4py's own machinery; no data in git.
- `uv run ruff check .` / `uv run ruff format --check .` — clean.
- `uv run mypy --strict -p symcon.core` — clean (45 files).
- `uv run lint-imports` — 2 contracts kept.
