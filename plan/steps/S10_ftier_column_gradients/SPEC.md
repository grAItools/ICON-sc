# S10 — F-tier on the column + gradient verification (L8)

**Lane:** A (trunk-merging) · **Depends on:** S05, S09

## Goal
The §8.5–8.6 differentiability layer, proven at column scale: StateTree/ParamTree from the vault schema, functional compile of the SCM composition, `native` functional core for graupel, `custom` (implicit-function) rule for satad, and the full L8 battery — `jax.jvp`/`jax.vjp` of a multi-step SCM window as a passing test.

## In scope
`symcon/core/functional/pytree.py` (generated frozen-dataclass StateTree from schema + explicit carry from `functional_state()`; ParamTree from `params` declarations) · `functional/compile.py` (composition → pure `step_fn`; SUS chaining, bus slots, cadence-as-carry+`jnp.where`; `scan_window(step_fn, n, remat)`) · `functional/rules.py` (`custom_root`/IFT helper for fixed points; `custom_vjp` registration scaffolding) · graupel functional core co-located in `microphysics.py` sharing `_constants.py` (S06 thermo already array-API generic — reuse) · satad: `custom` route via IFT on the saturation fixed point (adjoint of the Newton solve through implicit differentiation, NOT unrolled) · `examples/07_gradient_scm.py` (vjp of accumulated precipitation w.r.t. an autoconversion parameter in ParamTree) · `validation/L8_gradients/` seeded.

## Acceptance criteria
1. Functional-core parity (L2 restated): graupel JAX core vs the gtfn kernel on the S08 reference data, fp64, rtol ≤ 1e-10 (identical constants module ⇒ this is achievable; any relaxation needs STATUS justification).
2. **Taylor tests** (jvp): remainder of first-order expansion decays at slope 2.0±0.1 over 6 halvings, per component and for a 10-step `scan_window`.
3. **Dot-product test** (adjoint consistency): |⟨Jv,w⟩−⟨v,Jᵀw⟩| / (|⟨Jv,w⟩|+ε) ≤ 1e-10 fp64, per component and through the window — including through the satad IFT rule.
4. FD cross-check on the example's scalar functional: central-difference vs vjp gradient, rtol ≤ 1e-6 at optimal FD step.
5. `stop_gradient` policy: marking satad `none` and compiling with `policy="error"` raises naming the component; `policy="stop_gradient"` compiles, warns, and stamps provenance.
6. `donate_argnums` path verified (jit with donation runs; memory not asserted, only functionality).
7. T0 ↔ F-tier forward equivalence on the SCM window: rtol ≤ 1e-10 fp64 (different kernels ⇒ not bitwise).
