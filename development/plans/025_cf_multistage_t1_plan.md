# Task 25 — CF under multi-stage schemes at T1 (per-stage cache-slot aliasing)

> **⚠ Difficulty warning.** This is the hardest prompt in this set — it modifies the
> S05 plan compiler's cell-ownership model, whose central contract is BITWISE
> T0≡T1. A previous strong-model attempt at the "obvious" fix was correctly
> rejected by the compiler's own corruption guard (see History). Prefer a
> strong model; if a weaker model attempts it, the stop rules below are load-bearing.
> A fully acceptable outcome of this task is a WRITTEN DESIGN + failing-guard
> analysis with NO code change, if the implementation risks the bitwise contract.

**Branch:** `task/25-cf-multistage-t1` (from `main`).

## History (read first, verbatim sources)

- S05 restriction: a `CallingFrequency` wrapper whose section uses a multi-stage
  scheme (rk2/rk3ws/ssprk3) is rejected at bind time. T0 handles it fine (the
  stepper re-evaluates its coupling once per stage; CF replays its cache on
  stage > 0 because `state["time"]` has not advanced).
- The rejection lives in `packages/symcon-core/src/symcon/core/plan/bind.py`,
  `visit_calling_frequency` — the `_seen_cf` guard (search `_seen_cf`). Its error
  message already names this task as the fix ("per-stage cache-slot aliasing").
- **The failed quick fix (do not repeat):** keying `_seen_cf` by
  `(id(wrapper), stage)` lets the visit proceed, but the stage>0 re-dispatch of the
  wrapped component re-registers its cadence-masked diagnostic cells under a second
  path, and the compiler's cell-write corruption guard (bind.py, search
  `"persistent-cache slot would be corrupted"`) rightly rejects that. See
  `development/records/005_vault_plan_t1_record/STATUS.md` "Review fixes (round 1)" for the record.
- Loud-rejection regression tests exist and MUST keep passing until the feature
  works, then be CONVERTED (not deleted):
  `packages/symcon-core/tests/test_plan_equivalence.py::test_calling_frequency_under_multi_stage_scheme_is_rejected_loudly`
  and the forward_euler-variant bitwise test next to it. The builder they use is
  `make_cf_multistage(scheme)` in `packages/symcon-core/tests/_plan_toys.py`.

## The design requirement (what "per-stage cache-slot aliasing" must mean)

At T0, stage>0 evaluations of the CF read the SAME cached arrays its stage-0 fire
wrote. Therefore at T1:
1. The CF's cadence-masked ops (the fire) are emitted ONCE, at stage 0 — this
   already works (`fires = ... and ev.stage == 0`).
2. Stage>0 evaluations must BIND THEIR READS to the very cells the stage-0 mask
   writes — no re-registration of those cells, no second write path, no new cells.
   Concretely: the stage>0 dispatch of the wrapped component must be replaced by a
   read-only aliasing step that resolves the component's output fields to the
   existing persistent cache cells and records them as inputs of the enclosing
   stage evaluation — WITHOUT calling `_dispatch(wrapper.component)` again (that is
   what re-registers cells).
3. The resulting plan must be bitwise T0≡T1 — the stage sums must consume exactly
   the cached values, in the same accumulation order as T0's ConcurrentCoupling.

## Stop rules (in priority order)

- If after implementing, ANY test in `test_plan_equivalence.py` fails — including
  your new ones flaking between runs — STOP. Do not weaken any assertion, do not
  add tolerances (bitwise means `assert_array_equal`). Either fix the compiler or
  fall back to the design-document outcome.
- If you find yourself modifying the corruption guard's logic to "let it through",
  STOP — the guard is correct; the fix must make re-registration not happen, not
  make the guard blind. Any diff to the guard block is out of bounds.
- If the change grows beyond `visit_calling_frequency` + one new helper + tests,
  STOP and write the design document instead.

## Implementation sketch (follow unless you produce a written better argument)

In `visit_calling_frequency`: keep the existing single-visit path for
`ev.stage == 0` unchanged. For `ev.stage > 0` with the SAME wrapper instance
already seen at stage 0 of this phase (track `{id(wrapper): stage0_cells}` where
`stage0_cells` maps the wrapped component's output field names → cell sids,
captured after the stage-0 dispatch): do NOT dispatch the component; instead call
the same cell-consumption bookkeeping the enclosing evaluation applies to ordinary
component outputs, feeding it `stage0_cells` (find where the evaluation records
member outputs — the ConcurrentCoupling visit — and factor the smallest possible
helper so both paths share it). A wrapper seen twice at the SAME stage keeps
raising the current error (true duplicate occurrence).

## Tests (definition of done)

1. CONVERT the loud-rejection test: `make_cf_multistage(scheme)` for rk2, rk3ws,
   ssprk3 must now BIND and be **bitwise T0≡T1 over 100 and 101 steps**
   (`assert_states_bitwise_equal`, both even/odd, mirroring the forward_euler
   variant test that already exists). Keep a loud-rejection test ONLY for the
   still-unsupported true-duplicate case (same CF instance twice in one stage).
2. A cadence-phase interaction test: period 3Δt under rk3ws, 7 steps, asserting the
   fire/replay pattern matches T0 step-by-step (compare full state each step, not
   only at the end — lockstep loop like `test_jw_plan_equivalence.py` does).
3. All S05 regression files pass unmodified apart from the sanctioned conversion
   in (1): `test_plan_swap.py`, `test_plan_hash.py`, `test_plan_guards.py`,
   `test_plan_zero_traffic.py`, `test_plan_dycore_substep_outer.py`,
   `test_plan_publication.py`.
4. The S09 SCM and S14 JW/SCM plan tests pass unmodified (they don't use CF under
   multi-stage, so any change there means you broke something general).

## Acceptance criteria

Either (A) feature complete: tests 1–4 green + full README gate green + report
`development/records/25_cf_multistage_REPORT.md` describing the cell-aliasing
mechanism and why the corruption guard stays intact; or (B) design outcome: no
code change (or a reverted branch), plus the report containing the attempted
approach, the exact guard/equivalence failure evidence, and a concrete design for
a stronger model. Both outcomes are acceptable; a merged half-working compromise
is not.

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Outcome A: run the converted bitwise tests 3× (flake check); diff-inspect that
  the corruption guard block is byte-identical to main
  (`git diff main..HEAD -- packages/symcon-core/src/symcon/core/plan/bind.py` and
  read every hunk); verify no `allclose` entered any equivalence test; run the
  full fast gate + `test_plan_*` files yourself; verify the true-duplicate case
  still raises.
- Outcome B: verify the branch leaves `main`'s behavior untouched (empty diff or
  report-only), and that the report's failure evidence actually reproduces (run
  the described probe once).
- Either outcome: any tolerance or assertion weakening anywhere = MAJOR.
