# S14 — Execution plan through the dycore: STATUS

Branch `step/S14-plan-through-dycore`. The slice's exit gate: the composed JW
model (S12 dycore + S13 diffusion) compiles to a §8.2 execution plan and runs
under T1 bitwise-identically to T0; the SCM and JW example scripts are
plan-hash-pinned to their preset builders; dispatch-overhead evidence recorded.

## 1. What was built

1. **Substep-outer dycore unrolling** (`plan/bind.py::_emit_dycore_substep_outer`,
   PLAN item 1). `DynamicalCore` gains `substep_nesting: ClassVar[str]`
   (`"stage_outer"` default = the Fig. 3.10 orchestration S05 already compiled;
   `"substep_outer"` = ICON's nesting). A substep-outer core is unrolled into
   the exact op order of `perform_dyn_substepping` / the icon4py driver
   (REFERENCES.lock `icon4py-driver-substep-op-order`,
   `icon-fortran-substep-op-order`):
   `plan_ingress(n)` → per substep [`plan_substep_begin` (private carry swaps)
   → `substep_array_call(stage, substep)` per stage → `plan_substep_end`
   (private time-level swap; postponed past the last substep)] →
   `plan_egress`. All hooks are plain BoundCalls sharing one pre-bound boundary
   pack; **the private buffers never reach the vault** — the only vault-visible
   effect is the step-level ping-pong of the boundary prognostics (PLAN
   pitfall, verified with the hand-worked op list at `ndyn_substeps=2` before
   the full model). Bind-time guards: hook-set completeness, `substeps >= 1`,
   Δt divisibility at μs resolution (the S12 `array_call` runtime refusal,
   promoted to bind time).
2. **`NonhydroSolver` compiles unrolled** (S12 STATUS follow-up resolved): the
   `visit` override routes to `visit_dynamical_core`; the plan-hook quartet
   replays `array_call`'s orchestration verbatim on the component-private
   icon4py state (MOST_EFFICIENT advective-pair swaps, the initial-timestep
   exception via the private `_at_initial_timestep` flag — §4.5 restart
   semantics unchanged), `plan_egress` does the bookkeeping + boundary egress.
3. **Top-level `ConcurrentCoupling` publication** (the S05-refused
   "ConcurrentCoupling as tendency provider"; S05 STATUS follow-up
   "SlowTendencyBus/LFC publication pattern through the plan"): a coupling
   dispatched outside a tendency evaluation compiles as the §5.1 bus
   publication — stage-0 member walk (CallingFrequency cadence masks work
   unchanged) plus one publication Axpy per tendency field into its published
   state cell, replaying T0's `acc = c1; acc += c2; ...` member order
   (bitwise). On non-fire cadence phases the persistent member cells hold the
   cache, so the per-step publication Axpy reproduces the CF replay verbatim.
4. **Monitor exclusion + the host-step seam** (PLAN item 2): `run_ops`/
   `run_step` gain `on_segment` (additive, default `None`) — the interpreter
   yields to a host callback at every `SegmentMarker`; `ctx.timeloop`'s plan
   tier advances time and stores monitors in the `step_end` host step, and a
   `Monitor` inside a composition tree is a loud `PlanCompileError` pointing at
   `ctx.timeloop(monitors=...)`. Design note for T2 (graph replay stops at
   exactly these markers) lives in the interpreter docstring; no T2 code.
5. **JW composition + explicit bus slots**: `JWModel` gains `composition =
   SequentialUpdateSplitting([dycore, diffusion], name="jw_dry")` and
   `build_jw` adds explicit zero `icon:ddt_vn_phy`/`icon:ddt_exner_phy` fields
   to the initial state. **Decision (S12 STATUS follow-up):** the plan compiler
   does *not* synthesize default-zero bus slots — the bound state is explicit;
   the `__call__` zero-fill stays a T0 convenience. Under T0 the dycore ingests
   the same zeros it would have synthesized, bitwise, so the S13 L4 cache
   remains valid (asserted: `composition` ≡ `model.step` closure, bitwise).
6. **SCM composition bindable**: `SCMComposition` gains `visit` (compiles
   exactly the `step()` sequence: publishing slow suite → consumer → fast SUS)
   and a Stepper-shaped `__call__` adapter, both additive.
7. **Examples wired for the drift test** (PLAN item 4, S09 STATUS follow-up):
   `examples/01`/`02` expose `build_model()`; tests bind the example's
   composition and the preset builder's and assert equal `plan_hash` — the
   layout-doc drift test, now enforceable (supersedes S09's textual check,
   which still passes).
8. **Benchmark** `benchmarks/dispatch_overhead/jw_step.py` (SPEC in-scope):
   T0-vs-T1 per-step wall time with repetition; gpu path records a
   kernel-launch count by capturing one T1 step into a CUDA graph via cupy
   stream capture + ctypes `cudaGraphGetNodes` (cupy v13 binds no node
   enumeration — REFERENCES.lock `cupy-graph-launch-count`), reporting a
   capture failure position as the T2 segment observation. Artifact in §4.
9. **Two latent S05 compiler fixes** (found by the new coverage, both
   hash-preimage-relevant):
   - `_ingress_cache` was keyed by walk path alone; a composite that
     dispatches several children at one path (the S14 loop-body composites)
     collided ingress plans across components. Now keyed by
     `(path, id(component))`.
   - the `plan_hash` preimage embedded `repr(ctx.backend)`; for a `Backend`
     *object* (S07+) that repr contains live executor objects (memory
     addresses), making the hash instance/process-dependent. Now
     `ctx.backend_name`. String-backend hashes (all S05 toys) are unchanged.

## 2. Acceptance criteria → tests

| # | Criterion | Test |
|---|---|---|
| 1 | T0 ≡ T1 on JW, 24 simulated hours, bitwise fp64 per backend | `test_jw_plan_equivalence.py::test_jw_t0_t1_bitwise_24h[gtfn_cpu]` (288 lockstep steps, all 5 prognostics compared bitwise after **every** step + checkpoint diagnostics at 24 h; `data`+`slow`) and the gpu-marked `[gtfn_gpu]` leg (skips without a device). `::test_jw_composition_matches_step_closure_first_steps` ties the composition to the S13 L4-cache closure. Unit-level: `test_plan_dycore_substep_outer.py` (bitwise at n ∈ {1,2,5} × {100,101} steps), `test_nonhydro_component.py::test_plan_unrolled_hook_order_matches_t0` (stub granule) |
| 2 | Zero-traffic assertions on the JW plan | `test_jw_plan.py::test_zero_traffic_on_the_jw_plan` — settrace (no xarray/pint/negotiation frames) + counting `names` map (0 lookups) over full signature periods. The tracemalloc criterion is toy-plan-only per SPEC S05 acceptance 3 (the hosted granule allocates device temporaries by design) |
| 3 | Plan-hash equality for both example/builder pairs; changes on 3 knobs | `test_scm_plan.py::test_plan_hash_example_01_matches_scm_builder` + `::test_plan_hash_changes_with_scm_config_knob[dtime/slow_timestep/fast_order]`; `test_jw_plan.py::test_plan_hash_example_02_matches_builder` + `::test_plan_hash_changes_with_jw_config_knob[dtime/ndyn_substeps/strict]` |
| 4 | Benchmark artifact in STATUS | §4 below (observation, no threshold) |
| 5 | `pytest -m "not gpu and not slow"` full-repo ≤ 15 min | §5 below |

## 3. Deviations / decisions / findings

- **Additive frozen-interface extensions (declared per AGENTS.md):**
  `DynamicalCore.substep_nesting` ClassVar + the plan-hook quartet contract
  (documented on the ClassVar); `run_ops(..., on_segment=None)` /
  `ExecutionPlan.run_step(..., *, on_segment=None)`; `JWModel.composition`
  field; `SCMComposition.visit`/`__call__`; `examples build_model()`. No frozen
  signature changed.
- **Fast tier stays uncompiled.** The S05 error message promised the per-stage
  `fast_tendency_component` tier "in S14"; SPEC S14's scope is "everything the
  JW loop uses", and the JW loop has no fast tier. The rejection stays loud
  with the message updated to "post-slice follow-up" (compiling it needs
  per-stage coupling evaluation on provisional state at both nestings). Same
  for adaptive `ratio_provider` (T2 signature-cache territory, unchanged).
- **Shape knobs do not move `plan_hash` — by design.** The symbolic plan is
  shape-free (§8.2: shapes bind at materialization against the vault), so
  `nlev`/`n_cell` hash identically; the knob spot-checks use plan-visible
  knobs (Δt, cadence, substep count, section order, strict flag). Constructor
  scalars remain the documented S05 blind spot (folding a component-config
  digest into the hash is still open — see follow-ups).
- **`plan_hash` preimage change** (finding 9): any persisted hash from
  S05–S13 for object-backend contexts was instance-dependent (broken) and for
  string-backend contexts is *unchanged*. No hash is persisted anywhere in the
  repo (checked: T3 caching is post-slice), so no migration.
- **Explicit bus slots in `build_jw` state** (decision, §1.5): `model.state`
  gains two zero fields. The 9-day L4 cache is untouched and remains valid —
  the closure path ingests identical zeros (bitwise; asserted by the
  composition≡closure test); the L4 runner and its provenance dict are
  unmodified, and the cache was **not** regenerated.
- **JW knob test touches a private** (`dycore._substeps`, restored in
  `finally`): the `ndyn_substeps` hash knob without a second ~25 s archive
  build; S12 precedent (STATUS deviation 6) for upstream-style private staging
  in tests.
- **The 24 h equivalence costs ~20 min wall** (gtfn_cpu, warm caches, both
  legs in lockstep); it is `data`+`slow` and dominates that gate. It is
  **chunk-resumable** via `SYMCON_S14_EQUIV_HOURS`/`SYMCON_S14_EQUIV_STATE`
  (the S13 `make_reference.py` pattern: per-leg component restart protocols +
  boundary prognostics; every chunk re-asserts lockstep bitwise equality per
  step). CI default (no env) is the single 24 h run; the acceptance evidence
  here was produced as 4 × 6 h chunked invocations of the same test function
  (this environment caps single commands at 10 min). The 24-hours-continuous
  claim across chunk boundaries rests on the bitwise restart fidelity S12
  acceptance 3 proved for the dycore (and the diffusion restart schema),
  plus each chunk's per-step bitwise lockstep assertions.
- **GPU benchmark leg is unvalidated here** (no CUDA device in the
  implementation environment; cupy not installed). The capture-based launch
  count is best-effort with an explicit failure mode that itself reports the
  T2 segment observation. gpu-marked tests skip cleanly (verified).

## 4. Benchmark artifact (SPEC acceptance 4 — observation, not threshold)

`uv run python benchmarks/dispatch_overhead/jw_step.py --steps 20 --repeats 3`
(gtfn_cpu, R02B04 × 35 levels, fp64, warm persistent gt4py cache;
16-core host, otherwise idle):

```
model:                 JW dry (R02B04, 35 levels), backend gtfn_cpu
steps per repeat:      20  (repeats: 3, best reported)
T0 per step:              3680.7 ms  (median 3736.8 ms)
T1 per step:              3433.3 ms  (median 3488.6 ms)
host-side delta:           247.4 ms/step  (6.7% of T0)
one-time bind cost:         3.30 s  (negotiation + materialize + step 0)
```

Reading: the composed JW step is kernel-dominated (two hosted gtfn granules,
~10 predictor/corrector program invocations per Δt), so the T0→T1 delta — the
sympl negotiation/ingress/wrapping cost removed by the §8.2 phase split — is
a small fraction of the step at this grid size, in contrast to the
kernel-free S05 toy benchmark (~50× on pure dispatch). The per-step host-side
saving is the constant that matters at production grid counts and on GPU,
where kernel time shrinks but dispatch does not (the P5/T2 motivation).

## 5. Gates

All green on the step branch (16-core host; gt4py/gt4py-data caches warm):

- `pytest packages -m "not gpu and not slow" -q` — **736 passed, 1 skipped (mpi)**,
  **14:08 warm-cache** (acceptance 5: ≤ 15 min — met, with thin margin; an 18:30
  first run paid one-time gtfn compiles of the new S14 plan-path variants, and the
  three S08 embedded graupel L2 cases dominate at ~10 min combined — trunk candidates
  if the margin erodes further).
- 24 h JW T0≡T1 bitwise (`test_jw_plan_equivalence.py -m "not gpu"`, acceptance 1):
  **2 passed** (288 composed steps in lockstep, every prognostic exact at every step +
  final checkpoint diagnostics), 25:27.
- `-m "slow and not gpu and not data"` — **30 passed**, 5:20.
- `-m "data and not slow and not gpu"` — **43 passed**, 6:33.
- `-m "data and slow and not gpu"` — **76 passed, 1 skipped** (upstream MCH-only
  initial-step), 32:04.
- S14 test files in isolation: substep-outer + publication **20 passed**; JW
  plan-equivalence file green standalone.
- `ruff check` clean · `ruff format --check` 171 files clean ·
  `mypy --strict -p symcon.core` clean (50 files) · `lint-imports` 2 contracts kept.
- Benchmark artifact: §4 (run alone on an otherwise idle host).

## 6. Follow-ups

- Fast tier (`fast_tendency_component`) through the plan: per-stage coupling
  evaluation on provisional state, for both nestings (post-slice).
- Adaptive `ratio_provider` under T1/T2 via the signature cache (§8.3),
  including the Δt-divisibility policy (S12 STATUS item, still open).
- Fold a stable component-config digest into `plan_hash` before anything
  caches compiled artifacts by it (S05 review MINOR-2, still open).
- CF copy-on-replay for Stepper-kind wrapped components; CF restart phases;
  scheme-emitter registration (S05 follow-ups, unchanged).
- `validation/L4_idealized/make_reference.py --run all` still excludes the
  symcon leg (S13 STATUS); folding it in (or renaming the option) remains a
  sanctioned trunk-or-later fix — that file was deliberately not touched in
  S14 (the L4 cache must not be perturbed by the exit-gate step).
- T2: capture SegmentMarker-delimited segments under stream capture; the
  host-step seam and the benchmark's capture probe are its landing points.

## 7. Artifacts

- Benchmark output committed verbatim in §4 (no data files; `artifacts/`
  unused). Probe logs under the session scratchpad.

## Review fixes (round 1)

- Benchmark docstring corrected: the JW dycore unrolls to **21** BoundCalls at
  ndyn_substeps=5 (1 ingress + 5 begin + 10 stage calls + 4 end + 1 egress), not 13
  (reviewer MINOR 1; measured from `plan.describe()`).
- **⚠ PR NOTE (reviewer MINOR 2):** acceptance 1's "bitwise per backend" is
  evidence-backed for **gtfn_cpu only** — the `[gtfn_gpu]` leg has never executed
  anywhere (no CUDA device/cupy in the implementation or review environments; skip
  verified clean). First GPU-runner execution must be watched, together with the
  gpu-marked legs accumulated since S07 (same standing note in S07/S08/S12 STATUSes).
- test_nonhydro_component.py docstring cross-reference corrected (S12 §1.5/§3).
- Reviewer INFO 3 (CadenceMask `on_segment` forwarding in direct interpretation —
  unreachable today, latent T2 seam) recorded as a follow-up.
