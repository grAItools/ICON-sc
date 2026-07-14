# S02 — Core state layer + contracts

**Lane:** trunk · **Depends on:** S01 · **Unblocks:** S03, S06, S11

## Goal
The §2 boundary exists: FieldBuffer protocol, canonical names/units registries, boundary DataArray construction, property-dict schema with the symcon extensions (location, halo, differentiable, params), and the Checker/Operator machinery (static/dynamic split per §4.2 ← Ubbiali).

## In scope (module map = layout doc `symcon/core/`)
`typing.py` (FieldBuffer protocol via `__dlpack__`; `Location`, `HaloState` enums) · `registry.py` (`Factory`/`MetaFactory`, name-keyed, register-on-import; port semantics from stubbiali/sympl `oop`) · `state/names.py` (registry machinery + `_on_interface_levels` convention; namespacing `cf:`-implicit vs `icon:`) · `state/units.py` (canonical-units table keyed by name; `verify_noop(component_units, canonical)`; Pint only at negotiation) · `state/dataarray.py` (constructors stamping units/location/halo/grid_uuid attrs) · `contracts/properties.py` (typed property-dict schema incl. `differentiable: native|custom|none` and `params`; validation of the dicts themselves) · `contracts/checkers.py` + `contracts/operators.py` (static checkers: definition-only; dynamic checkers/operators: definition × data; ingress/egress plan objects that S03 executes and S05 pre-resolves) · `config.py` (frozen-dataclass base + provenance stamp helper) · `time.py` (cftime-aware datetime handling; cadence arithmetic: lcm of timedeltas, phase) · `profiling.py` (labelled nested Timer, device-sync hook).

## Out of scope
Component base classes (S03), StateVault (S05), any grid.

## Frozen interfaces
```python
class FieldBuffer(Protocol): __dlpack__, __dlpack_device__, shape, dtype
Location = Enum("cell","edge","vertex","scalar"); HaloState = Enum("valid","dirty")
make_dataarray(buffer, *, name, dims, units, location, grid_uuid=None) -> xr.DataArray
canonical_units(name: str) -> str;  register_quantity(name, units, cf_name=None, icon_name=None, grib2=None)
PropertySpec / parse_properties(dict) -> Mapping[str, PropertySpec]
StaticChecker(component_cls) -> None | raise;  DynamicChecker(spec, state) -> None | raise
IngressPlan.build(spec, state_schema) -> IngressPlan;  IngressPlan.apply(state) -> tuple[raw...]
Factory.factory(name, *args, **kw);  class attr `name` + `registry`
```

## Acceptance criteria
1. Unit tests: property-based (hypothesis) round-trip on `make_dataarray` attrs; units no-op verification rejects any pair Pint deems non-identity; names registry rejects duplicate/unnamespaced-icon registrations.
2. Strict-mode semantics testable in isolation: `DynamicChecker` with `strict=True` raises on (a) unit mismatch, (b) dim-order mismatch, (c) dtype mismatch, (d) device mismatch (cupy vs numpy buffer), each with an error naming field + component; `strict=False` returns a conversion plan instead.
3. `IngressPlan` built once, applied twice, returns identical buffer identities (zero-copy assertion via `ctypes`/`__array_interface__` pointer equality for numpy).
4. Factory registration matches the thesis Fig. 3.5 behavior (registry populated on import; unknown name → KeyError listing known names).
5. mypy --strict clean; no runtime Pint import on the `IngressPlan.apply` path (assert via import-time monkeypatch test).
