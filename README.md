# symcon

A sympl-conformant Python architecture for the ICON model: sympl/Tasmania-lineage composition
(property-contracted components, a general dynamics–physics coupling algebra) over a zero-copy
device-field boundary, hosting icon4py granules, with bind-time interface specialization,
tiered execution (interpreted → plan → graph replay → native driver), and a functional JAX
lowering that makes the composed model differentiable (`jax.jvp`/`jax.vjp`).

**Status: vertical slice implemented (S01–S14, merged).** The SCM physics column
(satad + graupel, SUS coupling, F-tier gradients) and the idealized dycore
(NonhydroSolver + diffusion + Jablonowski–Williamson, T1 plan) are built, validated
(L2 parity at upstream tolerances; 9-day L4 bitwise-zero vs the icon4py driver;
T0 ≡ T1 bitwise through the dycore), and merged — see `plan/IMPLEMENTATION_REPORT.md`.
Post-slice work proceeds as numbered tasks registered in `plan/prompts/README.md`;
a Sphinx documentation site builds from `docs/` (task 28).

## Contents

| path | what |
|---|---|
| `docs/architecture/symcon_architecture.md` | the architecture, v1.3 — canonical; §-refs everywhere point here |
| `docs/architecture/symcon_repo_layout.md` | target repository layout the steps build toward |
| `plan/00_OVERVIEW.md` | implementation plan: agent contract, dependency DAG, lanes |
| `plan/steps/SXX_*/` | one folder per step: `SPEC.md` (frozen contract + acceptance), `PLAN.md` (tasks + reference mining), `STATUS.md` (record of what landed) |
| `plan/outlines/` | post-slice phases P2–P7, coarse |
| `plan/IMPLEMENTATION_REPORT.md` | process record of the S01–S14 slice: merge ledger, findings, verification headlines |
| `plan/TRUNK_DECISIONS.md` | living register of trunk decisions and human sign-offs |
| `plan/prompts/` | post-slice task register, prompts, review protocol; deliverables under `reports/` |
| `plan/README.md` | plan-tree map: file taxonomy, naming rules, templates, plan/docs boundary |
| `docs/` | published documentation site (Sphinx + MyST, task 28): tutorials, API reference, glossary |
| `AGENTS.md` | the agent working agreement (canonical; Claude Code imports it via `CLAUDE.md`) |
| `.claude/`, `opencode.json`, `.opencode/` | Claude Code and OpenCode configuration |
| `REFERENCES.lock` | provenance ledger for every external source consulted (schema inside) |
| `references/` | drop-zone for local reference documents (gitignored; see its README) |

## Working on the repo

Implementation steps run per the DAG in `plan/00_OVERVIEW.md` (`/implement-step
SXX_<name>` with Claude Code or OpenCode); the S01–S14 slice is complete. Post-slice
work is assigned as numbered task prompts — see the register and the non-negotiable
invariants in `plan/prompts/README.md`. Every step/task lands as one PR; the definition
of done lives in `AGENTS.md` and is restated by the PR template.

```bash
uv sync                          # workspace env (three PEP 420 packages)
uv run pytest packages -m "not gpu and not slow" -q    # the fast gate
uv run sphinx-build -b html docs docs/_build/html      # the docs site
```

## License

BSD-3-Clause (matching ICON, icon4py, and GT4Py). See `LICENSE`.
