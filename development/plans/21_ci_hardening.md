# Task 21 — CI and repo hardening (five small, independent fixes)

**Branch:** `task/21-ci-hardening` (from `main`; verify `git branch --show-current`
before every commit). One commit per item below (5 commits + report).

## Hard rules (restated; full list in development/plans/README.md)

- No tolerance changes. No pin changes. No data in git. Do not edit
  `docs/architecture/*`, any SPEC/PLAN, or completed steps' STATUS files.
- Each item has an exact scope. Do not refactor beyond it. If an item turns out to
  require more than described, STOP on that item, mark it "blocked — needs trunk
  decision" in your report, and continue with the others.

## Item A — jax leg in the CI constraints matrix

**Problem** (S10 STATUS follow-up): the `constraints` matrix jobs in
`.github/workflows/test-cpu.yml` install no jax, so every F-tier test silently
skips there; only the `locked` job (uv.lock, jax 0.6.2) exercises S10. Also, dev
environments on Python ≥3.11 resolve a newer, unverified jax.

**Change**: in `.github/workflows/test-cpu.yml`, `constraints` job, extend the
`uv pip install` line to include `jax` so the pinned `jax==0.6.2` from
`constraints/cpu-ci.txt` (line 14) is installed — i.e. append `jax` to the package
list that already ends with `pytest pytest-mpi`. Do NOT touch the constraints file
itself. Add one YAML comment line above, citing "S10 follow-up: F-tier must not
silently skip in the matrix".

**Verify locally** (CI can't run here): simulate the matrix install in a throwaway
venv under /tmp:
```
uv venv /tmp/task21-venv --python 3.10
VIRTUAL_ENV=/tmp/task21-venv uv pip install --prerelease=allow \
  -e packages/symcon-core -e packages/symcon-icon -e packages/symcon-bridges \
  -c constraints/cpu-ci.txt pytest pytest-mpi jax
/tmp/task21-venv/bin/python -c "import jax; print(jax.__version__)"   # must print 0.6.2
/tmp/task21-venv/bin/pytest packages/symcon-core/tests/test_functional_compile.py -q  # must run, not skip
```

## Item B — fast-gate margin: move the three embedded graupel L2 cases to `slow`

**Problem** (S14 STATUS §5): the fast gate (`-m "not gpu and not slow"`) budget is
≤15 min (SPEC S14 acceptance 5) and currently lands ~14 min warm; ~10 of those
minutes are the three `embedded`-backend cases of
`packages/symcon-icon/tests/test_graupel_datatest.py::test_graupel_l2_parity_against_icon4py_savepoints`
(~190–210 s each).

**Change**: mark ONLY the `embedded` parametrization legs of that one test with
`pytest.mark.slow` (use `pytest.param("embedded", marks=pytest.mark.slow)` in the
backend parametrization of that test — check the file's actual parametrize
structure first and keep gtfn_cpu/gtfn_gpu legs untouched). Do not change
tolerances, test bodies, or any other test. Add a comment citing "S14 STATUS §5
fast-gate margin; embedded graupel is covered in the slow tier".

**Verify**:
```
uv run pytest packages/symcon-icon/tests/test_graupel_datatest.py --collect-only -q -m "not gpu and not slow"   # embedded legs GONE
uv run pytest packages/symcon-icon/tests/test_graupel_datatest.py --collect-only -q -m "slow and not gpu"       # embedded legs PRESENT
uv run pytest packages/symcon-icon/tests/test_graupel_datatest.py -q -m "slow and not gpu"                      # they still PASS (~10 min)
```
Then the full fast gate: expect **733 passed** (736 − 3 moved), 1 skipped, and a
runtime several minutes below the old ~14 min. The `data and slow` partition grows
by exactly 3. Record both new counts in your report — they become the new baseline
and you must say so explicitly.

## Item C — `make_reference.py --run all` must include the symcon leg

**Problem** (S13 STATUS follow-up): `validation/L4_idealized/make_reference.py`
`--run all` generates reference + twin + manifest but NOT the symcon leg (which
needs a separate `--run symcon`). This cost the orchestrator a full cycle during
S13.

**Change**: in `main()` of that file, make `run == "all"` also call
`generate_symcon(days)` AFTER the reference/twin loop and BEFORE the manifest
block. Update the module docstring's usage lines accordingly. DO NOT run a 9-day
generation to test this (it costs ~7 h and must not touch
`~/.cache/symcon/l4_reference`).

**Verify** without touching the real cache:
```
SYMCON_L4_CACHE=/tmp/task21-l4 uv run python validation/L4_idealized/make_reference.py --days 0.25 --force --run all
ls /tmp/task21-l4/   # must contain jw_l4_reference.npz, jw_l4_twin.npz, jw_l4_symcon.npz, manifest.json
uv run pytest validation/L4_idealized/test_jw.py -q   # against the REAL (untouched) cache: 3 passed
```
(The script reads `SYMCON_L4_CACHE` for its cache dir — confirm that env hook at
the top of the file; if it does not exist, adding it as an env-var override with
the current default is in scope for this item.)

## Item D — replace the `VerticalGrid._i4_grid` friend access in satad

**Problem** (S07 deviation, S11 provided the fix): `packages/symcon-icon/src/symcon/icon/components/fast/satad.py`
still reads the private `VerticalGrid._i4_grid`; S11 added the public
`VerticalGrid.icon4py_grid` property for exactly this.

**Change**: replace the `_i4_grid` access(es) in satad.py (find them with
`grep -n "_i4_grid" packages/symcon-icon/src/`) with `.icon4py_grid`. No other
change. If grep shows OTHER files using `_i4_grid`, list them in the report but
touch only satad.py.

**Verify**: `uv run pytest packages/symcon-icon/tests/test_satad_component.py -q`
(all pass) and `grep -rn "_i4_grid" packages/symcon-icon/src/symcon/icon/components/`
returns nothing.

## Item E — extend the names-registry re-assert check to `cf_name`

**Problem** (S06 review MINOR-1, declared follow-up): the consistency check in
`packages/symcon-icon/src/symcon/icon/names.py` that re-asserts S02-seeded rows
compares only `units` and `icon_name`; a drift in a core row's `cf_name` passes
silently.

**Change**: extend that check to also compare `cf_name` (locate the compare in
names.py — S06 STATUS "Review fixes" describes it; keep the error type
`NamesRegistryError` and its message style). Add one unit test in
`packages/symcon-icon/tests/test_names.py`: pre-register a core-seeded name with a
conflicting `cf_name`, import/trigger the re-assert, expect `NamesRegistryError`
(mirror the existing conflicting-units test in that file, including its
registry save/restore fixture).

**Verify**: `uv run pytest packages/symcon-icon/tests/test_names.py -q` (all pass,
one more test than before).

## Acceptance criteria

1. Items A–E each done exactly as scoped (or explicitly reported blocked), one
   commit each, verified by the per-item commands above.
2. Full gate green with the NEW baselines from item B (733 fast / +3 in data+slow)
   — record the exact numbers.
3. Report `development/records/21_ci_hardening_REPORT.md` committed: per-item
   what/verify-output/new-baselines, plus anything found out of scope.

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Re-run every per-item verification command yourself. For item B, additionally
  run the full fast gate and confirm 733 passed AND that the three moved legs pass
  under `-m "slow"` — a marker move that orphans tests (running in NO partition) is
  a MAJOR finding: check total collected counts across all four partitions sum to
  the old total + any new tests.
- For item C, confirm the REAL l4_reference cache is bit-identical to before:
  `sha256sum ~/.cache/symcon/l4_reference/*` must match the manifest's recorded
  hashes (read `manifest.json` and compare).
- Diff discipline: `git diff main..HEAD --stat` must touch only: test-cpu.yml,
  test_graupel_datatest.py, make_reference.py, satad.py, names.py,
  test_names.py, and the report. Anything else is a finding.
- Confirm no tolerance strings changed:
  `git diff main..HEAD | grep -E "^[-+].*(rtol|atol)" ` must be empty.
