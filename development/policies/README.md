# policies/ — living rules for development

Policies are living, trunk-gated; agents follow them and propose changes via `ideas/`
or a `development/REGISTRY.md` row — never by silently editing during a work unit.

| Policy | One line |
|---|---|
| `agent_workflow.md` | how a work unit runs: spec → plan → mine references → implement → gates → record → one PR; the implementer/reviewer loop |
| `naming_conventions.md` | the `NNN_<slug>_<kind>` scheme, the number-allocation rule, exemptions, the `TD-PENDING:` marker |
| `document_kinds.md` | taxonomy of file kinds, what is frozen vs living, forward spec/record/plan templates |
| `docs_boundary.md` | `docs/` is the published surface; `development/` is never a Sphinx source, never linked from the site |
| `verification_gates.md` | the gate battery, baseline counts, output-reading rules, caches |
| `reference_mining.md` | sources before code; `development/references/lock.toml` append-at-consultation; the pinned reference pair |
| `review_protocol.md` | the reusable skeptical-reviewer protocol work units append their checklists to |
| `repo_layout.md` | the repository layout, packaging boundaries, and layout conventions (formerly `docs/architecture/symcon_repo_layout.md`) |
