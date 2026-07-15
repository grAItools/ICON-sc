# document_kinds — what each file kind is and how it may change

Scope: the taxonomy of development-memory kinds, their liveness rules, and the forward
templates for new specs, plans, and records.

## 1. Taxonomy

| Kind | Liveness | Where |
|---|---|---|
| Canonical architecture | trunk-edited only | `docs/architecture/*.md` |
| Working agreement | living, trunk-gated | `AGENTS.md` (+ `CLAUDE.md` shim) |
| Provenance ledger | append-only | `development/references/lock.toml` |
| Policy | living, trunk-gated | `development/policies/*.md` |
| ADR | frozen after accepted; `Status:` field mutable | `development/adr/NNN_*_adr.md` |
| Idea / phase outline | living until graduated (`Status:` header; graduated → spec NNN) | `development/ideas/NNN_*_idea.md` |
| Document + decision register | living | `development/REGISTRY.md` (document numbers §1, remap §2, TD rows) |
| Work-unit contract (spec) | frozen at acceptance | `development/specs/NNN_*_spec.md` |
| Work-unit plan | frozen at assignment | `development/plans/NNN_*_plan.md` |
| Work-unit record (STATUS/REPORT) | frozen at merge — never retro-edited | `development/records/NNN_*_record{.md,/}` |
| Design document / proposal | frozen; decisions extracted to the register | `development/records/NNN_*_record/` (the deliverable *is* the document) |
| Process report (slice-level) | frozen | `development/work/reports/report-0036-implementation-report.md` (its §5/§6 are superseded going forward by `REGISTRY.md`) |
| Reference card | living (updated on pin/corpus decisions) | `development/references/*.md` |
| Archive | dead — kept for reference; nothing authoritative | `development/archive/` |
| Generated artifact | regenerate, never hand-edit | `docs/names_registry.md` (committed, headered); `docs/_build/`, `development/records/*/artifacts/` (untracked) |
| Published site source | living | `docs/{conf.py,index.md,glossary.md,tutorials/,api/}` |
| Agent tooling / CI templates | living | `.claude/`, `.opencode/`, `.github/` |

**Content-frozen rule (adr 044):** "frozen" means content-frozen — mechanical path
retargeting confined to link/path strings is permitted in a sanctioned migration
commit, isolated so `git diff --word-diff` shows path strings only; header-line
*additions* above the original text may be sanctioned case-by-case by the migration
plan. All other edits to frozen documents remain violations.

## 2. Forward templates (new work units only; existing files are records — no retro-edits)

- **Spec** (`development/specs/NNN_*_spec.md`): Goal · In scope · Out of scope (may be
  "nothing excluded") · **Frozen interfaces — mandatory; write "none" explicitly** ·
  Acceptance criteria. An absent frozen-interface section is a template violation,
  not a statement.
- **STATUS record** (`development/records/NNN_*_record/STATUS.md`): header
  `**Branch:** … · **Date:** … · **State:** …` ·
  `## 1. What was built` · `## 2. Acceptance criteria → tests` · `## 3. Deviations` ·
  `## 4. Tolerances & sign-off flags` (each flag on a `TD-PENDING:` line) ·
  `## 5. Gates (dated)` · `## 6. Follow-ups` · `## 7. Artifacts` ·
  `## 8. Review fixes (round N)`.
  **Artifact-reference rule:** `development/records/*/artifacts/` is gitignored; cite
  every untracked artifact *with its regeneration command*, never as a bare path.
- **Plans** follow the register format (Hard rules → Items → Acceptance criteria →
  Verification gates → Review checklist, cf. `development/work/plans/plan-0021-ci-hardening.md`);
  how plans are used: `development/work/plans/README.md`.
