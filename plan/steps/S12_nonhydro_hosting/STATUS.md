# S12 — STATUS

**Branch:** `step/S12-nonhydro-hosting` · **State:** DRAFT (gates pending)

## 1. What was built

`symcon/icon/components/dycore.py` — `NonhydroSolver(DynamicalCore)`: the icon4py
nonhydrostatic solver + velocity advection hosted as **one** symcon component
(wrap-don't-rewrite, §4.4: the ~50 predictor/corrector stencil programs stay icon4py
granule internals; symcon invokes `run_predictor_step`/`run_corrector_step` exactly
as icon4py's own integration tests and driver do — REFERENCES.lock
`icon4py-solve-nonhydro`, `icon4py-solve-nonhydro-tests`,
`icon4py-driver-dyn-substepping`).

- **Component boundary.** Prognostics in/out on their locations: `icon:normal_wind`
  (edge×K), `upward_air_velocity_on_interface_levels` (cell×K+1), `air_density`,
  `icon:exner_function`, `icon:virtual_potential_temperature` (cell×K). Bus inputs
  `icon:ddt_vn_phy` (new registry row, m s-2) and `icon:ddt_exner_phy`, declared via
  `tendency_port` and **zero-filled by `__call__` when absent** (the S13 JW run needs
  no physics). Constructor `NonhydroSolver(grid, vgrid, static, cfg, ctx, *,
  substeps, ratio_provider, fast_tendency_component, edge_geometry, cell_geometry,
  owner_mask, exchange, name)`: `grid` is a symcon `IconGrid` (production path —
  geometry/owner mask derived from `icon4py_geometry`/`decomposition_info` per the
  icon4py standalone-driver recipe) or a raw icon4py grid (host-grid path, geometry
  passed explicitly — how the parity tests mirror upstream).
- **Static-state enumeration (the S11 coordination point).**
  `STATIC_METRIC_FIELDS` (32) / `STATIC_INTERPOLATION_FIELDS` (16) map every icon4py
  `MetricStateNonHydro`/`InterpolationState` field to its S11 registry name;
  coverage of both dataclasses is asserted exactly in tests, and every name is
  produced by S11 `metrics()|interpolation()`. Entries may be S11 DataArrays
  (converted onto the component's backend) or ready icon4py fields (savepoint path,
  zero conversion).
- **Config.** `NonhydroConfig` mirrors the slice-relevant ICON namelist knobs
  (`itime_scheme`, `iadv_rhotheta`, `igradp_method`, `rayleigh_type`,
  `divdamp_order/type/fac..fac4/z..z4`, `ndyn_substeps(+max)`, `rhotheta_offctr`,
  `veladv_offctr`, `lextra_diffu`, `nudge_max_coeff`, `lvert_nest`, `ldeepatmo`,
  IAU flag) with `icon_namelist_origin` dataclass-metadata annotations
  (machine-readable via `icon_namelist_origins()`), plus two declared
  runtime-derived knobs (`second_order_divdamp_factor` = ICON's spinup-ramped
  `divdamp_fac_o2`, fixed per run in this slice; `prepare_advection` = `lprep_adv`).
  `to_icon4py()` re-runs the granule's own slice validation at construction;
  defaults are asserted equal to icon4py's in tests.
- **Substep tier.** Fixed ratio (default `cfg.ndyn_substeps`) + `ratio_provider`
  hook (S04 semantics, called once per step), bounded by `ndyn_substeps_max` (ICON's
  CFL escalation cap, 12). CFL exposure for adaptive providers is **stubbed to the
  fixed ratio in this slice (declared, per SPEC)**: the carry `max_vertical_cfl`
  (ICON `max_vcfl_dyn`) is serialized and readable via the `max_vertical_cfl`
  property, but no CFL-adaptive provider ships until the diagnostics land.
- **Time-level privacy + restart/functional protocols.** Two private prognostic
  buffer sets (icon4py `TimeStepPair`), swapped internally per substep; single-level
  state at the boundary. `restart_state()` = both time levels + the
  velocity-advection carry (ddt_vn_apc / ddt_w_adv predictor–corrector pairs, vt,
  vn_ie, w_concorr_c, theta_v_ic, rho_ic, exner_pr, mass_fl_e, exner_dyn_incr,
  max_vertical_cfl), prep-advection accumulators, the 7 predictor→corrector
  intermediates (z_*), and substep bookkeeping (36 keys). `functional_state()`
  declares the same schema as `PropertySpec`s (F-tier consumption is P6).
  `load_restart_state` is strict (full schema, no extras) and doubles as the
  savepoint-carry ingestion path of the parity tests. Cold start initializes
  `exner_pr = exner − exner_ref_mc` (mo_nh_stepping.f90 l.396-400).
- **Names registry:** one new row `icon:ddt_vn_phy` ("m s-2", ICON `ddt_vn_phy`).

Tests: `tests/test_nonhydro_component.py` (17 tests, stubbed granule on the icon4py
`SimpleGrid` — config/static/restart contracts, acceptance-2 hook-order recording,
bus plumbing, fast tier, standalone call) and `tests/test_nonhydro_datatest.py`
(11 collected, markers `data`+`slow` — savepoint parity, restart bitwise, bus
linear-response; details in §3).

## 2. Deviations (and why)

1. **Tier nesting: `array_call` overridden (S04 base orchestration not used).**
   The S04 `DynamicalCore` unrolls Fig. 3.10 *stage-outer* (each stage runs its own
   substep block). ICON nests the other way: each of the `ndyn_substeps` substeps
   runs the full predictor→corrector pair
   (`mo_nh_stepping.f90::perform_dyn_substepping`; icon4py driver
   `_do_dyn_substepping`). `NonhydroSolver` therefore overrides `array_call` — the
   method the base class itself designates as "tier orchestration" — while keeping
   the frozen S04 subclass hooks (`substep_array_call(stage, substep, …)` = one
   stage of one substep; `stage_array_call` = its degenerate single-substep form).
   No S04 code or interface was changed. **Proposal for the architecture doc /
   trunk:** the DynamicalCore contract should name the substep-outer nesting as a
   sanctioned variant (ICON's own semantics), e.g. via an overridable
   `tier_nesting` class attribute; recorded here rather than silently resolved.
2. **Hook data flow is via private state (`communicates_internally=True`).** The
   S04 hook docstrings say hooks receive raw buffers; the hosted granule reads and
   writes the component-private icon4py state objects instead, and `array_call`
   ingests/egresses the boundary buffers once per step. Declared in the class/module
   docstrings; the buffers are still passed to the hooks (informational).
3. **No `embedded` backend leg in the savepoint parity matrix** (SPEC acceptance 1
   says "backends embedded + gtfn_cpu"). Upstream icon4py **xfails every
   solve_nonhydro integration test on embedded** ("Embedded backend currently fails
   in remap function", `icon4py.model.testing.filters` at v0.2.0) — the donor cannot
   produce embedded reference behavior for these fused stencils. Parity runs on
   gtfn_cpu, with gpu-marked gtfn_gpu legs that skip cleanly without a device.
4. **Multi-substep tolerances reused from an MCH-only upstream test.** Upstream
   `test_run_solve_nonhydro_multi_step` (the only test of the full N-substep loop)
   runs for MCH_CH_R04B09 only ("# why is this not run for APE?" upstream); its
   per-field tolerances are reused verbatim for the EXCLAIM_APE multi-substep parity
   here. The single-substep / predictor / corrector tests use the EXCLAIM_APE-native
   upstream legs and tolerances. No tolerance was loosened.
5. **`visit()` compiles as an opaque Stepper op.** `visit_dynamical_core` would
   unroll the (wrong for ICON) stage-outer tiers; until S14 teaches the plan
   compiler the ICON nesting, the component presents itself as one opaque
   `array_call` op (`communicates_internally=True` justifies the coarse granularity;
   the S05 semantics of a fixed ratio are preserved; adaptive `ratio_provider` under
   `tier="plan"` is declared unsupported until S14).
6. **Parity tests touch two private members** (`solver._load_bus(...)` to stage bus
   values without a full `__call__`, and `solver._current_call_substeps = 2` to
   replicate upstream's "one substep with ndyn_substeps_var=2" invocation). These
   replicate icon4py's own sub-step-level test entries, which have no public symcon
   equivalent by design (the public boundary is the full Δt).
7. **Restart schema scope.** `grf_tend_*` (LAM nesting inputs) and the IAU increment
   fields are *not* serialized: they are external inputs (zeroed; IAU is
   config-rejected in this slice), not private carry. The z_* intermediates *are*
   serialized (cheap relative to a mid-experiment bitwise guarantee and needed by
   the corrector-only parity replay).

## 3. Acceptance criteria → tests

| # | Criterion | Test |
|---|---|---|
| 1 | Savepoint parity at icon4py tolerances, first + mid-run timestep, single + multi substep, gtfn_cpu + gpu-marked gtfn_gpu | `test_nonhydro_datatest.py::test_full_timestep_multi_substep_parity[first/mid-run]`, `::test_single_substep_parity`, `::test_predictor_stage_parity`, `::test_corrector_stage_parity` (tolerances cited per field, per upstream test) |
| 2 | Hook-order vs hand-written ICON sequence (ndyn_substeps=2), velocity-advection reuse per icon4py flags | `test_nonhydro_component.py::test_hook_order_matches_icon_sequence_for_two_substeps` (stub granule, initial + subsequent step) + the velocity-advection invocation recording inside `test_full_timestep_multi_substep_parity` (real granule, data) |
| 3 | Restart: 5 → serialize → restore → 5 ≡ 10 straight, bitwise fp64 | `test_nonhydro_datatest.py::test_restart_bitwise_reproducibility` |
| 4 | Constant `ddt_vn_phy` shifts vn by ≈ Δt·c | `test_nonhydro_datatest.py::test_bus_constant_vn_tendency_linear_response` (2% smoke bound, documented in-test) |
| 5 | Standalone, federation-free construct + call | `test_nonhydro_component.py::test_standalone_call_without_federation` (+ every datatest drives the bare component) |

## 4. Gates

(to be filled with final numbers)

## 5. Follow-ups

- S14: teach the plan compiler the ICON substep-outer nesting (deviation 1/5) and
  decide plan-tier semantics for adaptive `ratio_provider`.
- CFL-adaptive `ratio_provider` preset (`cfl_adaptive(base, max_ratio)` of §5.1)
  once the velocity-advection CFL diagnostics are exposed per substep.
- Consider a public constructor path that builds the static mapping internally from
  `metrics(grid, vgrid) | interpolation(grid)` when `static is None`.
- P5: distributed `exchange` (constructor already accepts one; single-node default).
