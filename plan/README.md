# plan/ — repo process memory: map, naming, templates, boundary

This directory is the repo-internal process memory: plans, contracts, records, and
registers for the agent-driven implementation. Rationale and full analysis:
`plan/prompts/reports/29_plan_structure/29_plan_structure.md` (task 29). This file states
the rules; it does not restate the analysis.

## 1. Taxonomy — what each file kind is and how it may change

| Kind | Liveness | Where |
|---|---|---|
| Canonical architecture | trunk-edited only | `docs/architecture/*.md` |
| Working agreement | living, trunk-gated | `AGENTS.md` (+ `CLAUDE.md` shim) |
| Provenance ledger | append-only | `REFERENCES.lock` |
| Plan overview / task register | living | `plan/00_OVERVIEW.md`, `plan/prompts/README.md` |
| Trunk-decision register | living, append-mostly | `plan/TRUNK_DECISIONS.md` |
| Step contract (SPEC) | frozen at step start | `plan/steps/SXX_*/SPEC.md` |
| Step how-to (PLAN) | frozen at step start | `plan/steps/SXX_*/PLAN.md` |
| Step record (STATUS) | frozen at merge — never retro-edited | `plan/steps/SXX_*/STATUS.md` |
| Phase outline | frozen until specced into steps | `plan/outlines/PN_*.md` |
| Review protocol | living (task checklists append) | `plan/prompts/10_REVIEW_PROTOCOL.md` |
| Task prompt | frozen at assignment | `plan/prompts/NN_*.md` |
| Task execution report | frozen at task merge | `plan/prompts/reports/NN_*_REPORT.md` |
| Design document / proposal | frozen; decisions extracted to the register | `plan/prompts/reports/NN_<name>/NN_<name>.md` |
| External-facing draft | frozen after human publishes | `plan/prompts/reports/<theme>/` (e.g. `upstream/`, `prs/`) |
| Process report (slice-level) | frozen | `plan/IMPLEMENTATION_REPORT.md` (its §5/§6 are superseded going forward by `TRUNK_DECISIONS.md`) |
| Generated artifact | regenerate, never hand-edit | `docs/names_registry.md` (committed, headered); `docs/_build/`, `plan/steps/*/artifacts/` (untracked) |
| Published site source | living | `docs/{conf.py,index.md,glossary.md,tutorials/,api/}` |
| Agent tooling / CI templates | living | `.claude/`, `.opencode/`, `.github/` |

## 2. Naming convention

- **S-series** (implementation steps): `plan/steps/SXX_<snake>/` with `SPEC.md`,
  `PLAN.md`, `STATUS.md`, optional untracked `artifacts/`. Phase steps continue the
  series (S15+). Two digits, zero-padded.
- **P-series** (phase outlines): `plan/outlines/PN_<snake>.md`. The file stays as a
  record after the phase is specced.
- **N-series** (post-slice tasks): two-digit, strictly monotonic, never reused, gaps
  never backfilled. Bands: `0x` plan-root ordering prefixes (only `00_OVERVIEW`),
  `10–19` protocols, `20+` tasks.
  - Prompt file: `plan/prompts/NN_<snake>.md`. **Allocation rule:** the number is
    allocated by adding a row to the register table in `plan/prompts/README.md` *at
    assignment*, even when the prompt text is delivered ad hoc and never committed
    (the row then says so). The register is the single allocator; on a collision the
    first-registered number wins and the latecomer takes the next free one.
  - Execution report: `plan/prompts/reports/NN_<snake>_REPORT.md` (flat, suffixed).
  - Document-deliverable (design doc / proposal / multi-file): subdirectory
    `plan/prompts/reports/NN_<snake>/NN_<snake>.md` (+ sidecar files).
  - External-facing drafts: thematic subdirs under `reports/` as the owning prompt
    names them; indexed in `plan/prompts/reports/README.md`.
- **Sign-off marker:** any line in a STATUS or report that requires trunk/human action
  carries the literal token `TD-PENDING:` and gets a row in `plan/TRUNK_DECISIONS.md`
  in the same PR. `grep -rn "TD-PENDING" plan/` must only return lines whose register
  row is still open.

## 3. Forward templates (new steps/tasks only; existing files are records — no retro-edits)

- **SPEC.md**: Goal · In scope · Out of scope (may be "nothing excluded") · **Frozen
  interfaces — mandatory; write "none" explicitly** · Acceptance criteria. An absent
  frozen-interface section is a template violation, not a statement.
- **STATUS.md**: header `**Branch:** … · **Date:** … · **State:** …` ·
  `## 1. What was built` · `## 2. Acceptance criteria → tests` · `## 3. Deviations` ·
  `## 4. Tolerances & sign-off flags` (each flag on a `TD-PENDING:` line) ·
  `## 5. Gates (dated)` · `## 6. Follow-ups` · `## 7. Artifacts` ·
  `## 8. Review fixes (round N)`.
  **Artifact-reference rule:** `plan/steps/*/artifacts/` is gitignored; cite every
  untracked artifact *with its regeneration command*, never as a bare path.
- **Task prompts** follow the register format of `plan/prompts/README.md`
  (Hard rules → Items → Acceptance criteria → Verification gates → Review checklist,
  cf. `21_ci_hardening.md`).

## 4. plan/ ↔ docs/ boundary policy

1. `plan/` is repo-internal process memory: never a Sphinx source, never hyperlinked
   from `docs/` site pages (prose mentions without links are fine), never deployed.
2. `docs/` is the published surface. Its only trunk-frozen zone is `architecture/`;
   everything else there is living site source.
3. Plan content wanted user-facing is *rewritten* under `docs/` (tutorials cite
   `plan/IMPLEMENTATION_REPORT.md` as author-side source material, without links) —
   never included, symlinked, or excerpted mechanically. P7's architecture
   canonicalization owns any future exception.
4. Generated files are committed under `docs/` only with a `GENERATED FILE` header
   naming the regeneration command (`docs/names_registry.md` is the precedent).
