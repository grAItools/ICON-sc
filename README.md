# symcon

A sympl-conformant Python architecture for the ICON model: sympl/Tasmania-lineage composition
(property-contracted components, a general dynamics–physics coupling algebra) over a zero-copy
device-field boundary, hosting icon4py granules, with bind-time interface specialization,
tiered execution (interpreted → plan → graph replay → native driver), and a functional JAX
lowering that makes the composed model differentiable (`jax.jvp`/`jax.vjp`).

**Status: pre-implementation.** This is the bootstrap commit: architecture documents, the
agent implementation plan, and agent tooling configuration. No framework code exists yet —
step S01 of the plan creates the package scaffolding, and its acceptance criteria define
what "scaffolded" means.

## Contents

| path | what |
|---|---|
| `docs/architecture/symcon_architecture.md` | the architecture, v1.3 — canonical; §-refs everywhere point here |
| `docs/architecture/symcon_repo_layout.md` | target repository layout the steps build toward |
| `plan/00_OVERVIEW.md` | implementation plan: agent contract, dependency DAG, lanes |
| `plan/steps/SXX_*/` | one folder per step: `SPEC.md` (frozen contract + acceptance) and `PLAN.md` (tasks + reference mining) |
| `plan/outlines/` | post-slice phases P2–P7, coarse |
| `AGENTS.md` | the agent working agreement (canonical; Claude Code imports it via `CLAUDE.md`) |
| `.claude/`, `opencode.json`, `.opencode/` | Claude Code and OpenCode configuration |
| `REFERENCES.lock` | provenance ledger for every external source consulted (schema inside) |
| `references/` | drop-zone for local reference documents (gitignored; see its README) |

## Bootstrap

```bash
git init -b main && git add -A && git commit -m "Bootstrap: architecture v1.3, implementation plan, agent tooling"
```

Then kick off the first step with your agent of choice:

```bash
claude              # then: /implement-step S01_repo_scaffold
opencode            # then: /implement-step S01_repo_scaffold
```

Steps run per the DAG in `plan/00_OVERVIEW.md`: trunk S01→S05 sequentially; lanes A (column)
and B (dycore) fork after S03 and may run as concurrent agents. Every step lands as one PR;
the definition of done lives in `AGENTS.md` and is restated by the PR template.

## License

BSD-3-Clause (matching ICON, icon4py, and GT4Py). See `LICENSE`.
