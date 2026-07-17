# L8 — gradient verification (architecture §9, seeded by S10)

For every `native`/`custom` component and for composed windows: Taylor-remainder
tests for `jvp` (first-order remainder decays at slope 2), adjoint-consistency
dot-product tests `⟨Jv, w⟩ = ⟨v, Jᵀw⟩` to fp64 tolerances (per component and
through multi-step `scan` windows — through the satad implicit-function rule),
and finite-difference cross-checks on scalar functionals. Long-window gradient
growth is *characterized, not gated* — sensitivity blow-up over chaotic horizons
is physics, not a defect.

## Contents

- `run_l8.py` — the runnable battery at column scale (S10 slice: satad IFT,
  graupel scan core, the SCM `scan_window`): prints the Taylor/dot-product/FD
  table and writes remainder-decay plots to `artifacts/` (gitignored).

The CI-gating form of these checks lives in the package test suites
(`packages/icon-sc-icon/tests/test_satad_functional.py`,
`test_graupel_functional.py`, `test_scm_functional.py`,
`packages/icon-sc-core/tests/test_functional_*.py`); this directory is the
human-runnable/plotting harness on top of the same
`icon_sc.core.testing.gradients` machinery, extended per level as later steps
add components (P6 wires it into the ladder proper).

## Run

```
uv run python validation/L8_gradients/run_l8.py
```
