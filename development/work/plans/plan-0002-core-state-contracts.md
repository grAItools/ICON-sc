# S02 — Plan

1. **Mine sympl first.** Read upstream sympl `_core` (property mechanics, units, alias handling) and the stubbiali fork's Checkers/Operators/Factory (branch `oop`). Port *semantics*, not code: symcon's schema adds location/halo/differentiable/params and drops sympl's implicit any-unit conversion in favor of canonical units + strict mode. Record files read in `development/references/lock.toml`.
2. Implement `typing.py`, `registry.py` (metaclass registration; keep it ~40 lines — resist cleverness).
3. `state/names.py` + `state/units.py`: table-driven; canonical units stored as strings, compared via a cached Pint identity check at registration time only.
4. `contracts/`: `PropertySpec` as frozen slotted dataclass; static checker validates spec dicts at class definition (invoked from a `__init_subclass__` hook that S03 will wire); dynamic checker + `IngressPlan` operate on a lightweight `StateSchema` (name → (dims, units, dtype, device, location)) so S05 can reuse them without real data.
5. `time.py`: cadence lcm/phase using integer microseconds; property tests vs brute force.
6. `profiling.py`: port the Ubbiali Timer idea (labelled sections, cumulative, explicit sync callback so cupy can be injected later without a core dependency).
7. Tests per acceptance; wire hypothesis into dev deps.

**Pitfalls:** don't let xarray coerce cupy buffers (no `.values` anywhere in core paths — the fork's duck-array lesson, §4.2); keep `IngressPlan` free of xarray objects (schema in, raw buffers out) or S05's zero-lookup goal dies here.
