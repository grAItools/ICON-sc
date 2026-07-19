# S12 — Plan
1. Mine icon4py dycore package: the SolveNonhydro/velocity-advection classes, their init (static fields, config), their per-substep call signature, and — critically — their datatest savepoint tests; the hosting component should invoke the granules the way those tests do. Read ICON `mo_solve_nonhydro.f90` + `mo_nh_stepping.f90` only to confirm sequencing semantics (substep loop, where slow tendencies enter), not to reimplement.
2. Map icon4py's config dataclasses ↔ ICON-sc config; annotate namelist origins.
3. Time-level privacy: own two prognostic buffer sets inside the component; expose single-level state at the boundary; swap internally per substep. Restart schema = exactly the internal buffers + substep bookkeeping.
4. Bus port: additive application point per ICON semantics (vn tendency inside substeps; exner per its documented path) — cite tutorial §3.7 lines in comments.
5. Savepoint test bridge mirroring S07's fixture pattern.
**Pitfalls:** savepoint field naming/staggering mismatches (icon4py savepoints use ICON short names — go through the registry); do not leak icon4py's own grid/state objects across the component boundary (ingress views only); ndyn_substeps in the savepoints is fixed — assert the config matches the data's provenance before comparing.
