# S07 — Plan
1. Discover the granule: search pinned icon4py for saturation adjustment (expect it under the microphysics / subgrid-scale-physics package; it exists with its own tests + serialized data). Read its field interface, the Fortran `mo_satad.f90` for algorithm ground truth (Newton on T with latent-heat closure), and icon4py's test for tolerances + fixtures. Lock everything.
2. Build `ingress/gt4py.py`: backend object bundling program processor + `as_field` + offset-provider hook (empty dict for the column). Keep icon4py's granule invocation *as their tests invoke it* — do not re-plumb their internals.
3. Component: contracts from the granule's actual field list; `array_call` = ingress views → granule program call → done (outputs preallocated by caller).
4. Tests: bridge icon4py fixtures; port their assert pattern through `assert_allclose`.
**Pitfalls:** formulation mismatch (T-based vs θv/exner-based) between granule variants — pick the one with serialized reference data and record the choice; don't silently convert with cpd where ICON's satad path implies cvd bookkeeping (check `mo_satad` commentary).
