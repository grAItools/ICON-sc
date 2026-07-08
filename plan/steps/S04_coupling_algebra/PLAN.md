# S04 — Plan

1. **Mine Tasmania.** Read `tasmania` federation classes, `STSTendencyStepper`/sequential-tendency stepper, `DynamicalCore` (stage/substep pipelining), and its `DataArrayDictOperator`. Port semantics onto S03's ABI; where Tasmania and the thesis text disagree, the thesis equations (2.8–2.13) win — cite equation numbers in docstrings.
2. Implement steppers first (pure functions of (coupling, state, dt) using S03 machinery); verify each stepper's own order on ψ' = λψ before touching federations.
3. Federations: keep them thin sequencers over components + steppers; recombinations via a small `dict_axpy` helper (numpy-level; S05 will compile it away).
4. `DynamicalCore`: implement the tier scheduling exactly per Tasmania Fig. 3.10 (fast tendencies evaluated per stage; super-fast coupling per substep); ratio provider hook shared with `Subcycle`.
5. Order-verification harness: generic `measure_order(builder, dts, exact)` in `symcon.core.testing`; used again in validation/L7 later. Plot artifacts (matplotlib, saved to step artifacts dir) for the human gate — reviewers eyeball the convergence lines.
6. Constraints + bus checker; unit tests.

**Pitfalls:** the STS forcing uses ψⁿ (the step-initial state) in *every* section, not the previous section's state — easy to get subtly wrong and still converge at order 1 on friendly problems; the ODE system in acceptance 1 is chosen because it exposes this (add a regression test asserting the intermediate forcing values on one hand-computed step). SSUS reverse pass order and λ/(1−λ) split per eq. (2.13a–e) exactly.
