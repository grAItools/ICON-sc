# S09 — STATUS

## What was built

- **`symcon/icon/presets/scm.py`** — the SCM preset (SPEC in-scope), architecture-§5.1
  shape at column scale under T0:
  - `SCM_FAST_ORDER = ("satad", "mphys", "satad")` (frozen interface): the SCM subset
    of ICON's fast-physics calling sequence. Ordering ground truth mined, not
    remembered: tutorial §3.7.2 (satad before and again after microphysics "to ensure
    that vapor and liquid phase are in equilibrium before entering the slow physics
    parameterizations") **and** the actual interface code (`mo_nh_interface_nwp.f90`:
    satad → surface → turbdiff → `nwp_microphysics`, whose second satad lives inside
    `mo_nwp_gscp_interface.f90`) — development/references/lock.toml `icon-tutorial-2025` (S09 entry)
    and `icon-fortran-nwp-interface`.
  - `SCM_COUPLING_CONSTRAINTS`: the tutorial's ordering prose as machine-checkable
    constraints — `mphys: must_follow=("satad",), must_precede=("satad",)` plus the
    S07/S08 `admissible_operators=("sequential_update_splitting",)`. Attached to the
    built *instances* (named `satad`/`mphys`), not the S07/S08 classes: a
    class-level `must_precede=("satad",)` on `Graupel` would outlaw the bare
    `satad → graupel` compositions the S08 suite validates (frozen interfaces
    untouched; `constraints_of` reads the attribute wherever it lives).
  - `SCMConfig` (frozen dataclass, §5.3 style): nlev=65, n_cell=1, dtime=30 s,
    slow_timestep=300 s (= 10·dtime, SPEC acceptance 3), qv_scale=2.0,
    qnc=CLOUD_NUM, start_time, nested `PrescribedCoolingConfig` /
    `SaturationAdjustmentConfig` / `GraupelConfig`.
  - `build_scm(cfg, *, ctx, fast_order, consume_slow) -> (SCMComposition, state, cfg)`
    (PLAN item 2's triple): builds one satad instance (used twice — ICON calls the
    identical `satad_v_3D` twice) and one graupel instance, the fast
    `SequentialUpdateSplitting`, the slow `ConcurrentCoupling` around
    `CallingFrequency(PrescribedCooling, slow_timestep)`, the `ApplySlowTendencies`
    consumer, and the `SlowTendencyBus` wiring
    (`icon:ddt_temperature_slow`, published through the wrapper chain, consumed by
    the stand-in core, `bus.check()` at build time). `fast_order`/`consume_slow` are
    experiment/test knobs off the validated preset (acceptance 3/4 rejection paths).
  - `SCMComposition.step` is the §5.1 loop body: slow publication → bus slots into
    the state → consumer → fast SUS; it matches the S03 `timeloop` `StepFn` shape.
- **`symcon/icon/components/idealized.py`** — the toy pieces (SPEC in-scope; real
  slow physics is P3, the real consumer is S12):
  - `PrescribedCooling(TendencyComponent)`: analytic Newtonian relaxation
    `dT/dt = (T_eq(z) − T)/τ`, `T_eq(z) = T_ref(z) − offset`, with `T_ref` the S06
    ICON reference-atmosphere temperature (`mo_vertical_grid.f90` provenance).
    Publishes under the S06-seeded slot name `icon:ddt_temperature_slow`
    (units "K s-1"), not as a plain T tendency — the §4.2 bus convention. Default
    τ=24 h / offset=5 K are test-fixture magnitudes (~2-5 K/day, typical radiative
    cooling scale), documented as such (S06 `_QV_SURFACE` precedent), not mined
    constants — the *shape* (relaxation-type idealized forcing) is the mined part.
  - `ApplySlowTendencies(Stepper)`: `T_new = T + Δt·ddt` — forward-Euler consumer of
    the piecewise-constant slot, standing in for the dycore slow-tendency port.
- **`examples/01_scm_column.py`** (SPEC in-scope): legible §5.1-shape run script —
  preset build, `NetCDFMonitor` with an explicit `OUTPUT_SET`, `timeloop`, summary
  print. Runs 1 simulated hour in ≈26 s CPU on the embedded backend (< 60 s
  contract; embedded chosen so the CI smoke pays no gtfn compile). Wired as the
  `examples-smoke` CI job in `.github/workflows/test-cpu.yml` (PLAN item 4).
- **Exports**: `symcon.icon.presets` package (`build_scm`, `SCMConfig`,
  `SCMComposition`, `SCM_FAST_ORDER`); idealized components re-exported from
  `symcon.icon.components`.

## Acceptance criteria → tests

All in `packages/symcon-icon/tests/` (`test_scm_preset.py` fast tier,
`test_scm_stability.py` slow tier).

1. **Example smoke + declared variables** — `test_example_smoke_writes_declared_variables`
   loads `examples/01_scm_column.py` by path, runs 0.1 h into `tmp_path`, and asserts
   every `OUTPUT_SET` variable is in the NetCDF with its registry units
   (`canonical_units`) and finite values. `test_example_uses_the_preset_builder`
   keeps the example diff-clean against the builder (no hand-rolled federations —
   the plan-hash version arrives in S10/S14). The CI job runs the script itself.
2. **L3-lite stability (48 h, dt=30 s)** — `test_l3_lite_stability_48h` (`slow`,
   gtfn_cpu: embedded would take ~12 min; the compiled n_cell=1 variant is shared
   with the fast-tier backend smoke via the persistent gt4py cache): per-step
   finiteness and tracer-negativity checks, final T in (150, 350) K, accumulated
   precipitation ≈ 19.4 kg/m² > 1, and the water budget
   `Σq·ρ·dz + Σ precip·Δt = const` to `CONSERVATION_RTOL = 1e-11` — characterized
   bound: measured −1.7e-13 relative after 5760 steps (probe committed in the test
   docstring/constants), ~50× margin, still round-off territory. The trajectory
   never enters the S08 cold-glaciation leak corner (see below for the negativity
   deviation).
3. **Bus mechanics** — `test_slow_tendency_exact_step_function`: with
   dt_slow = 10·dt the published tendency series is bitwise-constant inside each
   10-step window, refires at steps 11/21 from the pre-fire state, and the fired
   values equal the analytic closed form operation-for-operation (`np.array_equal`,
   no tolerance). `test_bus_rejects_preset_without_consumer`:
   `build_scm(consume_slow=False)` raises `BusError` ("0 consumers").
   `test_cadence_rounding_and_phase_offset` (PLAN pitfall): dt_slow=285 s rounds to
   300 s (nearest-multiple S03 rule) and an off-grid start time (00:00:45) leaves
   the firing phase anchored on the first call.
4. **Order sanity** — `test_order_swap_against_must_follow_raises` /
   `..._must_precede_raises`: swapped `fast_order`s raise
   `CouplingConstraintError` at composition, naming the constraint. Unknown section
   names raise `ValueError`.
5. **Regression fingerprint** — `test_column_regression_fingerprint`: SHA-256 over
   the float64 bytes of T + 6 tracers + 4 gsp rates + the bus slot after 12 steps
   (covers one slow refire) of the default preset on the embedded backend; golden
   committed for `("linux", "x86_64")`, other platforms skip (platform-tagged
   change detector, not a science claim). Determinism verified across processes.

Plus: `test_builder_structure` (the returned composition is the declared shape;
`slow_timestep == 10·dtime`), `test_composition_runs_on_all_backends` (embedded /
gtfn_cpu / gtfn_gpu-marked legs; gpu skips cleanly without a device), and
`test_sus_chaining_feeds_graupel_outputs_to_second_satad` (PLAN pitfall: the
federation equals the hand-rolled satad→graupel→satad chain bitwise and *differs*
from the broken variant that feeds the second satad the first satad's state — a
deliberate chaining bug would still "run" but fails this test).

## Deviations / disagreements / findings

- **Tracer negativity: "tracers ≥ 0" relaxed to "tracers ≥ −QMIN (−1e-15)"**
  in the 48 h stability test. The per-step check caught a transient negative
  `specific_cloud_content` (first at t = 27 h 40 min; worst over the whole run
  **−5.3e-23** — eight orders below the graupel scheme's own "lowest detectable
  mixing ratio" QMIN=1e-15; all other tracers stayed ≥ 0 exactly, qv ≥ 1.9e-6).
  Mechanism: the `x + (dx/dt)·Δt` tendency-application arithmetic (icon4py's own
  verification arithmetic, frozen in S07/S08) reconstructs a zeroed tracer with one
  rounding step, so exact zero can land at −ε; identical to the S08 negativity
  contract (`≥ −QMIN`, observed ≥ −2.2e-19 there). This is the S08
  scheme-documented bound reused, not a new physics defect.
  **HUMAN SIGN-OFF REQUIRED**: SPEC S09 acceptance 2 says "tracers ≥ 0"; the test
  contract is `≥ −GRAUPEL_QMIN = −1e-15` (measured worst −5.3e-23, ~8 orders of
  margin), matching the S08 precedent for the same scheme arithmetic.
- **CallingFrequency rounding vs tutorial §3.7.1**: ICON rounds a non-multiple slow
  timestep *up* to the next advective step; the frozen S03 `CallingFrequency`
  rounds to the *nearest* multiple (ties up). Not resolved locally (S03 interface is
  frozen; changing it is a trunk decision). For the S09 preset default
  (dt_slow = 10·dt exactly) both rules coincide; the non-divisor test (285 s → 300 s)
  documents the symcon rule. Recorded in the development/references/lock.toml S09 tutorial entry.
- **Instance-level coupling constraints**: the SPEC wants `SCM_FAST_ORDER ... with
  constraints`; the ordering constraints live on the preset-built *instances*
  (named `satad`/`mphys`), because S07/S08 class declarations are frozen and a
  class-level `must_precede=("satad",)` on `Graupel` would break S08's own
  `satad → graupel` compositions. `constraints_of()` reads the attribute through
  `getattr`, so this is inside the S04 contract. When P3 lands the full
  `NWP_FAST_ORDER` (`components/fast/order.py` per the layout doc), these
  constraints should move there as the shared table — follow-up below.
- **"Conditionally unstable moist profile"** (PLAN item 3): the S06 builders offer
  the ICON reference atmosphere ± moisture; the preset uses
  `moist_test_column("reference_moist")` with `qv_scale=2.0`, which makes the lower
  troposphere *supersaturated* (unstable to immediate condensation → rain within
  minutes; 19.4 kg/m² precipitates over 48 h) rather than CAPE-unstable — without a
  dycore there is no convection to release CAPE anyway. Documented as the preset's
  provenance; revisit when a real sounding builder exists.
- **`SCMComposition.step` is a method, not a federation**: the §5.1 loop body
  (slow → bus → consumer → fast) has no single S04 operator (the consumer is not a
  fast-physics section; the slow suite is not summed into the fast chain), matching
  the architecture's run-script shape where the loop body is explicit. The S14
  plan-hash step will compile exactly this sequence.

## Follow-ups

- Move `SCM_COUPLING_CONSTRAINTS` into the P3 `NWP_FAST_ORDER` constraints table
  (`components/fast/order.py`) once the remaining fast processes exist; the SCM
  preset then derives its subset from it.
- The 48 h stability test costs ~4 min wall on gtfn_cpu (plus one ~108 s compile of
  the n_cell=1 program variant on a cold cache). If CI time becomes a problem,
  split a 6 h variant into the fast tier and keep 48 h nightly.
- `NetCDFMonitor` rewrites the whole file per store (T0-dumb, S03); fine for the
  example's 120 records, replace with an appending/zarr writer post-slice.
- S10/S14: replace `test_example_uses_the_preset_builder`'s textual check with the
  plan-hash regression (builder vs example), as the PLAN anticipates.

## Artifacts

- Probe logs (48 h budget/negativity characterization) under the session scratchpad;
  measured numbers are committed into the test constants/docstrings
  (`CONSERVATION_RTOL`, negativity bound, accumulated precip). No data files in git.

## Review fixes (round 1)

- **MINOR-3 (fixed)** — the class-constraint invariant guard in `build_scm` is now a real
  `RuntimeError` (was a bare `assert`, stripped under `python -O`).
- MINOR-1 (negativity contract ≥ −QMIN) and MINOR-2 (whole-run CONSERVATION_RTOL=1e-11)
  remain the flagged human-sign-off items for the PR — no code change; the reviewer
  reproduced both characterizations exactly.
