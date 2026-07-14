# S08 — Graupel microphysics component (L2)

**Lane:** A · **Depends on:** S06 (+S03, S07's `ingress.gt4py` — coordinate: whichever step lands first owns it) · **Parallel with:** S07

## Goal
`Microphysics(Stepper)` (single-moment graupel scheme) via the icon4py graupel granule; L2 parity against serialized ICON reference; the second — and structurally last — pattern-setting gt4py physics component.

## In scope
`symcon/icon/components/fast/microphysics.py`: contracts (T, ρ, p/exner, qv qc qi qr qs qg in/out; precipitation-rate diagnostics; dz from VerticalGrid via static-state input); scheme selectable by registry name (`"graupel"` only, for now); `differentiable:"native"` declared (JAX core lands in S10); sedimentation/level-loop structure preserved exactly as the granule has it.

## Acceptance criteria
1. L2 parity vs icon4py graupel reference data at icon4py's own tolerances (embedded + gtfn_cpu; gpu marker for gtfn_gpu).
2. Conservation checks on random admissible columns: total water (Σq·ρ·dz + accumulated precip flux) conserved to scheme-documented tolerance; negativity: no tracer < 0 beyond clipping epsilon.
3. Performance smoke: gtfn_cpu ≥ 5× embedded on a 10k-column batch (regression tripwire, not a target).
4. Component test file structure mirrors S07 exactly — the diff between the two test modules should be ≲ field lists (pattern discipline for P3's remaining physics).
