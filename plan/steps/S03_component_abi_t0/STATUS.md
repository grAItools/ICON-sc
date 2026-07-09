# S03 — STATUS

**Branch:** `step/S03-component-abi-t0` · **Date:** 2026-07-09 · **State:** ready for PR

## What was built

Module map exactly as SPEC in-scope (all under `packages/symcon-core/src/symcon/core/`):

- **`components/base.py`** — `Component` shared base plus the four callable kinds
  (`DiagnosticComponent`, `TendencyComponent`, `ImplicitTendencyComponent`, `Stepper`) and
  the `Monitor` ABC. Property dicts are class attrs validated by S02's `StaticChecker` from
  `__init_subclass__` (a component declaring non-canonical units never *defines*, let alone
  constructs); `__call__` runs full T0 negotiation per call — `DynamicChecker` (strictness
  from `ctx.strict`, device from `ctx.device`) → `IngressPlan` → allocate/extract outputs →
  `array_call(inputs, outputs, timestep)` → egress wrapping — with one negotiation cached
  per (instance, state-schema-hash) via hashable `FieldSchema` keys (PLAN item 2; dicts and
  DataArrays stay on the path — this is not S05). `allocate_output(name, schema, ctx)`
  default allocates through the context allocator with shape inferred from state dim sizes
  (consistency-checked) and dtype from the spec / same-named state field / fp64.
  `restart_state()`/`load_restart_state()` default-empty; `functional_state()` default-empty
  (§4.5/§8.5). Two public ClassVars added for downstream federations (S04):
  `output_dict_names` (egress order) and `timestep_required`.
- **`components/wrappers.py`** — `CallingFrequency(component, dt)` (sympl
  `UpdateFrequencyWrapper` firing rule: fires when `state["time"] >= last_update + period`,
  else cached output; rounding-to-multiple rule over exact integer microseconds, ties round
  up, clamped to ≥ 1 multiple; cache snapshot is deep-copied both at fire and on replay so
  piecewise-constancy survives caller mutation; phase + cache surfaced in `restart_state()`
  under `calling_frequency/…` keys and declared in `functional_state()`).
  `Subcycle(stepper, n=None, ratio_provider=None)` (exactly one; provider called once per
  outer step with the current state, integer ≥ 1 honored; substates chain tasmania-style;
  `out=` forwarded to the final substep only). `ScalingWrapper(component, *, …_scale_factors)`
  (keys validated at construction; inputs scaled into attr-preserving copies; outputs scaled
  in place so `out=` pointer identity is preserved).
- **`context.py`** — minimal `ComputeContext(backend, strict=True, allocator=...)`:
  backend is an opaque string (S07 brings real backends), allocator derived from the
  backend name (cupy for `gpu`/`cuda`-flavoured names, numpy otherwise) unless given,
  `device` (DLPack tuple) probed once at construction. No `ctx.timeloop()` (S05).
- **`contracts/conversion.py`** — `apply_conversion_plan`: executes the non-strict
  `DynamicChecker`'s `ConversionPlan` (S02 follow-up "S03 executes it"): units (Pint,
  offset-aware, negotiation-time only), transpose, cast. See *deviations* for `transfer`.
  Plus `convert_array` added to `state/units.py` (public addition; no frozen S02 signature
  touched).
- **`driver/timeloop.py`** — deliberately dumb `timeloop(state, step, *, timestep,
  n_steps|until, monitors)`: step → advance `state["time"]` → `monitor.store`; `until` must
  be an exact multiple of `timestep`; input mapping never mutated.
- **`io/monitor.py` + `io/netcdf.py`** — `MemoryMonitor` (deep-copied snapshots, variable
  selection) + synchronous single-rank `NetCDFMonitor` (xarray/netcdf4; one file; a time
  record appended per `store`; enum attrs sanitized to strings; §5.3 provenance stamp as a
  JSON global attr). `Monitor` base lives in `components/base.py` (§4.1 kind), never on the
  component call path (PLAN pitfall).
- **`testing/toys.py`** (PLAN item 6, reused by S04/S05) — `Relaxation(TendencyComponent)`
  (Newtonian relaxation, closed form under Euler), `Damping(Stepper)` (exact exponential),
  `ImplicitDamping(ImplicitTendencyComponent)` (damping as timestep-dependent tendency,
  exact under Euler apply), `WindSpeed(DiagnosticComponent)` (`hypot(u, v)`), and the
  `column_state()` factory. Purely mathematical toys — no scientific constants, nothing to
  mine.
- **Packaging** — symcon-core gains `netcdf4>=1.6` (lower bound; xarray's engine for
  `io/netcdf.py` — generic I/O is symcon-core's mandate per its package description; not a
  gt4py/icon4py pin change). Curated re-exports in `symcon/core/__init__.py` extended.
- **Tests** — 8 new test files (63 tests): `test_components_base.py`,
  `test_components_wrappers.py`, `test_strict_end_to_end.py`, `test_toys_acceptance.py`,
  `test_driver_timeloop.py`, `test_io_monitors.py`, `test_contracts_conversion.py`,
  `test_context.py` (one gpu-marked cupy allocator test, skips cleanly).

## Gate results (local)

- `uv run pytest packages -m "not gpu" -q`: **193 passed, 1 skipped (mpi), 4 deselected
  (gpu), 1 warning** (the warning is netCDF4's import-time numpy-size RuntimeWarning from
  the prebuilt wheel, not symcon code).
- Every new test file also green in isolation (order-independence checked).
- `uv run ruff check .`: clean. `uv run ruff format --check .`: 55 files already formatted.
- `uv run mypy --strict -p symcon.core`: **Success: no issues found in 27 source files**.
- `uv run lint-imports`: 2 contracts kept, 0 broken.
- Acceptance mapping:
  1. `test_toys_acceptance.py` — Fig. 1 standalone diagnostic call; Fig. 2 RCE-style loop
     (diagnostics → Euler tendencies → stepper → monitor) matching closed forms at
     rtol=1e-12 fp64, every intermediate monitor record included.
  2. `test_components_base.py::TestOutPath` — `out=` pointer identity (`is` on DataArrays
     *and* raw buffers), a monkeypatched `allocate_output` that raises proves no hidden
     allocation, counting subclass proves exactly one `allocate_output` per missing field
     (and only the missing field under partial `out=`).
  3. `test_components_wrappers.py::TestCallingFrequency` — 20 steps with dt_proc = 3·dt
     verified `assert_array_equal` (bit-equal, same op order) against a hand loop; fire
     count = 7; phase + cache survive `restart_state`→`load_restart_state` bit-exactly
     (phase compared by value identity, arrays bit-equal, continued twin trajectories
     bit-identical); rounding rule unit-tested (190 s → 3 min at dt = 1 min).
  4. `test_strict_end_to_end.py` — degC declaration raises `PropertyDictError` at class
     creation naming field + component; transposed state raises `ContractViolationError`
     at call naming field + component; non-strict ctx converts (transpose, offset degC→K)
     instead.
  5. `test_components_wrappers.py::TestSubcycle` — provider called exactly once per outer
     step with the current state (times asserted), returned integer honored (12 sub-calls
     of dt/4 over 3 outer steps).

## Interpretations & deviations

- **Single flat `out=` mapping.** The SPEC freezes `__call__(state, timestep, *, out=None)`
  with *one* out dict, where the sympl-oop donor has `out_tendencies`/`out_diagnostics`/
  `out_state`. Implemented the frozen shape: `out` and `array_call`'s `outputs` are flat
  `name → value` unions of the kind's output dicts; a name colliding across the two output
  dicts of one component is rejected at class creation (cannot disambiguate). Recorded as a
  deliberate ABI simplification per the frozen interface.
- **`array_call` signature is uniform** across kinds (`inputs, outputs, timestep`), with
  `timestep=None` for kinds that don't require one — the SPEC's exemplar signature applied
  "analogously" instead of sympl-oop's per-kind signatures. `overwrite_tendencies` and
  `tendencies_in_diagnostics` (sympl-oop features) are out of S03 scope and not ported.
- **`allocate_output` covers all output kinds.** SPEC freezes only `allocate_output`; the
  donor's `allocate_diagnostic`/`allocate_tendency` are subsumed by it (the `schema`
  argument carries the `PropertySpec`, so an override can dispatch per field). `schema` is
  the new `OutputSchema` dataclass (spec + shape + dtype) — the SPEC did not pin its type.
- **`out` is keyed by contract names only** (aliases are resolved for *state* lookups, not
  for `out=`), and caller-provided outputs are validated **strictly regardless of
  `ctx.strict`**: `array_call` writes raw into those buffers, so no conversion could
  reconcile a mismatch afterwards.
- **`transfer` conversion steps are not executed at T0** (`ConversionError` with guidance).
  Executing host↔device copies silently in the "debug" path would contradict §2.4's intent,
  and no acceptance criterion needs it; revisit when a GPU state exists (S07).
- **CallingFrequency phase representation:** `restart_state()` carries the last-update
  datetime in a 0-d DataArray's `attrs["value"]`, not in the array payload — xarray coerces
  object arrays of stdlib datetimes to `datetime64[ns]`, which would break bit-exactness
  and cftime round-trips. In-memory round trip is bit-exact (acceptance 3); NetCDF
  serialization of restart dicts is `RestartMonitor`'s problem (post-slice). The cache
  arity (dict vs tuple result) is stored the same way under
  `calling_frequency/cache_is_tuple`.
- **`functional_state()` phase spec:** declared as a dimensionless scalar `PropertySpec`
  (units "1") — a datetime has no canonical-units representation in the S02 schema. S10
  (F-tier carry) should decide the real encoding; flagged as follow-up.
- **`CallingFrequency` replay copies:** replayed outputs are deep copies (or copies into
  `out=` buffers), so callers can never corrupt the cache; this trades allocations for
  correctness at T0 (the plan compiler owns the efficient version, §8.2 cadence masks).
- **NetCDFMonitor rewrites the file per store** (append semantics at the record level, not
  the syscall level): xarray cannot append along a dimension to netCDF. Synchronous and
  O(n²)-ish in I/O — acceptable for the SCM slice, replaced by async/zarr post-slice.
  This required the `netcdf4` dependency (recorded above; not a pinned-pair change).
- **Unregistered-name policy (S02 follow-up):** kept permissive — names unknown to the
  canonical registry are the component author's claim and skip the canonical-units check
  (the toys use `wind_speed`, `departure_from_equilibrium`, `damping_rate` this way).
  Hard-failing would force every toy/test quantity into the global registry; revisit at
  composition level (S04) if federations need it.
- **`Subcycle` does not advance `state["time"]` between substeps** — deliberately dumb per
  the SPEC's T0 framing; time-dependent steppers under subcycling get correct times only
  from the plan compiler (S05). Documented in the class docstring.
- **No contradictions found** between architecture doc, SPEC and PLAN for this step.

## Follow-ups

- S04: federations consume `Component.output_dict_names`/`parsed_properties`/
  `timestep_required`; decide composition-level policy for unregistered names; register
  `icon:ddt_*` bus slots.
- S05: replace per-call negotiation with the bound plan; schema-hash caching here is the
  seed of that (keys are already hashable `FieldSchema` tuples); wrappers dissolve into
  cadence masks/unrolled loops.
- S07: real backend objects behind `ComputeContext.backend`; execute (or keep rejecting)
  `transfer` conversion steps once GPU states exist.
- S10: real F-tier encoding for the `CallingFrequency` phase carry (currently units "1"
  scalar spec).
- Aliases are resolved for state ingress but not for `out=` keys (contract names only) —
  extend if a real component needs it.

## Artifacts

- `REFERENCES.lock`: +3 entries (sympl-oop component ABI/wrappers/monitor shapes; sympl
  upstream NetCDFMonitor semantics + Fig. 1/2 usage pattern; tasmania substep semantics),
  appended at mining time. Reference clones reused from S02 (same SHAs, verified).
- No benchmarks/plots required by the SPEC.

## Review fixes (round 1)

- **M1 (MAJOR, fixed)** — `CallingFrequency` restart round trip crashed on replay for any
  wrapped component with an empty output dict (e.g. `ImplicitDamping`: tendencies, no
  diagnostics): empty parts left no per-field cache key, so `load_restart_state`
  reconstructed a shorter cache tuple. The part count is now persisted explicitly
  (`calling_frequency/cache_parts`) and reconstruction is by declared count with empty
  parts keeping their slot; corrupt counts (part index ≥ count) are rejected. Regression
  test: `TestCallingFrequencyEmptyPartRestart` (bit-exact replay on original and restored
  twin).
- **m1 (fixed)** — caller-provided `out=` buffers are now shape-checked per call against
  the state's dim sizes (schemas are shape-free, so the cached `EgressPlan` cannot carry
  this); a wrong-shaped buffer with correct dim names raises instead of silently
  broadcasting. Tests: `TestOutBufferShapeCheck` (reject + accept directions).
- **m2 (fixed)** — `out=` egress now validates against the context device symmetrically
  with ingress: `IngressPlan.build`/`EgressPlan.build` gained an optional keyword-only
  `device` (additive to the S02 frozen interface, default preserves old behaviour) and
  `_resolve_outputs` forwards `ctx.device`. Tests: synthetic CUDA-vs-CPU rejection at the
  operators level (`test_egress_build_enforces_device_expectation`) + a spy asserting the
  component forwards `ctx.device` (`TestEgressDeviceForwarding`).
- **INFO items** — `_ComponentWrapper` is now public (`ComponentWrapper`) and wrapper
  constructors accept `Component | ComponentWrapper`, so mypy-strict user code composes
  `CallingFrequency(Subcycle(...))` without casts; `Subcycle`'s docstring notes that
  `Subcycle(CallingFrequency(...))` degenerates to at most one effective fire per outer
  step (time does not advance between substeps). The "`__init_subclass__` import-identity
  fix" mentioned in the implementer's interim report was folded into the original
  `base.py` commit during development (module-level `StaticChecker` import); it was never
  a separate post-review change — recorded here to reconcile the reports.
- Gate after fixes: 198 passed, 1 skipped (mpi), 4 deselected (gpu); ruff/format clean;
  mypy --strict 27 files clean; import contracts 2 kept.
