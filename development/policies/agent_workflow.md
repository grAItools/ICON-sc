# agent_workflow — how a work unit is executed

Scope: the working sequence for implementing a work unit, and the
implementer/reviewer loop.

## Workflow for a work unit

1. Pick a work unit whose dependencies are merged (the 0001–0014 slice DAG:
   `development/work/reports/report-0000-overview.md` §2). Branch: `work/NNNN-<kebab>`.
2. Read the spec (`development/work/specs/spec-NNNN-<kebab>.md`) fully, then the plan
   (`development/work/plans/plan-NNNN-<kebab>.md`). The spec's *Frozen interfaces* are
   load-bearing for concurrent lanes: implement them exactly; if a signature must
   change, that is a trunk decision, not a local fix.
3. **Mine references before writing code** — per
   `development/policies/reference_mining.md`; every consulted source lands in
   `development/references/lock.toml` at mining time.
4. Implement. Tests alongside. Tolerances stated in specs are contracts: loosening one
   requires a written justification in the work unit's report and human sign-off in
   the PR.
5. Gate before PR — the full battery and baselines in
   `development/policies/verification_gates.md`.
6. Write the report `development/work/reports/report-NNNN-<kebab>{.md,/}` (STATUS
   template in `development/policies/document_kinds.md`): what was built, deviations +
   why, follow-ups, benchmark/plot artifacts if the spec asks. One PR per work unit;
   fill the PR template.

## Implementer/reviewer loop

1. Give the implementer agent the **full text of one plan file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `development/policies/review_protocol.md` plus the plan file's "Review checklist"
   section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per work unit.
