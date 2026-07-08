# S01 — STATUS

**Branch:** `step/S01-repo-scaffold` · **Date:** 2026-07-08 · **State:** ready for PR

## What was built

- **uv workspace** at the root (`packages/*` members, virtual root, Python pinned 3.10 via
  `.python-version`, `requires-python >=3.10,<3.15` from gt4py 1.1.10's support window).
- **Three PEP 420 namespace distributions**: `symcon-core` (extras `gpu`/`jax`/`mpi`/`native`),
  `symcon-icon` (deps: symcon-core, icon4py-common>=0.2.0), `symcon-bridges` (deps:
  symcon-core, cffi). All ship `py.typed`; namespace verified to span all three install roots.
- **Pin decision** (constraints/cpu-ci.txt, gpu-cuda12.txt, REFERENCES.lock): **icon4py 0.2.0**
  (tag v0.2.0 = `28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + **gt4py==1.1.10** — the latest
  tagged icon4py release, with every subpackage published on PyPI, whose metadata pins
  gt4py==1.1.10 exactly. icon4py HEAD at mining time pinned gt4py==1.1.11; we pin the released
  pair, not HEAD. Discovered distribution names recorded (symbolic `icon4py.common` →
  `icon4py-common`, `icon4py.dycore` → `icon4py-atmosphere-dycore`, …).
- **`symcon.core.testing`** (frozen interface): `assert_allclose(actual, desired, rtol, atol,
  names=...)` wrapping numpy.testing with worst-offender reporting (index, both values,
  abs/rel error, field names); `MARKERS` = gpu/mpi/slow/data; pytest plugin
  (`symcon.core.testing.plugin`) with marker registration, gpu-skip-without-device collection
  hook, and the `backend` fixture stub (`embedded`, `gtfn_cpu`, `gtfn_gpu`+gpu-mark).
- **`.importlinter`**: `core ↛ {icon, bridges}`, `icon ↛ bridges`. Negative test via
  import-linter's Python API (synthetic violating tree) + positive test on the real config.
  Tripwire commits `1b5247b` (deliberate core→icon import; `lint-imports` exits 1, contract
  BROKEN) and revert `ad76822` demonstrate acceptance 2 end-to-end.
- **CI**: `lint.yml` (ruff check/format, `mypy --strict -p symcon.core`, lint-imports),
  `test-cpu.yml` (locked-sync job, constraints-matrix job incl. the acceptance-5 icon4py
  import probe, core-standalone job), `test-gpu.yml`/`test-mpi.yml` skeletons whose marked
  tests skip cleanly without hardware. `.pre-commit-config.yaml` with ruff, ruff-format,
  mypy-on-core, lint-imports.
- **Top-level tree**: `examples/ validation/(data/) benchmarks/ tools/ docs/api envs/(spack/)`
  placeholder READMEs.

## Gate results (local)

- `uv sync` / `uv sync --locked`: OK (resolves gt4py 1.1.10 + icon4py 0.2.0).
- `uv run pytest packages`: 15 passed, 1 skipped (gtfn_gpu backend — no cupy/device).
- `ruff check` + `ruff format --check`: clean. `mypy --strict -p symcon.core`: clean.
- `lint-imports`: 2 contracts kept.
- Acceptance 3: fresh venv + `uv pip install -e packages/symcon-core` → `symcon.core` and
  `symcon.core.testing` import; `symcon.icon` correctly absent.
- Acceptance 5: `python -c "import icon4py.model.common"` OK under the pinned set.
- Acceptance 4 (workflows actually running) needs a push — not exercisable pre-PR; every
  command the workflows run was executed locally.

## Deviations

- **`prerelease = "allow"` in root `[tool.uv]`**: gt4py 1.1.10 has an unconditional
  `dace>=2.0.0a3` dependency with only pre-releases on PyPI; uv refuses transitive
  pre-releases by default. Scoped comment in pyproject.toml; constraints files still pin the
  exact working set.
- **mypy strictness is enforced by command (`mypy --strict -p symcon.core`)**, not per-module
  config — `strict` is not a per-module mypy option. Encoded identically in CI, pre-commit,
  and this gate.
- **`symcon-bridges` uses hatchling, not scikit-build-core+CMake** (layout doc §3): no Fortran
  source exists yet; switching the build backend lands with the first real bridge. Noted in
  the package's pyproject.
- **`envs/pixi.toml` not written** (listed in layout §0 tree): deferred until an HPC/system-dep
  target is exercised; `envs/README.md` says so. SPEC's in-scope list did not include it.
- **`constraints/alps-gh200.txt`, `jax-interop.txt`** deferred per SPEC (only cpu-ci and
  gpu-cuda12 in scope for S01).

## Follow-ups

- S02+: give `backend` fixture values meaning; wire gpu-marked tests to the real device CI.
- `tools/constraints_update.py` + scheduled CI job (layout §5 pin-refresh discipline) — not in
  S01 scope.
- When the first mpi-marked test lands, activate the commented `mpirun -n 4 … --with-mpi`
  block in `test-mpi.yml`.
- gt4py 1.1.10's `dace` pre-release dependency is worth revisiting at the next pin bump; if a
  stable dace 2.x appears, drop `prerelease = "allow"`.

## Artifacts

- Tripwire evidence: commits `1b5247b` → `ad76822` on this branch.
- REFERENCES.lock entries `icon4py` (v0.2.0) and `gt4py` (v1.1.10), step S01.
