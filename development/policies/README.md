# policies/ — living rules for development

Policies are living, trunk-gated; agents follow them and propose changes via `ideas/`
or a `development/REGISTRY.md` row — never by silently editing during a task.

| Policy | One line |
|---|---|
| `agent_workflow.md` | how a step/task runs: spec → plan → mine references → implement → gates → record → one PR; the implementer/reviewer loop |
| `naming_conventions.md` | S/P/N-series and ADR naming, the number-allocation rule, the `TD-PENDING:` marker |
| `records_and_liveness.md` | taxonomy of file kinds, what is frozen vs living, forward SPEC/STATUS/prompt templates |
| `docs_boundary.md` | `docs/` is the published surface; `development/` is never a Sphinx source, never linked from the site |
| `verification_gates.md` | the gate battery, baseline counts, output-reading rules, caches |
| `reference_mining.md` | sources before code; `REFERENCES.lock` append-at-consultation; the pinned reference pair |
| `review_protocol.md` | the reusable skeptical-reviewer protocol tasks append their checklists to |
