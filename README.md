# ICON-sc

A sympl-conformant Python architecture for the ICON model: sympl/Tasmania-lineage composition
(property-contracted components, a general dynamics–physics coupling algebra) over a zero-copy
device-field boundary, hosting icon4py granules, with bind-time interface specialization,
tiered execution (interpreted → plan → graph replay → native driver), and a functional JAX
lowering that makes the composed model differentiable (`jax.jvp`/`jax.vjp`).

**Status: vertical slice implemented (work units 001–014, merged).** The SCM physics column
(satad + graupel, SUS coupling, F-tier gradients) and the idealized dycore
(NonhydroSolver + diffusion + Jablonowski–Williamson, T1 plan) are built, validated
(L2 parity at upstream tolerances; 9-day L4 bitwise-zero vs the icon4py driver;
T0 ≡ T1 bitwise through the dycore), and merged — see
`development/work/0036-implementation-report/report.md`. Post-slice work proceeds as
numbered work units registered in `development/REGISTRY.md` §1;
a Sphinx documentation site builds from `docs/` (work unit 028).

## Contents

| path | what |
|---|---|
| `docs/architecture/icon-sc_architecture.md` | the architecture, v1.3 — canonical; §-refs everywhere point here |
| `development/` | repo-internal process memory (map in its README): policies, ADRs, the work lifecycle (proposals/specs/plans/reports), reference cards |
| `development/REGISTRY.md` | living registry: work ids, the old→new name remap tables, trunk decisions and human sign-offs |
| `development/policies/` | living rules: agent workflow, naming, document kinds, gates, reference mining, review protocol, docs boundary, repo layout |
| `development/ADRs/` | architecture decision records (`NNNN-<kebab-title>.md`, own sequence, cited `ADR-NNNN`) |
| `development/work/<NNNN>-<slug>/` | one folder per work unit: `proposal.md` / `spec.md` / `plan.md` / `report.md` (only those that exist) + optional `artifacts/`; e.g. `0000-overview/report.md` (agent contract, dependency DAG, lanes), `0036-implementation-report/report.md` (001–014 slice process report), the P2–P7 phase proposals (`0037-…`–`0042-…`) |
| `development/references/` | per-source reference cards; `lock.toml` — the provenance ledger for every external source consulted (schema inside); `local/` drop-zone for local reference documents (gitignored) |
| `docs/` | published documentation site (Sphinx + MyST, work unit 028): tutorials, API reference, glossary |
| `AGENTS.md` | the agent working agreement (canonical; Claude Code imports it via `CLAUDE.md`) |
| `.claude/`, `opencode.json`, `.opencode/` | Claude Code and OpenCode configuration |

## Working on the repo

The 001–014 slice ran per the DAG in `development/work/0000-overview/report.md`; it is
complete. Post-slice work is assigned as numbered work-unit plans (`/implement-plan
NNNN-<kebab>` with Claude Code or OpenCode) — see the register in
`development/REGISTRY.md` §1 and the non-negotiable invariants in
`development/work/README.md`. Every work unit lands as one PR; the definition of done
lives in `AGENTS.md` and is restated by the PR template.

```bash
uv sync                          # workspace env (three PEP 420 packages)
uv run pytest packages -m "not gpu and not slow" -q    # the fast gate
uv run sphinx-build -b html docs docs/_build/html      # the docs site
```

## License

BSD-3-Clause (matching ICON, icon4py, and GT4Py). See `LICENSE`.
