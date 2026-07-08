# S12 — NonhydroSolver hosting (DynamicalCore over icon4py solve_nonhydro)

**Lane:** B · **Depends on:** S04, S11 · **Unblocks:** S13

## Goal
`NonhydroSolver(DynamicalCore)`: the icon4py nonhydrostatic solver + velocity advection hosted as one symcon component — predictor/corrector as stages, `ndyn_substeps` as the super-fast tier, slow-tendency bus port declared, private time levels + carry behind the restart/functional-state protocols — verified against icon4py's solve_nonhydro savepoints.

## In scope
`symcon/icon/components/dycore.py`. Contracts: prognostics (vn, w, ρ, exner, θv) in/out on their locations; static-state metric/interpolation inputs (enumerate — this list is the S11 coordination point); bus inputs `icon:ddt_vn_phy`, `icon:ddt_exner_phy` (zero-filled default so the JW run needs no physics); config dataclass mirroring the slice-relevant ICON namelist knobs (`igradp_method`, `divdamp_order`, `itime_scheme`, rayleigh, …) with `icon_namelist_origin` annotations. Substep tier: fixed ratio + `ratio_provider` hook (CFL diagnostics exposure may stub to fixed for the slice — declare). `restart_state()`: both time levels + velocity-advection carry; `functional_state()`: same schema (F-tier consumption is P6, declaration is now).

## Acceptance criteria
1. **Savepoint parity:** driving the component with icon4py's serialized solve_nonhydro input savepoints reproduces their output savepoints at icon4py's tolerances, for ≥ the first and a mid-run timestep, single substep and multi-substep cases as their data provides (marker `data`; backends embedded + gtfn_cpu, gpu-marked gtfn_gpu).
2. Stage/substep orchestration: hook-order recording matches ICON's documented sequence (predictor→corrector per substep; velocity advection reuse across substeps per icon4py's flags) — assert against a hand-written expected sequence for ndyn_substeps=2.
3. Restart: run 5 steps → serialize → restore → 5 more ≡ 10 straight, bitwise fp64.
4. Bus consumption: constant synthetic `ddt_vn_phy` shifts vn by the analytically expected increment over one Δt within tolerance (linear-response smoke).
5. Standalone: component constructible and callable without any federation (sympl first-class-component property).
