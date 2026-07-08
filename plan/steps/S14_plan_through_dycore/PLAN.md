# S14 — Plan
1. Extend `plan/bind.py` visitors for `DynamicalCore` (substep loop → per-substep op sequence with internal swaps; keep the private buffers inside the component's BoundCalls — the vault only holds boundary fields, per §8.2/§4.5).
2. Monitor handling: plan emits SegmentMarkers; interpreter yields to a host callback between segments — the minimal seam T2 will need (design note in docstring, no T2 code).
3. Benchmarks with `pyperf`-style repetition; gpu path records launch counts (informational — motivates P5).
4. Plan-hash tests; wire the two builders.
**Pitfalls:** the dycore's per-substep internal swap must not leak into vault even/odd variants (only boundary swaps do); verify with the S05 hand-worked-op-list technique on ndyn_substeps=2 before running the full model.
