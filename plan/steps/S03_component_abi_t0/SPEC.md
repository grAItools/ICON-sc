# S03 — Component ABI, wrappers, T0 dispatch

**Lane:** trunk · **Depends on:** S02 · **Unblocks:** S04, S06, S11 (lane forks here)

## Goal
The sympl component taxonomy exists with the Ubbiali ABI (§4.1–4.2): base classes whose `__call__` does full T0 negotiation-per-call, `array_call(inputs, outputs)` with caller-provided outputs, `allocate_*` hooks, restart protocol, and the control-flow wrappers.

## In scope
`components/base.py`: `DiagnosticComponent`, `TendencyComponent`, `ImplicitTendencyComponent`, `Stepper`, `Monitor` — each: property-dict class attrs checked by StaticChecker via `__init_subclass__`; `__call__(state, timestep=None, *, out=None)` running DynamicChecker + IngressPlan + `array_call` + egress wrapping; `restart_state()/load_restart_state()` default-empty; `functional_state()` returning schema of private carry (empty default, consumed in S10). `components/wrappers.py`: `CallingFrequency` (per-process dt, rounding-to-multiple rule, cached-output semantics, phase-in-restart-state), `Subcycle(stepper, n | ratio_provider)`, `ScalingWrapper`. `context.py` (minimal for the slice): backend name, allocator (numpy | cupy), strict flag; `ctx.timeloop()` NOT yet (S05). `driver/timeloop.py`: plain helper loop for T0 (advance `state['time']`, call monitors) — deliberately dumb. `io/monitor.py` + `io/netcdf.py`: synchronous single-rank NetCDFMonitor (async + zarr are post-slice).

## Frozen interfaces
```python
class Stepper:  # exemplar; all bases analogous
    input_properties/diagnostic_properties/output_properties: ClassVar[dict]
    def __call__(self, state, timestep, *, out=None) -> tuple[diagnostics, new_state]
    def array_call(self, inputs: dict[str, Buffer], outputs: dict[str, Buffer], timestep) -> None
    def allocate_output(self, name, schema, ctx) -> Buffer
    def restart_state(self) -> dict[str, xr.DataArray];  def load_restart_state(d) -> None
    def functional_state(self) -> Mapping[str, PropertySpec]   # explicit-carry schema (§8.5)
CallingFrequency(component, dt); Subcycle(stepper, n=None, ratio_provider=None); ScalingWrapper(...)
ComputeContext(backend: str, strict: bool = True, allocator=...)
```

## Acceptance criteria
1. The sympl paper's Fig. 1/Fig. 2 pattern reproduced with two toy processes (analytic relaxation + linear damping) on a 1-column state: diagnostic call standalone; RCE-style loop runs; results match closed-form to 1e-12 (fp64).
2. `out=` path: with preallocated outputs, `array_call` writes in place — pointer-identity test proves no hidden allocation; without `out=`, `allocate_output` is used exactly once per field.
3. `CallingFrequency` semantics: piecewise-constant output verified against hand computation over 20 steps with dt_proc = 3·dt; phase survives a `restart_state`→`load_restart_state` round trip bit-exactly.
4. Strict mode end-to-end: a component declaring non-canonical units raises at construction (static), a state with transposed dims raises at call (dynamic) — messages name field + component.
5. `Subcycle(ratio_provider=...)` calls the provider once per outer step with the current state and honors the returned integer.
