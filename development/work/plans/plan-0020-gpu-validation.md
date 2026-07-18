# Task 20 — First execution of the gpu-marked test legs on a CUDA machine

**Branch:** `task/20-gpu-validation` (from `main`; verify `git branch --show-current`
before every commit). **Prerequisite:** a machine with ≥1 CUDA device. If
`python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount())"` does not print
≥1 after the install step below, STOP and report — do not fake or skip this task.

## Why

Every gpu-marked test since S07 (satad, graupel, dycore, diffusion, JW plan
equivalence — the `gtfn_gpu` backend legs) has only ever been *skip-validated*:
written, collected, and confirmed to skip cleanly without a device, but never
executed. S14's acceptance "bitwise per backend" is evidence-backed for `gtfn_cpu`
only. This is flagged in the sign-off ledger (`development/work/reports/report-0036-implementation-report.md` §5) and
in the S07/S08/S12/S14 STATUS files.

## Hard rules (restated; full list in development/work/plans/README.md)

- **You may not change any test tolerance, assertion, or marker.** If a gpu test
  FAILS, that is a finding to report with full output — not something to fix by
  editing the test. Product-code fixes for genuine device bugs are IN scope but each
  needs its own justification in your report and must not change CPU-path behavior
  (prove with the CPU gate).
- No data in git; no pin changes. Installing the gpu extras is environment work, not
  a pin change: use the existing extras/constraints, do not edit them.
- Do not regenerate any cache under `~/.cache/icon-sc/`.

## Procedure

1. Read `development/work/plans/README.md` in full. Read the gpu-relevant STATUS notes:
   `development/work/reports/report-0007-satad-component.md` (Review fixes section),
   `development/work/reports/report-0008-graupel-component.md`,
   `development/work/reports/report-0012-nonhydro-hosting.md`,
   `development/work/reports/report-0014-plan-through-dycore.md` (Review fixes: the gpu PR note).
2. Install the GPU stack into the workspace env WITHOUT touching any pinned file:
   `uv pip install --prerelease=allow -c constraints/gpu-cuda12.txt "cupy-cuda12x==13.6.0" "gt4py[cuda12]==1.1.10"`
   Then verify: `uv run python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount())"` → ≥1.
3. Enumerate the gpu legs: `uv run pytest packages -m gpu --collect-only -q` and
   record the full list in your report (baseline expectation: legs exist in
   `test_satad_component.py`, `test_satad_datatest.py`, `test_graupel_component.py`,
   `test_graupel_datatest.py`, `test_contracts_checkers.py`,
   `test_nonhydro_datatest.py`, `test_diffusion_datatest.py`,
   `test_jw_plan_equivalence.py`, `test_backend_fixture.py`, `test_markers.py`, plus
   any others collection reveals — the collected list is authoritative).
4. Run them in file-sized chunks (each command <10 min where possible; the first
   gtfn_gpu compile per program variant can take minutes — that is expected):
   `uv run pytest <file> -m gpu -q` for each file from step 3, data files last
   (they need the archives in `~/.cache/icon-sc/icon4py-testdata`).
5. For every failure: capture the FULL pytest failure block verbatim into
   `development/plans/artifacts/` is NOT allowed (gitignored artifacts live outside plan/)
   — instead paste it into your task report and, if a product-code fix is warranted,
   fix on this branch with a test-backed justification. If a failure looks like a
   tolerance issue (values close but not equal), you MUST NOT touch the tolerance:
   report the measured deviation, the field, the test, and stop on that item.
6. After any product-code change, re-run the FULL CPU gate (all 8 commands from
   README.md) to prove CPU behavior is unchanged, plus the touched gpu files.
7. Write `development/records/020_gpu_validation_record.md`:
   device + driver + cupy versions; the collected gpu-leg list; per-file results
   (passed/failed/skipped with timings); every failure verbatim + disposition;
   whether S14's "bitwise per backend" now holds for gtfn_gpu (the
   `test_jw_t0_t1_bitwise_24h[gtfn_gpu]` outcome is the headline — state it
   explicitly, including its runtime).
8. Commit (report + any product fixes; message trailer per README).

## Acceptance criteria

1. Every collected gpu-marked test was EXECUTED (not skipped) at least once, with
   per-file results recorded. Zero tests were edited.
2. Any failures are reported verbatim with root-cause analysis or an explicit
   "unresolved — needs trunk decision" disposition. No silent failures.
3. The full CPU gate is green on the branch (baseline counts or better).
4. The report file exists, is committed, and answers the headline question
   (gtfn_gpu bitwise 24h: pass/fail/blocked-and-why).

## Verification gates

All 8 README gate commands, PLUS `uv run pytest packages -m gpu -q` (chunked by file
is acceptable; total counts must be reported and must contain 0 skips attributable
to "no CUDA device").

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Re-run at least 3 gpu files yourself, including one datatest file and
  `test_jw_plan_equivalence.py -m gpu`; compare against the report's numbers.
- `git diff main..HEAD` must contain NO changes under `packages/*/tests/` except
  possibly NEW test files (which need their own justification), and no
  tolerance/marker/assertion edits anywhere. Verify with
  `git diff main..HEAD -- 'packages/*/tests/' | grep -E "^[-+].*(rtol|atol|allclose|pytest.mark|assert)"`
  and read every hit.
- If product code changed: verify the justification, and confirm the CPU fast gate
  matches baseline (736+ passed) by running it yourself.
- Confirm the report's device/version info matches
  `uv run python -c "import cupy; print(cupy.__version__, cupy.cuda.runtime.runtimeGetVersion())"`.
