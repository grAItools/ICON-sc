# policies/ — living rules for development

Policies are living, trunk-gated; agents follow them and propose changes via a `proposal.md` in a `work/<NNNN>-<slug>/` folder
or a `development/REGISTRY.md` row — never by silently editing during a work unit.

| Policy | One line |
|---|---|
| `agent-workflow.md` | how a work unit runs: spec → plan → mine references → implement → gates → report → one PR; the implementer/reviewer loop |
| `naming-conventions.md` | the `<NNNN>-<slug>/` per-unit folder scheme, the number-allocation rule, exemptions, the `TD-PENDING:` marker |
| `document-kinds.md` | taxonomy of file kinds, what is frozen vs living, forward spec/plan/report templates |
| `docs-boundary.md` | `docs/` is the published surface; `development/` is never a Sphinx source, never linked from the site |
| `verification-gates.md` | the gate battery, baseline counts, output-reading rules, caches |
| `reference-mining.md` | sources before code; `development/references/lock.toml` append-at-consultation; the pinned reference pair |
| `review-protocol.md` | the reusable skeptical-reviewer protocol work units append their checklists to |
| `repository-layout.md` | the repository layout, packaging boundaries, and layout conventions |
