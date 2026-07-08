# S05 — Plan

1. Vault + façade first (façade reuses S02 `make_dataarray`, cached per slot, epoch-invalidated).
2. `ops.py`: frozen slotted dataclasses / NamedTuples only; document each op's exact semantics in its docstring — T2/T3 emitters (post-slice) will treat these docstrings as normative.
3. `bind.py`: reuse S03's cached DynamicalChecker/IngressPlan machinery to produce bound argument packs; walk the composition tree via a `visit(plan_builder)` protocol implemented by every S03/S04 container (add the protocol to those classes here — small, mechanical). Compute step signatures from S02 cadence lcm/phase; emit one op list per signature; even/odd variants only where a Swap exists.
4. Interpreter: a for-loop over ops with match on op type; keep it boring and measurable.
5. Guards + plan_hash (hash over canonical serialization of ops with names, not object ids).
6. Equivalence + zero-traffic + benchmark tests. The settrace test is fiddly: scope the trace to `run_step` frames only and assert on qualified names; mark `slow`.

**Pitfalls:** federations already executed correctly in T0 — the compiler must reproduce *their* semantics, so derive expected op lists in tests from hand-worked examples (write the expected op list literally for one SUS+PS+SSUS toy each). Bitwise T0≡T1 requires identical reduction orders in Axpy — implement `dict_axpy` (S04) and the Axpy op over the same kernel.
