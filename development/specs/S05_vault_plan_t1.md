# S05 — StateVault, plan compiler, T1 interpreter

**Lane:** trunk · **Depends on:** S04 · **Unblocks:** S10, S14

## Goal
The §8.2 negotiation/execution split: vault, ops algebra, bind-time compiler that dissolves wrappers and federations, even/odd swap variants, cadence masks, staleness guards, and the T1 interpreter — proven equivalent to T0 and measurably free of dict/xarray traffic.

## In scope
`plan/ops.py` (`BoundCall`, `Swap`, `Axpy`, `DiffScale`, `CadenceMask`, `SegmentMarker`; nothing else) · `plan/bind.py` (composition walk shared with the — post-slice — halo validator; per-signature op lists; federation/wrapper dissolution per §8.2: SUS flattens, PS → one k-ary Axpy, STS → provisional slots + DiffScale, SSUS → doubled reversed λ-scaled list, CallingFrequency → cadence masks with caches as vault slots, Subcycle/DynamicalCore substeps → unrolled or looped with bound dt) · `plan/interpreter.py` · `plan/guards.py` (schema hash; epoch on the façade; debug renegotiate-and-diff every N steps) · `state/vault.py` + `state/facade.py` (lazy DataArray view, epoch-invalidated) · `context.py` gains `tier: "interpret"|"plan"` and `ctx.timeloop(...)` performing bind.

## Frozen interfaces
```python
StateVault.from_state(state) -> StateVault;  vault.facade() -> Mapping[str, xr.DataArray]
ExecutionPlan.bind(composition, schema, ctx) -> ExecutionPlan   # signatures: plan.signatures
plan.run_step(vault, step_index) -> None
plan.plan_hash -> str   # stable across processes/runs for identical (composition, schema, ctx)
```

## Acceptance criteria
1. **T0 ≡ T1** on: (a) the S03 toy loop, (b) every S04 federation over the toy processes, (c) a CallingFrequency + Subcycle composite — bitwise equality in fp64 over 100 steps (same kernels, same order ⇒ bitwise is achievable and required).
2. Even/odd correctness: a composition with an explicit swap runs 101 steps (odd count) and matches T0.
3. Zero-traffic assertions: sys.settrace-based test proves no `dict.__getitem__` on state names and no `xarray` frames inside `run_step`; allocation tracker (tracemalloc) shows zero Python-level allocations per step after warmup for the toy plan.
4. `plan_hash` stable across two processes; changes when any config field, component order, or schema entry changes.
5. Guards: mutating the façade between steps raises StalePlanError on the next `run_step`; debug mode renegotiate-diff passes on the toys.
6. Microbenchmark artifact: per-step dispatch cost T0 vs T1 for 20 toy components (report, no hard threshold — but record in STATUS.md).
