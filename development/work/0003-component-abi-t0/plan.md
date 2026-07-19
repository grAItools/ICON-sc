# S03 — Plan

1. Mine stubbiali/sympl `oop` for the exact `out=`/`array_call(inputs, outputs)`/`allocate_*` shapes; keep signatures recognizably close (they were designed for this) but route all checking through S02's Checkers/Operators — the base classes should contain almost no logic of their own.
2. `__init_subclass__` wiring for StaticChecker; cache one DynamicChecker + IngressPlan per (component-instance, schema-hash) so T0 already amortizes negotiation across calls with an unchanged schema (this is *not* S05 — dicts and DataArrays are still on the path — but it makes T0 usable).
3. Wrappers: implement `CallingFrequency` cache as a component-private field surfaced in `restart_state()` and declared in `functional_state()` (S10 relies on this being carry).
4. Minimal `ComputeContext`: `backend` is an opaque string in this step (real backend objects arrive with the first gt4py component in S07); allocator chooses numpy/cupy.
5. NetCDFMonitor: xarray-based, one file, append on `store`; enough for the SCM example, nothing more.
6. Toy components + the acceptance test suite; add the toy pair to `icon_sc.core.testing.toys` — S04/S05 reuse them.

**Pitfalls:** resist adding vault/plan concepts here; T0 must remain the fully dynamic reference semantics that S05 diffes against. Keep `Monitor` out of the component call path (no diagnostics side-channel).
