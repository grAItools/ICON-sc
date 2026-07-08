# S04 — Coupling algebra + DynamicalCore base

**Lane:** trunk · **Depends on:** S03 · **Unblocks:** S05, S09, S12

## Goal
The §4.2 Tasmania layer: `ConcurrentCoupling`, registry-based `TendencyStepper` family incl. `SequentialTendencyStepper`, the four federations (PS/STS/SUS/SSUS), the tendency-bus checker, coupling constraints, and the `DynamicalCore` base class with its three cadence tiers. Verified by measured convergence orders (ladder L7-cheap).

## In scope
`coupling/concurrent.py` · `coupling/steppers.py` (registered: `forward_euler`, `rk2` (Heun), `rk3ws` (Wicker–Skamarock), `ssprk3`; `SequentialTendencyStepper` two-state signature `E(ψⁿ, Δt; P + (ψ_prov−ψⁿ)/Δt)`) · `coupling/federations.py` (`ParallelSplitting` with the Σψₗ − L·ψⁿ recombination; `SequentialTendencySplitting`; `SequentialUpdateSplitting` accepting bare `Stepper`s or `(TendencyComponent, stepper_name)` pairs; `SSUS(sections, core, lam, pre_steppers=None)` built from two SUS passes, reverse order first, per-side steppers) · `coupling/bus.py` (slot declaration; composition-time single-consumer check) · `coupling/constraints.py` (`must_follow`/`must_precede`/`admissible_operators` on components; validated when a federation is constructed) · `components/dycore.py` (`DynamicalCore`: slow-tendency input port declared via input_properties; optional per-stage `fast_tendency_component: ConcurrentCoupling`; super-fast substep tier with `stage_array_call`/`substep_array_call` hooks and ratio provider — Tasmania Fig. 3.9/3.10 semantics).

## Frozen interfaces
Constructor signatures exactly as named above; every federation is itself a component (composable). `TendencyStepper.factory(name, coupling)` via S02 registry. `DynamicalCore` subclass contract: implement `stage_array_call(stage, inputs, outputs, dt)`, `substep_array_call(...)`, declare `n_stages`, `substep_fraction`.

## Acceptance criteria (the step lives or dies on these)
1. **Order verification on a stiff-ish 2-process linear ODE system** (D = rotation, P₁ = relaxation, P₂ = damping; closed-form solution): measured self-convergence slopes over Δt ∈ {T/64…T/1024}, fp64, with RK2 as every Eₗ: FC ≈ 2.0; LFC ≈ 1.0; PS ≈ 1.0; STS ≈ 1.0; SUS ≈ 1.0; SSUS(λ=½) ≈ 2.0; SSUS(λ=0.3) ≈ 1.0. Slope tolerance ±0.15. (Thesis §2.4 expectations.)
2. **1-D viscous Burgers with a relaxation "physics" term** (thesis §2.5.2 spirit): same order pattern reproduced on a PDE; numpy implementation, N=512.
3. SUS honors `must_follow` (constructing a violating order raises with both component names); bus checker rejects a published tendency slot with 0 or 2 consumers.
4. `DynamicalCore` toy subclass (2-stage RK, substep_fraction=1/3) produces the Tasmania Fig. 3.10 call sequence — assert exact hook-invocation order via recording mocks; slow-port tendencies held constant across stages; per-stage fast coupling invoked once per stage.
5. `SSUS` with `pre_steppers` ≠ post steppers runs (Eₗ* ≠ Eₗ legality).
