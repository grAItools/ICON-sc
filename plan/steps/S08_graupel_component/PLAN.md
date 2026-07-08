# S08 — Plan
1. Discover the icon4py graupel granule + its verification data; read ICON Fortran `gscp_graupel`/`mo_gscp_*` for ground truth; check the C++ `muphys` rewrite (if locatable) only as a tie-breaker on ambiguities. Lock.
2. Reuse S07's ingress/backend and test scaffolding verbatim (copy-adjust; note divergences in STATUS.md — convergence of the two files is the review criterion).
3. Contracts: take the granule's field list; precipitation diagnostics via `diagnostic_properties`.
4. Conservation tests: hypothesis-generated admissible columns (bounded T, positive q's, hydrostatic-ish p).
**Pitfalls:** graupel variants (with/without ice sedimentation options, lookup-table vs analytic saturation) — pin the exact configuration flags the serialized data was produced with; dz sign/orientation conventions (ICON counts levels top-down).
