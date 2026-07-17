# S09 — SCM composition (SUS column model)

**Lane:** A · **Depends on:** S04, S07, S08 · **Unblocks:** S10

## Goal
The first scientifically meaningful ICON-sc model: a single-column configuration coupling satad → graupel → satad by `SequentialUpdateSplitting`, with a `CallingFrequency`-wrapped toy slow forcing publishing to the tendency bus — the entire §5.1 shape at column scale, running under T0.

## In scope
`icon_sc/icon/presets/scm.py` (`SCM_FAST_ORDER = ["satad", "mphys", "satad"]` with constraints; preset builder returning composition + initial state) · `examples/01_scm_column.py` (legible script, runs in <60 s CPU) · a `PrescribedCooling(TendencyComponent)` slow process (radiative-cooling stand-in publishing `icon:ddt_temperature_slow`) consumed by a trivial `ApplySlowTendencies(Stepper)` — the bus mechanics exercised end-to-end before a real dycore consumes them · NetCDFMonitor output wired.

## Acceptance criteria
1. `examples/01_scm_column.py` runs green as a CI smoke test; output NetCDF contains declared variables with registry units.
2. **L3-lite stability:** 48 simulated hours at dt=30 s on a moist unstable column: no NaN/Inf, tracers ≥ 0, total water conserved to graupel-scheme tolerance + accumulated precipitation.
3. Bus mechanics: cooling tendency held piecewise-constant (dt_slow = 10·dt) — assert exact step-function time series; bus checker rejects the preset if the consumer is removed.
4. Order sanity: swapping SUS section order against a `must_follow` constraint raises at composition.
5. Column regression fingerprint: hash of final-state selected fields committed as a golden value with fp64 exact match on same platform (platform-tagged; this is a change-detector, not a science claim).
