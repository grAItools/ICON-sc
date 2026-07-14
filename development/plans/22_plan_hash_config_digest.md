# Task 22 — Fold a component-config digest into `plan_hash` (S05/S10/S14 follow-up)

**Branch:** `task/22-plan-hash-config-digest` (from `main`; verify
`git branch --show-current` before every commit).

## Why

`ExecutionPlan.plan_hash` (S05) is a stable content hash of the symbolic plan, used
for cross-process identity, `renegotiate_and_diff`'s hash-first comparison, the
S14 plan-hash pins tying example scripts to preset builders, and (future, T3/P5)
caching compiled artifacts by hash. **Known blind spot, documented since S05 and
re-flagged in S10/S14 STATUS:** two compositions differing only in a component's
constructor parameters (e.g. `Relaxation(tau=30min)` vs `tau=5min`) hash
identically, because `_DraftCall` carries only tag/slots/dt (`component` is
`compare=False`). T3 must never serve a cached binary for a different tau.

## Hard rules (restated; full list in development/plans/README.md)

- This touches S05 core code (`packages/symcon-core/src/symcon/core/plan/bind.py`).
  The **frozen interfaces may not change**: `ExecutionPlan.bind(composition, schema,
  ctx)`, `plan.signatures`, `plan.run_step(vault, step_index)`, `plan.plan_hash`
  (property, returns a hex string). Only the hash PREIMAGE grows.
- **The T0≡T1 bitwise equivalence suites are untouchable** — you change nothing
  about op emission, ordering, or numerics. If any equivalence test fails after
  your change, your change is wrong; revert and rethink. Never touch a tolerance.
- Hash values WILL change (that is the point). The repo stores NO persisted plan
  hashes as fixtures (S14 review verified this; re-verify with
  `grep -rn "plan_hash" packages --include="*.py" | grep -v "\.py:" ` style searches
  before starting — the plan-hash tests compare two live hashes, never a hash to a
  string literal). If you DO find a hardcoded hash literal anywhere, STOP and
  report before proceeding.
- Determinism is a contract: the hash must be identical across processes and
  `PYTHONHASHSEED` values. No `repr()` of floats without `.hex()`, no dict
  iteration without sorting, no `id()`, no timestamps.

## Design (follow exactly; deviations need a written justification in your report)

1. **Digest source.** Each component occurrence contributes a config digest derived
   from, in priority order:
   a. `component.config` if it is a frozen dataclass (the repo convention:
      `GraupelConfig`, `SaturationAdjustmentConfig`, `NonhydroConfig`,
      `DiffusionConfig`, `SCMConfig` fields...) — serialize with
      `dataclasses.asdict`, then canonicalize (rule 3);
   b. else, public scalar attributes set at construction — DO NOT invent a general
      introspection; instead add an optional, documented protocol:
      `plan_config_fingerprint(self) -> Mapping[str, object]` that components MAY
      implement; S03 toys get it via their existing scalar attrs (`tau_seconds`,
      `equilibrium`, ...) — add it to the toys in `testing/toys.py` and
      `_coupling_toys.py`;
   c. else (no config, no protocol): contribute the stable marker string
      `"<no-config>"` — never an error.
2. **Where it enters the preimage.** In `_DraftCall.describe()` (bind.py), append
   ` cfg=<digest>` where `<digest>` is the first 16 hex chars of sha256 over the
   canonical serialization. Compute it ONCE per component occurrence at draft
   creation (store on the draft as a `compare=False`-excluded... NO — it must be
   compared; store it as a normal field `config_digest: str`), not per describe()
   call.
3. **Canonical serialization rules** (write these as a small pure function
   `_canonical_config_bytes(mapping) -> bytes` with unit tests):
   - keys sorted lexicographically; nested mappings recursively canonicalized;
   - floats rendered via `float.hex()`; ints as decimal; bools as `true|false`;
     `None` as `null`; strings UTF-8; `timedelta` as integer microseconds;
     `datetime`/cftime as ISO string; enums by `.value`;
   - tuples/lists element-wise; numpy scalars via `.item()` then the above;
   - any OTHER type: its `str()` is NOT acceptable — raise `PlanCompileError`
     naming the component, the key, and the type, so unstable configs fail loudly
     at bind time instead of hashing unstably.
4. **Tests to add** (extend `packages/symcon-core/tests/test_plan_hash.py`):
   - two toy loops differing ONLY in `Relaxation(tau=...)` now produce DIFFERENT
     `plan_hash` (this is the S05-documented blind-spot closure — cite it in the
     test docstring);
   - identical configs still produce IDENTICAL hashes cross-process under
     different `PYTHONHASHSEED` (extend the existing subprocess test's composition
     to include a configured component);
   - the loud-failure path: a component whose fingerprint contains an unsupported
     type raises `PlanCompileError` naming component+key+type;
   - unit tests for `_canonical_config_bytes` covering every rule-3 type incl.
     float `.hex()` stability and nested-mapping sorting.
   And in `packages/symcon-icon/tests/`: extend the existing S14 knob tests
   minimally — `test_scm_plan.py`/`test_jw_plan.py` already vary 3 knobs each; add
   ONE more knob case per file that previously hashed identically (e.g. graupel
   `GraupelConfig` scalar for SCM; a `NonhydroConfig` scalar for JW) and assert the
   hashes now differ.
5. **Docs**: update the `plan_hash` docstring (bind.py) to state the preimage now
   includes per-occurrence config digests and name the protocol; update the S05
   blind-spot mentions ONLY in living docs you own (your report) — do NOT edit
   S05/S10/S14 STATUS files (historical records).

## What NOT to do

- Do not hash the component object, its `repr`, `__dict__`, or pickle bytes.
- Do not add config digests to `signatures`, ops, the interpreter, or the vault —
  ONLY the hash preimage.
- Do not "clean up" bind.py beyond the minimal insertion.

## Acceptance criteria

1. The two-taus test proves the blind spot closed; the cross-process test proves
   determinism; the loud-failure test proves no unstable hashing is possible.
2. ALL pre-existing plan tests pass unmodified — especially
   `test_plan_equivalence.py` (bitwise), `test_plan_swap.py`, `test_plan_hash.py`
   sensitivity tests, `test_plan_zero_traffic.py`, and the S14 files
   (`test_plan_dycore_substep_outer.py`, `test_plan_publication.py`,
   `test_scm_plan.py`, `test_jw_plan.py`, `test_jw_plan_equivalence.py` non-slow).
3. Full gate green (README baselines, adjusted only by YOUR added tests — state
   exact new counts).
4. Report `development/records/22_plan_hash_REPORT.md`: design conformance,
   any justified deviation, new gate baselines.

## Verification gates

All 8 README commands, plus explicitly:
```
uv run pytest packages/symcon-core/tests/test_plan_hash.py -q                       # all pass incl. new
uv run pytest packages/symcon-core/tests/test_plan_equivalence.py -q                # 34+ passed, bitwise untouched
uv run pytest packages/symcon-icon/tests/test_scm_plan.py packages/symcon-icon/tests/test_jw_plan.py -q -m "not gpu and not slow"
PYTHONHASHSEED=1 uv run pytest packages/symcon-core/tests/test_plan_hash.py -q      # rerun; then PYTHONHASHSEED=7
```

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Verify determinism yourself: run the hash test file under two different
  `PYTHONHASHSEED` values and diff the printed hashes if the tests expose them
  (or add a scratch script under /tmp that binds the same composition twice in
  separate `uv run python` processes and compares `plan_hash`).
- Verify the blind-spot closure NEGATIVELY: on a /tmp scratch script, bind two
  compositions with identical configs → hashes MUST be equal (the digest must not
  accidentally include object identity).
- Read `_canonical_config_bytes` against rule 3 line by line; any `str(obj)`
  fallback for arbitrary objects is a MAJOR finding.
- Confirm zero diffs in `packages/symcon-core/src/symcon/core/plan/interpreter.py`,
  `ops.py` (except possibly none at all), and zero test-file modifications other
  than ADDITIONS to the named files.
- Run the bitwise equivalence file yourself; any change in its assertions is MAJOR.
