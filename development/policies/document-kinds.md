# document-kinds — what each file kind is and how it may change

Scope: the taxonomy of development-memory kinds, their liveness rules, and the forward
templates for new specs, plans, and reports. Report shape and the artifacts-folder
rule: TD-51.2 (`ADR-0007`).

## 1. Taxonomy

| Kind | Liveness | Where |
|---|---|---|
| Canonical architecture | trunk-edited only | `docs/architecture/*.md` |
| Working agreement | living, trunk-gated | `AGENTS.md` (+ `CLAUDE.md` shim) |
| Provenance ledger | append-only | `development/references/lock.toml` |
| Policy | living, trunk-gated | `development/policies/*.md` |
| ADR | frozen after accepted; `Status:` field mutable | `development/ADRs/NNNN-<kebab-title>.md` |
| Proposal / phase outline | living until graduated (`Status:` header; graduated → spec NNNN) | `development/work/<NNNN>-<slug>/proposal.md` |
| Document + decision register | living | `development/REGISTRY.md` (work ids §1, remaps §2–§2d, TD rows) |
| Work-unit contract (spec) | frozen at acceptance | `development/work/<NNNN>-<slug>/spec.md` |
| Work-unit plan | frozen at assignment | `development/work/<NNNN>-<slug>/plan.md` |
| Work-unit report | frozen at merge — never retro-edited | `development/work/<NNNN>-<slug>/report.md` (artifacts, only when they exist, in the unit's `<NNNN>-<slug>/artifacts/` subfolder) |
| Design document / evaluation | frozen; decisions extracted to the register | `development/work/<NNNN>-<slug>/report.md` (the deliverable *is* the document) |
| Process report (slice-level) | frozen | `development/work/0036-implementation-report/report.md` (its §5/§6 are superseded going forward by `REGISTRY.md`) |
| Reference card | living (updated on pin/corpus decisions) | `development/references/*.md` |
| Archive | dead — kept for reference; accepts any kind; nothing authoritative | `development/archive/` |
| Generated artifact | regenerate, never hand-edit | `docs/names_registry.md` (committed, headered); `docs/_build/`; untracked report-artifact folders (per-folder `.gitignore` line, e.g. `development/work/0004-coupling-algebra/artifacts/`) |
| Published site source | living | `docs/{conf.py,index.md,glossary.md,tutorials/,api/}` |
| Agent tooling / CI templates | living | `.claude/`, `.opencode/`, `.github/` |

**Content-frozen rule (ADR-0001):** "frozen" means content-frozen — mechanical path
retargeting confined to link/path strings is permitted in a sanctioned migration
commit, isolated so `git diff --word-diff` shows path strings only; header-line
*additions* above the original text may be sanctioned case-by-case by the migration
plan. All other edits to frozen documents remain violations.

## 2. Forward templates (new work units only; existing files are frozen — no retro-edits)

- **Spec** (`development/work/<NNNN>-<slug>/spec.md`): Goal · In scope · Out of scope
  (may be "nothing excluded") · **Frozen interfaces — mandatory; write "none"
  explicitly** · Acceptance criteria. An absent frozen-interface section is a template
  violation, not a statement.
- **Report** (`development/work/<NNNN>-<slug>/report.md`; artifacts, only when they
  exist, in the unit's `<NNNN>-<slug>/artifacts/` subfolder — TD-54.1): header
  `**Branch:** … · **Date:** … · **State:** …` ·
  `## 1. What was built` · `## 2. Acceptance criteria → tests` · `## 3. Deviations` ·
  `## 4. Tolerances & sign-off flags` (each flag on a `TD-PENDING:` line) ·
  `## 5. Gates (dated)` · `## 6. Follow-ups` · `## 7. Artifacts` ·
  `## 8. Review fixes (round N)`.
  **Artifact-reference rule:** a report folder holding ONLY untracked artifacts gets
  its own explicit `.gitignore` line (folders holding tracked sidecars are not
  ignored); cite every untracked artifact *with its regeneration command*, never as
  a bare path.
- **Plans** follow the register format (Hard rules → Items → Acceptance criteria →
  Verification gates → Review checklist,
  cf. `development/work/0021-ci-hardening/plan.md`);
  how plans are used: `development/work/README.md`.
