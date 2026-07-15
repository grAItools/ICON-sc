# S02 — STATUS

**Branch:** `step/S02-core-state-contracts` · **Date:** 2026-07-09 · **State:** ready for PR

## What was built

Module map exactly as SPEC in-scope (all under `packages/symcon-core/src/symcon/core/`):

- **`typing.py`** — `FieldBuffer` runtime-checkable protocol verbatim from §2.2
  (`__dlpack__`/`__dlpack_device__`/`shape`/`dtype`); `Location` (`cell`/`edge`/`vertex`/
  `scalar`) and `HaloState` (`valid`/`dirty`) as `str`-valued enums (attrs compare naturally
  with plain strings); `HORIZONTAL_DIMS` helper set.
- **`registry.py`** (~45 lines, per PLAN's "resist cleverness") — `Factory`/`MetaFactory`
  with sympl-`oop` semantics (thesis Fig. 3.5): direct `Factory` subclass = registry root
  with a fresh name-keyed `registry`; deeper subclasses that set `name` self-register at
  class creation (= on import); duplicates raise `RegistrationError`;
  `Factory.factory(name, *args, **kw)` instantiates, unknown name → `KeyError` listing
  known names.
- **`state/names.py`** — canonical registry rows `QuantityDef(name, units, cf_name,
  icon_name, grib2)`; `register_quantity` (frozen signature) with namespace enforcement
  (see *Interpretations*); `_on_interface_levels` convention helpers with unit-lookup
  fallback to the base quantity; seed table of 18 quantities mined from icon4py v0.2.0
  `states/data.py` (units + ICON short names), with §2.5's icon:-namespacing for
  solver-internal quantities (`icon:exner_function`, `icon:normal_wind`,
  `icon:virtual_potential_temperature`, `icon:tangential_wind`).
- **`state/units.py`** — `canonical_units(name)`; `verify_noop(component_units, canonical)`
  rejecting every pair Pint deems non-identity; `units_identical` with literal-string fast
  path and cached lazy-Pint comparison (Pint imported only inside the cache-miss path —
  negotiation only, never at module import, never on `apply`). CF/UDUNITS exponent syntax
  (`m s-1`, `kg m-3`, `m^3`) is normalized to Pint syntax before parsing; `%`/`°` cleanup
  and `degrees_north`/`degrees_east`/`percent` definitions ported from upstream sympl.
- **`state/dataarray.py`** — `make_dataarray` (frozen signature) stamping
  `units`/`location`/`halo`/`grid_uuid` attrs per the §2.2 table; validates the buffer
  against `FieldBuffer`, rank-vs-dims, and dims-vs-location consistency; wraps without copy
  (`da.data is buffer` asserted in tests); `halo` initialized `VALID`.
- **`contracts/properties.py`** — `PropertySpec` frozen slotted dataclass (`dims`, `units`,
  `location`, `halo`, `alias`, `dtype`, `differentiable: native|custom|none`, `params`);
  `HaloPolicy` enum (`owned`/`required`/`invalidated`, §2.4 example vocabulary — distinct
  from state-side `HaloState`); `parse_properties(dict)` validating the dicts themselves
  (types, required/unknown keys, enum values, repeated/wildcard dims, alias collisions)
  with errors naming the field. sympl's wildcard/`dims_like` machinery deliberately dropped
  (canonical names make target dims explicit).
- **`contracts/checkers.py`** — `FieldSchema`/`StateSchema` (name → dims/units/dtype/
  device/location; built from real states via `__dlpack_device__`, or constructed directly
  so S05 can negotiate without data, per PLAN item 4). `StaticChecker(component_cls)`:
  definition-only — parses all four sympl property dicts, cross-dict dims/units consistency
  (tendency dicts excluded from the same-units check), alias bijectivity across dicts, and
  canonical-units verification (`verify_noop`) for registry-known names. `DynamicChecker
  (spec, state, *, component, strict=True, device=None)`: definition × data — missing
  fields / dim-set / location mismatches raise unconditionally; units, dim-order, dtype and
  device (DLPack device tuple: cupy-vs-numpy) mismatches raise under `strict=True`, each
  naming field + component; under `strict=False` they are collected into a
  `ConversionPlan` (`.plan`) instead.
- **`contracts/operators.py`** — `IngressPlan.build(spec, state_schema)` (classmethod,
  strict-validates, resolves aliases, freezes name order) / `IngressPlan.apply(state) ->
  tuple[raw buffers]` (pure `state[name].data` lookups; no xarray objects stored, no Pint,
  no `.values`); `EgressPlan` twin for caller-provided output buffers; `ConversionStep`/
  `ConversionPlan` records.
- **`config.py`** — `Config` frozen-dataclass base with `validate()` hook run from
  `__post_init__`, `replace()`, `to_dict()`; `provenance_stamp(config, **extra)` with
  created-at/python/package-versions/config-sha256.
- **`time.py`** — calendar-keyed `datetime()` (stdlib for `proleptic_gregorian`, cftime
  classes otherwise; upstream-sympl semantics, cftime now a hard dep of symcon-core);
  cadence arithmetic over exact integer microseconds: `timedelta_lcm`, `phase`, `is_due`.
- **`profiling.py`** — `Timer` with labelled nested sections (tree of nodes, cumulative
  calls/runtimes, only-nested-stops), `section()` context manager, `report()`; device-sync
  as an injected callback (no cupy dependency in core) — Ubbiali's Timer idea,
  instance-based instead of class-global.
- **Packaging** — symcon-core gains `xarray`/`pint`/`cftime` lower-bound deps (not a pin
  change; constraints/ pins only the gt4py+icon4py set); `hypothesis` added to the root dev
  group (PLAN item 7); mypy override for untyped `cftime`; curated re-exports in
  `symcon/core/__init__.py`.
- **Tests** — 12 new test files under `packages/symcon-core/tests/`, one per acceptance
  criterion plus module coverage (see *Gate results*). Property-based (hypothesis):
  `make_dataarray` attrs round-trip, `verify_noop` vs an independent Pint oracle,
  lcm/phase/is_due vs brute force.

## Gate results (local)

- `uv run pytest packages -m "not gpu" -q`: **129 passed, 1 skipped (mpi), 3 deselected
  (gpu)** (post-review; the third deselected test is the new cupy device test, which
  skips cleanly — reason "no CUDA device available" — when run without the marker filter).
- `uv run ruff check .`: clean. `uv run ruff format --check .`: 36 files already formatted.
- `uv run mypy --strict -p symcon.core`: **Success: no issues found in 16 source files**.
- `uv run lint-imports`: 2 contracts kept, 0 broken.
- Acceptance mapping: (1) `test_state_dataarray.py` (hypothesis round-trip),
  `test_state_units.py` (Pint-oracle property test), `test_state_names.py`
  (duplicate/namespace rejections); (2) `test_contracts_checkers.py` (strict raises on
  units/dim-order/dtype/device each naming field + component; `strict=False` →
  `ConversionPlan`); (3) `test_contracts_operators.py` (build once, apply twice, `is`
  identity + `__array_interface__` pointer equality); (4) `test_registry.py` (populated on
  import, unknown → KeyError listing names); (5) mypy strict clean +
  `test_no_pint_on_apply_path.py` (clean-subprocess proof that import+build+apply never
  import pint, plus in-process import-blocker monkeypatch).

## Interpretations & deviations

- **"unnamespaced-icon registrations" (SPEC acceptance 1).** The registry cannot know the
  CF standard-name table, so "is this unprefixed name secretly ICON-internal?" is not
  decidable in general. Implemented, both directions of the §2.5 invariant *no CF name ⟺
  icon: namespace*: (a) unprefixed names claim CF identity (`cf_name` defaults to the
  name); explicitly disclaiming it (`cf_name=NO_CF`) while unprefixed is rejected with
  guidance to register `icon:<name>`; (b) `icon:` names passing a `cf_name` are rejected
  (quantities with a CF name register under it, unprefixed); (c) any namespace prefix other
  than `icon:` — including a spelled-out `cf:` — is rejected. All three are tested.
- **`DynamicChecker` "returns a conversion plan" (SPEC acceptance 2).** The frozen
  interface is constructor-shaped (`DynamicChecker(spec, state) -> None | raise`), and a
  constructor cannot *return* a plan; with `strict=False` the plan is exposed as the
  `.plan` attribute of the constructed checker. Extra keyword-only params
  (`component`, `strict`, `device`) added after the frozen positional pair.
- **`make_dataarray` has no `halo` parameter** (frozen signature is exact); halo is always
  stamped `VALID` at construction — a freshly built field has no stale ghosts by
  definition; later steps mutate the attr.
- **CF-exponent normalization in units.py** (`m s-1` → `m s**-1`) is an addition not in
  sympl: canonical strings mined from icon4py are CF/UDUNITS-style, which Pint cannot
  parse. The test oracle copies this normalization regex from the implementation — only
  the Pint *identity decision* (made by the oracle's own independently constructed
  registry) is independent; the spelling convention itself is not oracle-checked.
- **StaticChecker does not require every name to be registered** in the canonical registry
  (the S02 seed table is deliberately small); canonical-units verification applies to
  known names only. Whether unregistered names should hard-fail at composition time is an
  S03 policy decision.
- **`icon:ddt_*` bus slots are not seeded**: no units source was mined for them in S02
  (they belong to S04's bus work; sympl's tendency `units + " s^-1"` convention is the
  obvious derivation, but that is S04's call to record).
- **icon4py-vs-architecture naming disagreement recorded** (also in development/references/lock.toml):
  icon4py files exner/theta_v/vn under CF-style standard names
  (`dimensionless_exner_function`, …); architecture §2.5 namespaces them `icon:` as
  solver-internal. Architecture doc wins (authority order); units/short names taken from
  icon4py.
- **`EgressPlan`** is a thin, self-describing subclass of `IngressPlan` (same mechanics —
  outputs are caller-provided buffers in the same state mapping per §8.2); SPEC lists
  "ingress/egress plan objects" in scope but freezes only `IngressPlan`'s interface.

## Follow-ups

- S03: wire `StaticChecker` into the component `__init_subclass__` hook; execute
  `ConversionPlan`s in non-strict ingress; decide unregistered-name policy.
- S04: register `icon:ddt_*` bus-slot quantities with reference-backed units.
- S05: reuse `StateSchema`/`IngressPlan` for zero-lookup bound argument packs;
  `schema_hash`/epoch live there.
- The `backend` fixture is still the S01 string stub; S02 introduced no gt4py coupling
  (none required by the SPEC).

## Artifacts

- `development/references/lock.toml`: +4 entries (sympl upstream, sympl-oop fork, tasmania, icon4py v0.2.0
  states metadata), appended at mining time.
- No benchmarks/plots required by the SPEC.

## Review fixes (round 1)

- **M1**: step branch actually points at the S02 commits now; local `main` restored to the
  S01 merge (`daf9e17`). Nothing had been pushed.
- **m1**: `@settings(deadline=None)` on `test_verify_noop_matches_pint_identity` — the
  first drawn example pays the lazy Pint `UnitRegistry` construction (~290 ms).
- gpu-marked `test_field_schema_from_cupy_dataarray_and_strict_device_check` added
  (acceptance 2(d) over a real cupy buffer; skips cleanly without a device via the S01
  collection hook + `importorskip`).
- `DynamicChecker` docstring now spells out the `device=None` semantics (first spec'd
  field in property-dict order sets the expectation; pass `device` explicitly when a
  backend-mandated device exists) — S03/S05 inherit these semantics.
- `test_registry.py` uses a save/restore registry fixture (order-independent).
- Softened the STATUS claim about the CF-exponent test oracle (regex is copied, not
  re-derived; only the Pint identity decision is independent).
