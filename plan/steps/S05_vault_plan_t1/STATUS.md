# S05 — StateVault, plan compiler, T1 interpreter — STATUS

**Branch:** `step/S05-vault-plan-t1` · **State:** complete, all gates green.

## What was built

- **`state/vault.py`** — `StateVault.from_state(state)`: dense slotted container
  (flat buffer list + interned `names` map + per-slot boundary metadata), zero-copy
  buffer adoption, stable `schema_hash`, `epoch` (out-of-band mutations) and
  `generation` (plan-internal swaps) counters. **`state/facade.py`** —
  `vault.facade()`: lazy `MutableMapping[str, DataArray]` with per-slot wrapper
  caching invalidated by `generation`; `__setitem__`/`__delitem__` bump `epoch`
  (staleness guard); in-place buffer writes stay legal and plan-preserving.
- **`plan/ops.py`** — exactly the six ops (`BoundCall`, `Swap`, `Axpy`,
  `DiffScale`, `CadenceMask`, `SegmentMarker`), flat NamedTuples with pre-bound
  references. Docstrings are normative (exact ufunc sequences; T2/T3 emitters and
  the bitwise contract are stated against them). `Axpy` is a k-ary
  assign-or-accumulate multi-axpy with an optional trailing divisor (the divisor
  exists because ssprk3's `(ψ + 2(ψ₂ + Δt·k₃))/3` is a division, and `x/3 ≠
  x·(1/3)` bitwise); `DiffScale` is the STS forcing `(ψ_prv − ψⁿ)/Δt`.
- **`plan/bind.py`** — `ExecutionPlan.bind(composition, schema, ctx)` (frozen
  interface): the §8.2 negotiation/execution split. Composition walk via the
  `visit(plan_builder)` double-dispatch protocol (PLAN item 3) added to every
  S03/S04 container; bind-time negotiation reuses S02/S03 `DynamicChecker` +
  `IngressPlan` (cached per occurrence). Dissolutions per §8.2: SUS flattens;
  PS → per-section provisional slots + one k-ary `Axpy` per field with the T0
  term order `(ψ_l1, +ψ_l2, −ψⁿ, +ψ_l3, −ψⁿ, …)`; STS → provisional slots (the
  ping-pong partner cells) + one `DiffScale` per stepped field per section;
  SSUS → reversed λΔt pre-list + core + forward (1−λ)Δt post-list with the exact
  T0 timedelta arithmetic (`dt*λ`, `dt − dt*λ`); `CallingFrequency` → cadence
  masks resolved into per-signature op lists, its cache living in persistent
  per-member tendency/diagnostic slots (replay = simply not rewriting them);
  `Subcycle` and the `DynamicalCore` stage/substep tiers unroll with bound dt;
  `ScalingWrapper` folds to constant-coefficient `Axpy`s. The four S04 stepper
  schemes are emitted as their exact T0 ufunc sequences (coefficients are the
  same Python floats T0 computes: `dt/3.0`, `0.5*dt`, …). State evolution is
  in-place for elementwise ops and ping-pong (one `(vault cell, alt cell)` pair
  per swapped field) for kernel-written outputs; the compiler compiles phases
  until the (cadence-lcm-aligned) draft blocks and slot bindings repeat, giving
  the even/odd × cadence signature variants with buffer references pre-bound.
  `plan_hash` = sha256 over the canonical plan text (`describe()`): schema
  fingerprint, ctx config, slot table, per-phase drafts with slots-by-label and
  floats as `float.hex()` — no `id()`, no `hash()`, stable across processes.
- **`plan/interpreter.py`** — `run_ops`: a for-loop with `match` on op type;
  Axpy/DiffScale execute exactly their documented sequences via `out=` ufuncs.
- **`plan/guards.py`** — `StalePlanError`, `PlanDriftError`, `PlanCompileError`,
  `schema_fingerprint`, `renegotiate_and_diff(plan, composition, ctx)` (debug
  mode re-runs the full bind and diffs hash + canonical text).
- **`context.py`** — `ComputeContext` gains `tier: "interpret"|"plan"` and
  `timestep`; `ctx.timeloop(state, composition, *, timestep, n_steps|until,
  monitors, debug_renegotiate_every)` is the §5.1 entry: T0 loop under
  `interpret`, bind-once + `plan.run_step(vault, i)` + façade-fed monitors under
  `plan`.
- **Tests** (all exact equality — `assert_array_equal`, never `allclose`):
  `test_plan_equivalence` (30), `test_plan_swap` (3), `test_plan_hash` (6),
  `test_plan_guards` (9), `test_plan_zero_traffic` (9, slow),
  `test_plan_ops` (9), `test_state_vault` (9), `test_context_tier` (7), shared
  builders in `tests/_plan_toys.py`.
- **Benchmark**: `benchmarks/s05_dispatch.py` (acceptance 6, see below).

## Acceptance results

1. **T0 ≡ T1 bitwise, fp64, 100 steps** — (a) the S03 toy loop; (b) all six
   federation shapes (fc/ps/sts/sus/ssus λ=0.5/ssus λ=0.3) × all four schemes
   (forward_euler/rk2/rk3ws/ssprk3) over the S04 ODE toys — 24 combinations;
   (c) CallingFrequency(2Δt) + Subcycle(n=3) composite. Additionally: a
   ScalingWrapper composite and a 2-stage `DynamicalCore` with the substep tier
   on (N=4, fractions (½, 1)) and off. All bit-identical.
2. **Even/odd**: 101 steps (odd) match T0 bitwise for the swap-carrying toy loop
   and the cadence composite; the façade exposes the live ping-pong buffer.
3. **Zero traffic**: settrace shows no xarray/pint/negotiation frames inside
   `run_step`; an instrumented `vault.names` records **zero** lookups during
   steady stepping; tracemalloc (fresh subprocess) shows a step-invariant
   gc-object census and ≥195/200 steps with exactly zero traced-memory delta
   (see *Deviations* for the precise protocol).
4. **plan_hash**: identical across two subprocesses with different
   `PYTHONHASHSEED`; changes under config change (strict flag, timestep),
   section reorder, coupling-member reorder, added schema field, dtype change.
5. **Guards**: façade rebind/add/delete each raise `StalePlanError` on the next
   `run_step`; in-place value writes do not; `debug_renegotiate_every` passes on
   the toys and `renegotiate_and_diff` raises `PlanDriftError` against a
   drifted composition.
6. **Microbenchmark** (20 toy components, (1, 10) fp64 state, embedded backend,
   2000 steps × 5 repeats, best repeat; this machine, CPython 3.10):

   | tier | per-step dispatch |
   |------|-------------------|
   | T0 (interpret) | 3.6–5.8 ms (run-to-run spread across sessions) |
   | T1 (plan)      | 57 µs (≈2.9 µs/component including the numpy kernels) |

   Speedup 64–101×; one-time bind + materialize cost 1.6–1.7 ms (amortized
   within the first step). No hard threshold per SPEC; script:
   `uv run python benchmarks/s05_dispatch.py`.

## Gate

`uv run pytest packages -m "not gpu" -q`: **374 passed, 1 skipped (mpi),
4 deselected (gpu)** · `ruff check .` clean · `ruff format --check .` clean ·
`mypy --strict -p symcon.core`: no issues in 43 files · `lint-imports`: 2 kept,
0 broken. Every new test file also passes in isolation.

## Deviations and interpretations (with rationale)

1. **`ComputeContext` extended additively** with keyword fields
   `tier="interpret"` and `timestep=None` (defaults preserve S03 behavior). The
   frozen `bind(composition, schema, ctx)` signature has no Δt parameter, and
   §8.2 makes the loop Δt a bind-time constant, so it must ride on the context;
   it also belongs in `plan_hash`'s config coverage. Declared per the
   additive-keyword rule.
2. **`visit(plan_builder)` + small public accessors added to S03/S04 classes**
   (PLAN item 3, "small, mechanical"): `Component.visit`,
   `DynamicalCore.visit`, `ConcurrentCoupling.visit`, both stepper roots, the
   four federations, and the three wrappers. `ComponentWrapper` gets a base
   `visit` that *refuses* compilation — `__getattr__` delegation would otherwise
   silently dissolve unknown wrappers. New read-only accessors:
   `CallingFrequency.update_period`/`.last_update_time`, `Subcycle.n`/
   `.ratio_provider`, `ScalingWrapper.scale_factors`, `SSUS.pre`/`.post`/`.core`.
   No existing signature changed.
3. **Acceptance 1(a) encoding**: the S03 toy loop is a hand-written script, not
   a component; it is encoded as
   `SUS([(CC([WindSpeed, Relaxation]), "forward_euler"), Damping])`, and the T0
   reference is the same composition under `tier="interpret"` — the equivalence
   statement is therefore exact and self-contained.
4. **Zero-traffic acceptance, precise reading.** `dict.__getitem__` is a C
   function invisible to `sys.settrace`/`setprofile`, so "no dict.__getitem__ on
   state names" cannot be proven by a tracer. The test proves (i) via settrace:
   no xarray/pint/contracts/state-wrapping/T0-call-path frames execute inside
   `run_step`; (ii) via instrumentation: the *state-shaped* mappings — the
   vault's interned `names` map — take zero lookups per step (bind-time only,
   §8.2). Component kernels receive **prebuilt** dict argument packs (built once
   at bind; the architecture's "argument order fixed, plain tuple pack" is
   realized as the frozen `(inputs, outputs, timestep)` pack); the C-level
   getitem *inside* a toy kernel is part of the kernel, and disappears when
   kernels become gt4py compiled programs with positional args (S07+).
5. **tracemalloc acceptance, precise protocol.** "Zero Python-level allocations
   per step after warmup" is asserted as: in a fresh subprocess, with the cycle
   collector held off, over 200 measured steps after 300 warmup steps —
   (a) the gc-tracked object census is exactly step-invariant (every launch);
   (b) ≥195/200 steps have exactly zero traced-memory delta with total drift
   < 2 KiB (existential over 3–4 launches). Forensics recorded in the test:
   CPython's full gc passes clear freelists (whose refill is traced and
   retained), and C-level ~63-byte block churn under the call machinery is
   layout-dependent and reproduces in a symcon-free control with hand-built
   ops, while a bare `out=` ufunc loop is deterministically clean. A genuine
   per-step leak (one retained int) would fail both (a)-adjacent counts and
   leave zero allocation-free steps. The recorder itself is allocation-free (a
   numpy scribble array); a Python-list recorder retains one int per step and
   fails the assertion it implements.
6. **`run_step` sequential-index contract**: ping-pong swap state makes the
   vault phase-dependent, so `step_index` must advance sequentially (mod the
   signature period) from materialization; violations raise `StalePlanError`
   rather than desynchronizing the façade. `ctx.timeloop` complies by
   construction.
7. **S05 compiler restrictions** (all loud `PlanCompileError`s at bind, never
   silent):
   - user-*registered* stepper schemes beyond the four S04 built-ins (a scheme
     emitter registration protocol is a follow-up);
   - `CallingFrequency` around Stepper-kind components (cache would need
     copy-on-replay), nested CF, the same CF instance appearing twice in one
     step, CF under a scaled dt (inside SSUS/Subcycle — time-dependent firing),
     CF with a live restart phase;
   - adaptive `ratio_provider` (Subcycle and DynamicalCore) — T2
     signature-cache territory (§8.3), deferred;
   - `DynamicalCore.fast_tendency_component` — the per-stage fast tier is S14's
     dycore-through-plan work;
   - federations nested as *redirected* sections (inside PS/STS); plain nesting
     under SUS/SSUS works;
   - `ScalingWrapper` around non-leaf components;
   - PS sections whose inputs are sibling sections' diagnostics (T0's
     ψⁿ-snapshot reads are unreproducible with shared canonical diag cells);
   - `Subcycle` over a component whose inputs intersect its own diagnostics
     (T0 substeps do not chain diagnostics);
   - a diagnostic written both under a cadence mask and by another component
     (would corrupt the persistent cache slot).
8. **Internal fix in S03 test-support toys** (`testing/toys.py`,
   `tests/_coupling_toys.py`): `_np` evaluated `npt.NDArray[np.float64]` per
   kernel call — a typing-module subscription that allocates through typing's
   parametrized-generic cache on the hot path. Hoisted to a module constant; no
   interface change.
9. **Cross-test global-state fix in the S01 suite**
   (`test_import_contracts.py`): the importability test popped all `symcon.*`
   modules and re-imported, leaving duplicate class identities in `sys.modules`
   for every later test (the S05 scheme `isinstance` dispatch tripped over it).
   Now saves/restores the original module objects — per the repo rule against
   cross-test registry/global-state leaks.
10. **CadenceMask at runtime**: per §8.2 the compiler resolves masks into the
    per-signature lists, so materialized variants inline the masked ops flat
    (the mask's guard is statically true for every step its variant serves);
    the `CadenceMask` op remains in the symbolic plan (hash/describe) and the
    interpreter can still execute one directly (one integer modulo) for debug.

## Follow-ups

- S14: dycore fast tier, adaptive substep ratios via the T2 signature cache,
  SlowTendencyBus/LFC publication pattern through the plan, plan-through-dycore.
- Scheme-emitter registration protocol so user-registered `TendencyStepper`
  schemes can compile (currently loud error).
- CF copy-on-replay compilation for Stepper-kind wrapped components; CF restart
  phases (bind currently requires fresh wrappers).
- `EgressPlan` is not exercised by the compiler (plan-allocated outputs need no
  egress validation); revisit when `out=`-style external buffers enter plans.

## Artifacts

- `benchmarks/s05_dispatch.py` (checked in; report-only). Numbers above; the
  gitignored `artifacts/` dir is unused — no data files were produced.
