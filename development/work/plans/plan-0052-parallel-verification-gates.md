# Work unit 0052 — Parallel verification gates (bounded two-layer test parallelism)

**Branch:** `work/0052-parallel-verification-gates` (from `main`; verify
`git branch --show-current` before every commit). One PR. **Deliverable:** the driver +
dependency + docs, and `development/work/reports/report-0052-parallel-verification-gates.md`.

Authority: `docs/architecture/symcon_architecture.md` > `spec-0052-parallel-verification-gates.md`
> this plan. The spec's *Frozen interfaces* bind. Parallelism changes **scheduling only** —
never what any test runs, asserts, or tolerates.

## Hard rules (restated; full list in `development/work/plans/README.md`)

- `git branch --show-current` = `work/0052-parallel-verification-gates` before every commit;
  never commit to main; never push; `Co-Authored-By:` trailer.
- **No tolerance changes, no reduction-order changes, no marker edits.** The driver must
  never inject `-x`, `-k`, `--ignore`, or edit markers; `-n`/`--dist` are the *only* added
  flags, and they change scheduling, not selection.
- **No pin bumps** to gt4py/icon4py. Adding `pytest-xdist` to the `dev` group is the one new
  dev dependency — trunk-visible (Item E raises it as a `TD-PENDING` + `REGISTRY.md §3` row).
- No data in git. Caches (`~/.cache/symcon/gt4py`, `~/.cache/symcon/icon4py-testdata`,
  `~/.cache/symcon/l4_reference`) are read-only context — never regenerated, never pointed
  cold (verification-gates.md "Caches").
- No `symcon.*` source change; import-linter contracts stay `2 kept, 0 broken`.
- Do not edit `docs/architecture/*` or any spec. If an item needs more than its scope: STOP,
  mark it "blocked — needs trunk decision" in the report, continue with the others.

## Item A — add `pytest-xdist` to the dev group

**Change:** add `pytest-xdist>=3.6` to `[dependency-groups].dev` in `pyproject.toml` (the
existing `>=` lower-bound style; `execnet` arrives transitively). Regenerate the lockfile
with `uv lock`. Record the exact resolved `pytest-xdist` and `execnet` versions in the report.
Do **not** touch `constraints/cpu-ci.txt` — the constraints/CI pin travels with the follow-up
CI work unit; adding an unused pin here would be dead weight the reviewer must justify.

**Verify:**
```
uv lock                      # lockfile updates; git diff shows only xdist/execnet additions
uv sync --locked             # resolves clean
uv run python -c "import xdist, execnet; print(xdist.__version__)"
uv run pytest packages -m "not gpu and not slow" -p xdist -n 2 --collect-only -q | tail -1
```
`git diff main -- pyproject.toml uv.lock` must touch only the xdist/execnet lines.

## Item B — `tools/run_gate.py` orchestrator

**Change:** add `tools/run_gate.py`. It shells out to the **exact** marker commands from
`policies/verification-gates.md`, adding only `-n`/`--dist` per the spec table, and provides:

- `--serial` — runs the eight gate commands verbatim (no `-n`/`--dist`): the baseline oracle.
- `--partition <fast|slow-nodata|data-noslow|data-slow>` — one partition, parallel.
- default — the full parallel gate: (1) lint battery (`ruff check` / `ruff format --check` /
  `mypy --strict -p symcon.core` / `lint-imports`) first as cheap fail-fast; (2) gt4py
  **warm-up** (a compile-only pass — collect-only across the backends, or a minimal trigger of
  each gtfn variant — populating `~/.cache/symcon/gt4py` before any parallel worker compiles,
  killing the compile race); (3) **Wave 1**: `fast` (`loadscope -n 10`) concurrently with
  `data-slow` (`load -n <cap>`); (4) **Wave 2**: `slow-nodata` (`load -n 6`) concurrently with
  `data-noslow` (`loadscope -n <cap>`).

Requirements:
- **Verbatim capture:** each partition's full stdout/stderr is streamed to a per-partition log
  and echoed; on any failure the driver prints the failing partition's output **verbatim**
  (the report-failures-verbatim rule) — never a summary.
- **Exit aggregation:** the driver exits non-zero iff *any* partition/lint/check is non-zero.
  A wave does not swallow a worker crash.
- **OOM guard:** the two memory-heavy data partitions never share a wave (they are in
  different waves by construction); the `-n` caps come from Item C.
- **No selection changes:** assert (in the code) that the only flags added to each marker
  command are `-n`/`--dist -p xdist`; nothing edits markers or adds `-x/-k/--ignore`.
- Worker counts are module-level constants with a comment tying each to the spec table, so the
  Item C calibration edits one place.

**Verify:**
```
uv run python tools/run_gate.py --serial      # full serial gate green = the oracle
uv run python tools/run_gate.py --partition fast     # parallel fast partition green
uv run python tools/run_gate.py               # full parallel gate green; prints wall-time
```

## Item C — RSS calibration of the two data-partition caps

**Change:** measure peak RSS of the `data-slow` and `data-noslow` partitions under xdist at
`-n 1,2,3,4` (`/usr/bin/time -v` peak RSS, or a `psutil` sampler wrapping the run). Set each
cap to the largest `-n` whose peak RSS stays under **75 % of 31 GB (≈ 23 GB)**. Encode the
chosen caps in the Item B constants. Record, in the report **and** in
`policies/verification-gates.md`, the chosen `-n` and the measured peak RSS at that `-n`.

**Verify:** re-run `data-slow`/`data-noslow` at the chosen caps; peak RSS < 23 GB; counts
unchanged vs serial.

## Item D — independence gate (serial ≡ parallel proof)

**Change:** for each of the four partitions, capture `passed`/`skipped`/`deselected` counts
serially and in parallel, and run the parallel case **twice**. Assert identical counts across
all three runs. Any divergence → **stop**, root-cause the shared-state/order dependency, fix
the offending *test* (never reorder-to-hide, never marker-edit), and document it. The only
permitted skips remain the 1 mpi opt-in, gpu-no-device, and the 1 upstream MCH diffusion skip;
a new skip is a finding to explain, not to accept.

**Verify:** a short comparison table (serial vs parallel×2) per partition in the report, all
rows identical; total collected across the four partitions equals the serial total.

## Item E — docs, baseline, and the dependency decision

**Change:**
1. `policies/verification-gates.md`: present `tools/run_gate.py` as the canonical way to run
   the gate; **keep the eight serial marker commands documented as the fallback / baseline
   oracle** (they define *what* runs and are what Item D validates against). Add a "Parallelism"
   subsection: the per-partition `--dist`/`-n` table, the calibrated data caps + measured RSS
   ceiling (Item C), the warm-up note, and the OOM guard. Update the baseline table with the
   measured **parallel** wall-times (keep the serial figures beside them). Counts are unchanged
   — say so explicitly.
2. `REGISTRY.md`: set row 0052 kinds to `proposal + spec + plan + report`; add a `§3` decision
   row for the new dev dependency (`TD-52.1` — pytest-xdist added to the dev group; status
   pending → (merge)); the report carries the matching `TD-PENDING:` line.

**Verify:** `uv run sphinx-build -b html docs docs/_build/html` still exits 0 (docs unaffected);
the baseline numbers in verification-gates.md match the report's dated gate lines.

## Acceptance criteria

1. Items A–E each done as scoped (or explicitly reported blocked), verified by the per-item
   commands.
2. `tools/run_gate.py` (default) leaves all eight gate commands green with **identical
   `passed`/`skipped`/`deselected` counts** to `--serial`; the independence gate (Item D)
   shows serial ≡ parallel ≡ parallel with no order-flakiness.
3. Peak RSS < 23 GB throughout (no OOM); calibrated caps + measured ceiling recorded in
   `policies/verification-gates.md`.
4. Measured parallel wall-time recorded (target ≈ 18–22 min) with no change to test outcomes.
5. `git diff main..HEAD --stat` touches only: `pyproject.toml`, `uv.lock`, `tools/run_gate.py`,
   `policies/verification-gates.md`, `REGISTRY.md`, and the report. Anything else is a finding.
6. Report `development/work/reports/report-0052-parallel-verification-gates.md` committed per
   the `document-kinds.md` template (flat file; no artifacts folder needed unless calibration
   logs are kept).

## Verification gates (run before the report; the driver runs them for you)

`uv run python tools/run_gate.py` green end-to-end, **and** `--serial` green as the oracle.
Equivalently the eight `policies/verification-gates.md` commands green. Counts unchanged from
the current baseline (fast 739/1 skip · slow 31 · data 43 · data-slow 76/1 skip · ruff
clean/format count · mypy 50 · lint-imports `2 kept, 0 broken`) except where a partition adds
tests (none here). Report every dated gate line verbatim.

## Review checklist (fresh reviewer; protocol `policies/review-protocol.md`)

- **Re-run** `tools/run_gate.py --serial` and default; confirm identical counts and green.
  Independently reproduce Item D's serial≡parallel table for at least the `data-slow` and
  `fast` partitions.
- **No hidden selection change:** `git diff main..HEAD` — confirm the driver adds only
  `-n`/`--dist -p xdist`; grep the diff for `-x `, `-k `, `--ignore`, marker edits, and
  tolerance strings (`grep -E "^[-+].*(rtol|atol|-x |--ignore| -k )"` must be empty of
  behavioral changes).
- **OOM/caps:** verify the calibrated caps in `tools/run_gate.py` match the RSS evidence in
  the report and in `policies/verification-gates.md`; confirm the two data partitions are in
  different waves.
- **Dependency hygiene:** `git diff main -- pyproject.toml uv.lock` = only xdist/execnet;
  `constraints/cpu-ci.txt` untouched; `TD-52.1` row present in `REGISTRY.md §3` and mirrored by
  a `TD-PENDING:` line in the report.
- **Diff discipline:** the §Acceptance-criteria-5 file set only; `docs/architecture/`, specs,
  and `lock.toml` untouched (`git diff main -- docs/architecture development/work/specs development/references/lock.toml` empty).
- Verdict per protocol.
