# S07 — Saturation adjustment component (L2)

**Lane:** A · **Depends on:** S06 (+S03) · **Parallel with:** S08

## Goal
`SaturationAdjustment(Stepper)` on the column/grid state, implemented by the icon4py saturation-adjustment granule, with ladder-L2 parity against icon4py's serialized ICON reference data.

## In scope
`icon_sc/icon/components/fast/satad.py`: property contracts (in: T or θv/exner per chosen formulation, qv, qc, ρ; out: adjusted T/qv/qc; `differentiable:"custom"` declared now, rules deferred to S10); gt4py-backend ingress via S02 plans wired to real gt4py `as_field` (first real backend — extend `ComputeContext` backend from opaque string to a small backend object: gt4py program processor + allocator, in `icon_sc/core/ingress/gt4py.py`). `coupling_constraints`: `admissible_operators={SUS}` position notes per tutorial §3.7.2.

## Frozen interfaces
`SaturationAdjustment(grid_or_column, cfg, ctx)`; state names from S06 registry; `ingress.gt4py.make_backend(name) -> Backend` used by every later gt4py component.

## Acceptance criteria
1. **L2 parity:** outputs match icon4py's own satad verification data (their serialbox savepoints / reference fixtures) to the tolerances icon4py's tests use — record those tolerances in the test as constants with provenance comments. Backends: embedded + gtfn_cpu; gtfn_gpu under `gpu` marker.
2. Zero-copy: pointer identity between vault buffer and gt4py field `.ndarray` for numpy and cupy paths.
3. Fixed-point property: applying satad twice changes nothing beyond 1e-12 (idempotence on adjusted states).
4. Standalone usability: the sympl Fig.-1 pattern (`satad(state)`) works interactively on an S06 test column.
5. `out=` path exercised (S03 acceptance 2 repeated on a real component).
