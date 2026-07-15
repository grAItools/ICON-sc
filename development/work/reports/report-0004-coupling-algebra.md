# S04 — Status

**Branch:** `step/S04-coupling-algebra` · **State:** implemented, gate green, ready for PR.

## What was built

- `symcon/core/coupling/concurrent.py` — `ConcurrentCoupling(comps)`: tendency
  summation, diagnostics union, serial chaining (each member sees its
  predecessors' diagnostics — tasmania's `serial` policy, the only one ported);
  itself a tendency-kind component (nests, wraps, feeds steppers); restart /
  functional-state delegation to members.
- `symcon/core/coupling/steppers.py` — two S02 `Factory` roots,
  `TendencyStepper` and `SequentialTendencyStepper`, each registering
  `forward_euler`, `rk2` (Heun), `rk3ws` (Wicker–Skamarock), `ssprk3`
  (Shu–Osher). `TendencyStepper.factory(name, coupling)` per the frozen
  interface; couplings may be bare tendency components. The sequential root
  implements the frozen two-state signature `E(ψⁿ, Δt; P + (ψ_prov − ψⁿ)/Δt)` by
  adding the provisional forcing to every tendency evaluation — algebraically
  identical to tasmania's fused `sts_rk2_0` / `sts_rk3ws_0` first-stage ops.
- `symcon/core/coupling/federations.py` — `ParallelSplitting(sections)` with the
  per-field `Σψₗ − L·ψⁿ` recombination (thesis eq. 2.10d);
  `SequentialTendencySplitting(sections)` (first section stepped plainly per
  eq. 2.11a; later sections are SequentialTendencySteppers forced **from the
  step-initial ψⁿ**); `SequentialUpdateSplitting(sections)` accepting bare
  `Stepper`s or `(TendencyComponent, stepper_name)` pairs;
  `SSUS(sections, core, lam=0.5, pre_steppers=None)` built from two SUS passes
  (reverse order over λΔt first, core over Δt, forward order over (1−λ)Δt,
  per-side steppers per thesis §2.3.5). Every federation is Stepper-shaped and
  composable (a SUS can be an SSUS core — tested).
- `symcon/core/coupling/bus.py` — `TendencySlot` + `SlowTendencyBus`
  (declare/publish/consume validated against component property dicts;
  `check()` enforces exactly-one-consumer and no consumed-but-unpublished
  slots). `symcon/core/coupling/constraints.py` — `CouplingConstraints`
  (`must_follow`/`must_precede`/`admissible_operators`) read from a
  `coupling_constraints` attribute and validated when a federation is
  constructed (PS checks admissibility only: order carries no semantics there).
- `symcon/core/components/dycore.py` — `DynamicalCore(Component)`: slow-tendency
  input port as `input_properties` slots mapped via a `tendency_port` class
  attribute and held constant across the step; optional per-stage
  `fast_tendency_component: ConcurrentCoupling` evaluated once per stage on the
  latest provisional state and summed onto the slow values in per-stage scratch
  buffers; super-fast substep tier (`substeps` static or `ratio_provider`
  adaptive, called once per step — Subcycle's semantics) with per-stage counts
  `max(1, round(substep_fraction[s]·N))` and substep dt `Δt/N` (Fig. 3.9/3.10).
  Subclass contract exactly as frozen: `stage_array_call(stage, inputs,
  outputs, dt)`, `substep_array_call(stage, substep, inputs, outputs, dt)`,
  `n_stages`, `substep_fraction`.
- `symcon/core/coupling/dictops.py` — `dict_axpy`/`dict_fma` (PLAN item 3;
  numpy-level, S05 compiles them away). `symcon/core/testing/order.py` —
  `measure_order(builder, dts, exact)` + `OrderFit` (PLAN item 5; exported from
  `symcon.core.testing` for L7 reuse; `exact=None` = self-convergence pairs).

## Acceptance results

1. **ODE orders** (`test_order_ode.py`, closed form, Δt ∈ {T/64…T/1024}, T=1.024 s,
   ω=2π/T, τ₁=0.7, τ₂=0.15, ζ_eq=0.5−0.3i, RK2 everywhere): FC **2.03**,
   LFC **0.95**, PS **1.03**, STS **1.00**, SUS **0.97**, SSUS(λ=½) **1.99**,
   SSUS(λ=0.3) **0.98** — all within ±0.15.
2. **Burgers orders** (`test_order_burgers.py`, N=512, ν=2·10⁻⁴, τ=0.5,
   u₀=0.2·sin 2πx, u_eq=0.2·cos 2πx, T=0.128 s, self-convergence): FC **2.00**,
   LFC **1.00**, PS **1.00**, STS **1.00**, SUS **1.00**, SSUS(½) **2.00**,
   SSUS(0.3) **1.01**.
3. SUS `must_follow` violation raises `CouplingConstraintError` naming both
   components; bus `check()` rejects published slots with 0 or 2 consumers
   (`test_coupling_federations.py`, `test_coupling_bus.py`).
4. Recording toy core (2-stage, `substep_fraction=1/3`, `substeps=6`) produces
   the exact Fig. 3.10 hook order (`fast, stage, substep×2` per stage), slow
   port constant across stages, fast coupling once per stage; the literal
   Fig. 3.10 example (3 stages, fractions ⅓/½/1, N=6) yields 2/3/6 substeps
   (`test_components_dycore.py`).
5. `SSUS(..., pre_steppers=["forward_euler"])` with rk2 post steppers runs and
   provably differs from the symmetric-steppers variant
   (`test_ssus_pre_steppers_differ_from_post_steppers`).

Gate: `pytest -m "not gpu"` → **287 passed, 1 skipped (mpi), 4 deselected(gpu)**;
`ruff check` + `ruff format --check` clean; `mypy --strict -p symcon.core` clean
(36 files); `lint-imports` 2 contracts kept. Every new test file also passes in
isolation.

## Deviations (and why)

- **`rk2` is Heun, not tasmania's midpoint RK2.** SPEC S04 names "rk2 (Heun)"
  explicitly; tasmania's `rk2` is the Gear/midpoint variant. Heun == the 2-stage
  SSP RK in upstream sympl (cross-mined; development/references/lock.toml). Both are second
  order; the acceptance slopes are scheme-family invariants.
- **Stepper display names.** The S02 `Factory` contract owns the `name` class
  attribute (registration key), so stepper instances expose the scheme key as
  `.name` and a `label` property ("rk2(Relaxation)") for error messages —
  instance-level `.name` would collide with the frozen registry `ClassVar`.
- **`substep_fraction` semantics.** SPEC freezes the attribute but not its
  meaning; adopted tasmania's `substep_fractions` reading (per-stage fraction of
  the total substep count N; scalar broadcasts; substep dt = Δt/N), which
  reproduces Fig. 3.10 exactly. Acceptance 4's "substep_fraction=1/3" toy runs
  with `substeps=6` → 2 substeps/stage.
- **DynamicalCore fast coupling needs a `tendency_port` map.** The SPEC says the
  slow port is "declared via input_properties"; combining fast tendencies
  (keyed by prognostic name) with slow slots (keyed by state-slot name) needs
  the prognostic→slot association, so the base class takes it as a class
  attribute, validated at construction. Fast tendencies for unmapped fields
  reject with an actionable error.
- **STS rejects bare `Stepper`s past position 0.** Eq. (2.11b) requires the
  two-state signature; adjustment-type components without it belong in SUS.
  Position 0 (the dynamics, eq. 2.11a) accepts bare Steppers. Tasmania has no
  bare-stepper STS sections either (only diagnostics, which S04 defers — see
  follow-ups).
- **Burgers ladder floored at T/512.** T/1024 = 125 µs makes λ·Δt = 62.5 µs,
  which `timedelta` rounds to 62 µs; the broken Strang symmetry (λ_eff ≈ 0.496)
  measurably corrupts the SSUS(½) self-convergence at that rung (observed slope
  break; error jumped from 5.4e-9 to 3.0e-8). All retained rungs and both λ
  splits are exactly microsecond-representable. Acceptance 1's ladder is
  unaffected (T=1.024 s keeps every rung and both splits exact). Follow-up
  below: sub-µs timesteps are a real T0 driver limitation.
- **matplotlib added to the dev dependency group** (PLAN item 5 requires plot
  artifacts). Dev-only; not a gt4py/icon4py pin change. Plots land in the
  gitignored `development/work/reports/report-0004-coupling-algebra/artifacts/` and regenerate with
  the suite (tests skip cleanly if matplotlib is absent).
- **Diagnostics of a stepper are those of the first (ψⁿ) evaluation** (tasmania's
  convention); later stage evaluations feed the scheme only. Documented in the
  module docstring and asserted in tests.
- **SSUS constraint validation covers the forward order only** (review INFO 3).
  Constraints are validated on `[core, *sections]` under the `"ssus"` label; the
  pre-pass necessarily executes the sections *before* the core, in reverse —
  that inversion is inherent to SSUS symmetry (thesis eq. 2.13a–e), not an
  ordering violation, and is stated in the class docstring. Components that
  cannot tolerate running before the core should exclude `"ssus"` via
  `admissible_operators`.

## Review fixes (round 1)

- **MINOR 1 — constraints now bind through wrapper chains.**
  `validate_composition` matches `must_follow`/`must_precede` names against the
  *innermost* component of a `ComponentWrapper` chain (`_constraint_name` walks
  `.component`), so `CallingFrequency(Convection, …)` no longer sheds
  constraints declared against `Convection` (the S09/S12 slow-physics pattern).
  The reverse direction (a wrapped component carrying its own constraints)
  already worked via attribute delegation. Regression:
  `test_constraints_bind_through_wrappers` — both directions, violating order
  raises naming both components, correct order constructs, doubly-wrapped
  chains covered.
- **MINOR 2 — `dict_axpy`/`dict_fma` are no longer untested dead exports.** The
  PS recombination now accumulates `ψⁿ⁺¹ = Σψₗ − L·ψⁿ` through `dict_axpy`
  (option (a); PLAN item 3 as written), and both helpers gained unit tests
  (`test_coupling_dictops.py`: in-place buffer identity, shared-fields default
  with `time` excluded, explicit field selection, out-of-place `dict_fma`). The
  existing PS hand-check tests pin the numerics unchanged.
- **INFO 3 — recorded** above under deviations (SSUS forward-order validation).

## Follow-ups

- Diagnostic-component sections inside federations (tasmania supports them;
  the SPEC scoped sections to Steppers/pairs). Needed at the latest for the
  ICON preset's dyn→phy diagnostics if S09/S12 want them *inside* a federation
  rather than in the loop body.
- `timedelta`'s microsecond floor makes sub-µs (or non-µs-multiple) stage/split
  arithmetic lossy; the S05 plan compiler should carry dt as float seconds
  internally and only quantize at the driver boundary.
- Federation `parsed_properties` is an approximate union view (inputs net of
  earlier outputs); fine for wrapping/introspection at T0, but S05's negotiation
  should recompute exact aggregate contracts from the plan.
- The per-stage fast coupling receives a timeless state snapshot (no `time`
  key), so time-triggered wrappers (`CallingFrequency`) inside the fast slot
  would misbehave; acceptable at T0 (the ICON preset keeps the slot empty),
  revisit with S12 if per-stage physics experiments need cadence.
- `DynamicalCore` scratch buffers use `numpy.empty_like` (T0 numpy-level per
  PLAN); GPU-resident cores need allocator-aware scratch in S05/S12.

## Artifacts

- `development/work/reports/report-0004-coupling-algebra/artifacts/convergence_ode.png` (acceptance 1)
- `development/work/reports/report-0004-coupling-algebra/artifacts/convergence_burgers.png` (acceptance 2)

Both are gitignored (repo policy); regenerate with
`uv run pytest packages/symcon-core/tests/test_order_ode.py packages/symcon-core/tests/test_order_burgers.py`.

## References consulted

Appended to `development/references/lock.toml` at mining time: tasmania
`75b46ac0737c88ea201274692ab6883e803efb29` (federations, steppers + fused STS
stage ops, ConcurrentCoupling, DynamicalCore, DataArrayDictOperator), sympl
upstream `512809ef35d2daf898b8747a717271ed4d2b684d` (SSP RK 2/3-stage
coefficients), Ubbiali thesis (eqs. 2.8–2.13, Table 2.1 order clauses, §2.5.2
experiment design, §3.5 + Fig. 3.8–3.10 tier semantics).
