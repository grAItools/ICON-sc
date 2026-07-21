# Work unit 0052 — Disjoint verification gates (renamed from "parallel")

**Branch:** `work/0052-disjoint-verification-gates` (from `main`; verify
`git branch --show-current` before every commit). One PR. **Deliverable:** the partition fix
+ driver + dependency + docs, and
`development/work/reports/report-0052-disjoint-verification-gates.md`.

Authority: `docs/architecture/icon-sc_architecture.md` > `spec-0052-disjoint-verification-gates.md`
> this plan. **The spec's per-partition table is the single source of truth for every
`--dist`/`-n` value** — this plan deliberately restates none of them; read them there and
encode exactly those. The spec's *Frozen interfaces* bind. Parallelism changes **scheduling
only**; the partition-boundary change (Item A) changes *which partition* runs a test, never
*whether* it runs.

## Hard rules (restated; full list in `development/work/plans/README.md`)

- `git branch --show-current` = `work/0052-disjoint-verification-gates` before every commit;
  never commit to main; never push; `Co-Authored-By:` trailer.
- **No tolerance changes, no reduction-order changes, no `pytest.mark` edits on any test.**
  The driver never injects `-x`, `-k`, or `--ignore`; `-n`/`--dist` are the *only* flags it
  adds to a marker command (do **not** add `-p xdist` — xdist registers via entry point).
- **No dependency pin changes.** `constraints/*.txt` and `uv.lock` version bumps are trunk
  decisions. Item A adds one *lower-bound dev declaration*, which `plans/README.md` permits
  only because this plan says so. If `uv lock` moves any pin other than xdist/execnet:
  **STOP**, mark blocked, do not "fix and continue".
- No data in git. Caches (`~/.cache/icon-sc/gt4py`, `~/.cache/icon-sc/icon4py-testdata`,
  `~/.cache/icon-sc/l4_reference`) are read-only context — never regenerated, never pointed
  cold (verification-gates.md "Caches").
- No `icon_sc.*` source change; import-linter contracts stay `2 kept, 0 broken`.
- Do not edit `docs/architecture/*` or any other work unit's spec. If an item needs more than
  its scope: STOP, mark it "blocked — needs trunk decision" in the report, continue the rest.

## Item A — disjoint partitions + `pytest-xdist`

**Problem:** the `fast` marker expression `not gpu and not slow` does not exclude `data`, so
the 43 `data and not slow` tests run inside `fast` *and* again in their own partition. That
duplicated work costs ~7 min, and — because those 43 are the reference loaders — it makes
`fast` a memory-heavy partition, falsifying any "complementary profiles" wave scheduling.

**Change:** (1) adopt the spec's `fast` expression `not gpu and not slow and not data`
everywhere the battery is invoked. (2) Add `pytest-xdist>=3.6` to `[dependency-groups].dev`
in `pyproject.toml` (existing `>=` style; `execnet` arrives transitively) and run `uv lock`.
Record the resolved `pytest-xdist`/`execnet` versions in the report. Do **not** touch
`constraints/cpu-ci.txt`: it pins no pytest plugin at all (`pytest`, `pytest-cov`,
`pytest-mpi`, `ruff`, `mypy`, `hypothesis` are all absent from it), so xdist does not belong
there — now or in the CI follow-up.

**Verify** — coverage invariance is the acceptance-critical proof:
```
cd $(git rev-parse --show-toplevel)
collect() { uv run pytest packages -m "$1" --collect-only -q | grep :: | sort; }
collect "not gpu and not slow"                 > /tmp/0052_fast_old.txt   # 740
collect "not gpu and not slow and not data"    > /tmp/0052_fast_new.txt   # 697
collect "data and not slow and not gpu"        > /tmp/0052_dn.txt         # 43
collect "slow and not gpu and not data"        > /tmp/0052_sn.txt         # 31
collect "data and slow and not gpu"            > /tmp/0052_ds.txt         # 77
cat /tmp/0052_fast_old.txt /tmp/0052_dn.txt /tmp/0052_sn.txt /tmp/0052_ds.txt | sort -u | wc -l  # 848
cat /tmp/0052_fast_new.txt /tmp/0052_dn.txt /tmp/0052_sn.txt /tmp/0052_ds.txt | sort -u | wc -l  # 848
comm -12 /tmp/0052_fast_new.txt /tmp/0052_dn.txt | wc -l   # 0  (disjoint)
comm -13 /tmp/0052_fast_new.txt /tmp/0052_fast_old.txt | wc -l   # 43 (delta is exactly the data set)
uv lock && uv sync --locked && uv run python -c "import xdist, execnet; print(xdist.__version__)"
```
Both unions **must** print 848; a mismatch means coverage moved and the item is blocked.
`git diff main -- pyproject.toml uv.lock` must touch only xdist/execnet lines (else STOP).

## Item B — the gt4py concurrent-compile question (decide before building anything)

**Problem:** xdist workers first-compiling the same gtfn variant into the shared persistent
cache (`~/.cache/icon-sc/gt4py`) may race or redundantly compile. This is an *assumption*, not
an observation — and the gate baseline is warm caches, so a warm-up may buy nothing.

**Change:** answer it with evidence, then act. Read gt4py 1.1.10's build-cache implementation
(the `GT4PY_BUILD_CACHE_DIR`/`GT4PY_BUILD_CACHE_LIFETIME` path, set in
`packages/icon-sc-core/src/icon_sc/core/testing/plugin.py`) and establish whether concurrent
writers are locked/atomic. Then:
- **If safe:** record the finding with file/function evidence; add no warm-up. Done.
- **If unsafe:** implement the narrowest mitigation — a serial pre-pass that *executes* a
  named minimal set of tests covering each gtfn variant the gate uses. Note `--collect-only`
  runs no test body and therefore compiles nothing; it is not a warm-up. Measure the effect.

**Verify:** the report states the answer, cites the gt4py code consulted, and — if a
mitigation was built — shows a before/after compile count or wall-time. "No warm-up needed"
is an acceptable outcome **only** with the evidence attached.

## Item C — `tools/run_gate.py` orchestrator

**Change:** add `tools/run_gate.py`. It shells out to the marker commands from
`policies/verification-gates.md`, adding only `-n`/`--dist` per the **spec's table**, and
provides:
- `--serial` — the marker commands verbatim, no `-n`/`--dist`: the baseline oracle.
- `--partition <fast|slow-nodata|data-noslow|data-slow>` — one partition at its table `-n`.
- default — the full parallel gate: lint battery (`ruff check` / `ruff format --check` /
  `mypy --strict -p icon_sc.core` / `lint-imports`) first as cheap fail-fast, then Wave 1
  (`fast` ‖ `data-slow`), then Wave 2 (`slow-nodata` ‖ `data-noslow`).

Requirements:
- **Verbatim capture:** each partition's full stdout/stderr streams to a per-partition log; on
  failure the driver prints the failing partition's output **verbatim**, never a summary.
- **Exit aggregation:** non-zero iff any partition/lint/check is non-zero; a wave never
  swallows a worker crash.
- **One RAM-heavy partition per wave** — true by construction only *because* Item A made the
  partitions disjoint; assert the wave composition in code so it cannot silently regress.
- **No selection changes:** assert in code that the only flags added are `-n`/`--dist`.
- Worker counts and dist modes are module-level constants, each citing the spec table, so
  Item D's calibration edits exactly one place.

**Verify:**
```
uv run python tools/run_gate.py --serial            # full serial gate green = the oracle
uv run python tools/run_gate.py --partition fast    # green
uv run python tools/run_gate.py                     # full parallel gate green; prints wall-time
```

## Item D — calibrate the caps against the waves, not the partitions

**Problem:** a cap that is safe for `data-slow` alone can still OOM once Wave 1 adds `fast`'s
10 workers on top. Only the wave peak bounds the gate.

**Change:** sample peak RSS (`/usr/bin/time -v`, or a `psutil` sampler wrapping the driver)
**of each wave as the driver runs it**, sweeping the `data-slow` cap over `-n 1..4` and the
`data-noslow` cap over `-n 1..4`. Measure `fast`'s own peak RSS too — it is the term the
original analysis wrongly assumed away. Set each data cap to the largest `-n` whose **wave**
peak stays under 75 % of 31 GB (≈ 23 GB). Encode the chosen caps in Item C's constants.
Record — in the report **and** in `policies/verification-gates.md` — the chosen caps, the
measured per-wave peak RSS at those caps, and `fast`'s measured peak.

**Verify:** re-run the full gate at the chosen caps; per-wave peak RSS < 23 GB; counts
unchanged vs `--serial`.

## Item E — independence gate (serial ≡ parallel proof)

**Change:** for each partition, capture `passed`/`skipped`/`deselected` serially and in
parallel, running the parallel case **twice**. Assert identical counts across all three. Any
divergence → **stop**, root-cause the shared-state/order dependency, and fix the offending
*test* (never reorder-to-hide, never marker-edit). Fixing a test file puts
`packages/**/tests/*.py` into the diff, which acceptance criterion 7's file set does not
otherwise allow: that is permitted **only** with the divergence, its root cause, and the fix
written up in the report. Permitted skips remain the 1 mpi opt-in, gpu-no-device, and the 1 upstream MCH
diffusion skip; a new skip is a finding to explain.

**Verify:** a serial-vs-parallel×2 table per partition in the report, all rows identical; the
four partitions' collected counts sum to 848 with no overlap.

## Item F — docs, baseline, and the dependency decision

**Change:**
1. `policies/verification-gates.md`: the `fast` command becomes
   `uv run pytest packages -m "not gpu and not slow and not data" -q`; present
   `tools/run_gate.py` as the canonical way to run the gate and **keep the serial marker
   commands as the fallback/baseline oracle**. Add a "Parallelism" subsection: the spec's
   `--dist`/`-n` table, the calibrated caps + measured per-wave RSS ceiling (Item D), the
   one-RAM-heavy-partition-per-wave rule, and the gt4py finding (Item B). Update the baseline
   table with the new counts and measured parallel wall-times beside the serial ones. State
   explicitly that `fast` 739 → ~696 passed is the 43 `data, not slow` tests moving to their
   own partition, with the union (848, unchanged) as evidence — not a removal.
2. Same file, "Caches": correct `EXCLAIM APE ~4 GB` → `~4.0 GB compressed / 8.7 GB extracted`
   (the 8.7 GB figure is load-bearing for Item D).
3. `REGISTRY.md`: row 0052 kinds → `proposal + spec + plan + report`; add a §3 decision row
   `TD-52.1` (pytest-xdist added to the dev group; status pending → (merge)), mirrored by a
   `TD-PENDING:` line in the report.

**Verify:** `uv run sphinx-build -b html docs docs/_build/html` exits 0; the numbers in
verification-gates.md match the report's dated gate lines exactly.

## Acceptance criteria

1. Items A–F each done as scoped (or explicitly reported blocked), verified by the per-item
   commands.
2. **Coverage invariance proven**: union = 848 before and after, `fast ∩ data-noslow = ∅`,
   delta = exactly the 43 `data, not slow` tests. This is the criterion that separates a
   partition-boundary change from a coverage regression.
3. `tools/run_gate.py` (default) leaves the gate green with **identical `passed`/`skipped`
   counts** to `--serial`; the independence gate (Item E) shows serial ≡ parallel ≡ parallel.
4. Per-wave peak RSS < 23 GB measured **on the waves as run** (no OOM); caps + measured peaks
   recorded in `policies/verification-gates.md`.
5. The gt4py concurrent-compile question is answered with cited evidence (Item B).
6. Measured parallel wall-time recorded against the measured serial baseline (target
   ≈ 18–22 min), with no change to test outcomes.
7. `git diff main..HEAD --stat` touches only: `pyproject.toml`, `uv.lock`,
   `tools/run_gate.py`, `development/policies/verification-gates.md`,
   `development/REGISTRY.md`, the report — plus `packages/**/tests/*.py` **only** under Item
   E's written-up exception. Anything else is a finding.
8. Report `development/work/reports/report-0052-disjoint-verification-gates.md` committed per
   the `document-kinds.md` template.

## Verification gates (run before the report; the driver runs them for you)

`uv run python tools/run_gate.py` green end-to-end, **and** `--serial` green as the oracle.
Counts: `fast` ~696 passed/1 skip (new expression) · `slow-nodata` 31 · `data-noslow` 43 ·
`data-slow` 76/1 skip · ruff clean/format · mypy `Success: no issues found in 50 source files`
· lint-imports `Contracts: 2 kept, 0 broken`. Report every dated gate line verbatim.

## Review checklist (fresh reviewer; protocol `policies/review-protocol.md`)

- **Re-derive coverage invariance yourself** — run Item A's collection commands; both unions
  must be 848 and the intersection empty. This is the finding that matters most: if the union
  moved, tests were silently dropped.
- **Re-run** `tools/run_gate.py --serial` and default; confirm identical counts and green.
  Independently reproduce Item E's table for at least `data-slow` and `fast`.
- **No hidden selection change:** `git diff main..HEAD` — confirm the driver adds only
  `-n`/`--dist` (and no `-p xdist`); grep the diff for `-x `, `-k `, `--ignore`, `pytest.mark`
  edits, and tolerance strings (`rtol|atol`) — all absent from test files except under Item
  E's exception.
- **Caps vs evidence:** the constants in `tools/run_gate.py` match the per-wave RSS evidence
  in the report and in `policies/verification-gates.md`; confirm the measurement was of a
  *wave*, not a partition alone, and that `fast`'s RSS was measured.
- **gt4py answer** (Item B) cites real gt4py code, not an assumption; any warm-up actually
  executes test bodies (`--collect-only` compiles nothing).
- **Dependency hygiene:** `git diff main -- pyproject.toml uv.lock` = only xdist/execnet;
  `constraints/cpu-ci.txt` untouched; `TD-52.1` in `REGISTRY.md` §3 mirrored by a
  `TD-PENDING:` line in the report.
- **Diff discipline:** the acceptance-7 file set only; `docs/architecture/`, other specs, and
  `lock.toml` untouched
  (`git diff main -- docs/architecture development/references/lock.toml` empty).
- Verdict per protocol.
