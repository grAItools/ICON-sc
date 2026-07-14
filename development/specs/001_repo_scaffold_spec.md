# S01 — Repository scaffold, CI, dependency pinning

**Lane:** trunk · **Depends on:** — · **Unblocks:** everything

## Goal
The monorepo of the layout document exists, empty but enforced: three installable namespace packages, one uv workspace, CI gates (lint, types, import contracts, tests), and the gt4py/icon4py version pin the whole slice will use.

## In scope
- uv workspace root; `packages/symcon-core|symcon-icon|symcon-bridges` with `src/symcon/{core,icon,bridges}/__init__.py`, `py.typed`, minimal `pyproject.toml` each (extras per layout doc: core `[gpu]`, `[jax]`, `[mpi]`, `[native]`).
- `.pre-commit-config.yaml` (ruff, ruff-format, mypy on core), `.importlinter` with contracts: `symcon.core` independent of `symcon.icon`/`symcon.bridges`; `symcon.icon` may not import `symcon.bridges`.
- `constraints/cpu-ci.txt` and `constraints/gpu-cuda12.txt`: pinned gt4py + icon4py commit pair, discovered from icon4py's own tested requirements (record rationale in `REFERENCES.lock`).
- GitHub Actions: `lint.yml`, `test-cpu.yml` (matrix over constraints), `test-gpu.yml` and `test-mpi.yml` as skeletons with the marker plumbing.
- `symcon.core.testing` module: `assert_allclose` wrapper (worst-offender reporting), marker registration, backend-parametrization fixture stub.
- Top-level dirs from the layout doc (`examples/ validation/ benchmarks/ tools/ docs/ envs/`) with placeholder READMEs; `REFERENCES.lock` initialized.

## Out of scope
Any framework code beyond `testing`.

## Frozen interfaces (later steps import these)
- Package import roots `symcon.core`, `symcon.icon`, `symcon.bridges`.
- `symcon.core.testing.assert_allclose(actual, desired, rtol, atol, names=...)`.
- Marker names: `gpu`, `mpi`, `slow`, `data`.

## Acceptance criteria
1. `uv sync` succeeds from clean checkout; `uv run pytest` green (placeholder tests).
2. `lint-imports` fails on a deliberate `symcon.core → symcon.icon` import (add + remove the tripwire in a test commit; keep the negative test as a unit test using import-linter's API).
3. `uv pip install -e packages/symcon-core` works standalone (core has no icon dependency).
4. CI runs all four workflows; gpu/mpi jobs skip cleanly on unavailable hardware.
5. `python -c "import icon4py.model.common"` (or discovered equivalent root) succeeds under the pinned constraints.
