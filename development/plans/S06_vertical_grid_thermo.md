# S06 — Plan
1. Mine: ICON Fortran `mo_physical_constants.f90`, `mo_vertical_grid.f90`; icon4py `common` for its vertical grid/params classes and datatest fixtures (discover paths; lock). Prefer *reusing* icon4py's vertical-grid object internally and adapting it behind `VerticalGrid` — write, don't wrap, only if its API resists.
2. `_constants.py`: one flat module; every constant with a comment citing the Fortran symbol. This module is the future shared-constants pattern (layout §5) — set the precedent.
3. `thermo.py` via the array-API namespace (`array_api_compat`) so the same functions serve numpy/cupy now and JAX in S10 — this is deliberate: S10 imports these *unchanged* as the start of functional cores.
4. Registry seed from a literal table; generate the docs page in `docs/` from it (script in `tools/names_audit.py` skeleton).
5. Column builders + fixture bridge to icon4py datatest (their pytest plugin handles download/caching; depend on it rather than re-hosting).
**Pitfalls:** ICON uses cvd-based isochoric coupling downstream — expose both cpd and cvd paths in thermo now and name them unambiguously; unit of exner is "1" — resist "dimensionless" string drift in the registry.
