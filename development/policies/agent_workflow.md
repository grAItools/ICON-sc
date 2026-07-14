# agent_workflow — how a step or task is executed

Scope: the working sequence for implementing a step (S-series) or task (N-series),
and the implementer/reviewer loop.

## Workflow for a step

1. Pick a step whose dependencies are merged (DAG: `development/records/00_OVERVIEW.md`
   §2). Branch: `step/SXX-short-name`; tasks branch as `task/NN-short-name`.
2. Read the spec (`development/specs/SXX_*.md`) fully, then the plan
   (`development/plans/SXX_*.md`). SPEC's *Frozen interfaces* are load-bearing for
   concurrent lanes: implement them exactly; if a signature must change, that is a
   trunk decision, not a local fix.
3. **Mine references before writing code** — per
   `development/policies/reference_mining.md`; every consulted source lands in
   `REFERENCES.lock` at mining time.
4. Implement. Tests alongside. Tolerances stated in SPECs are contracts: loosening one
   requires a written justification in the step's STATUS record and human sign-off in
   the PR.
5. Gate before PR — the full battery and baselines in
   `development/policies/verification_gates.md`.
6. Write `development/records/SXX_*/STATUS.md` (template in
   `development/policies/records_and_liveness.md`): what was built, deviations + why,
   follow-ups, benchmark/plot artifacts if the SPEC asks. One PR per step/task; fill
   the PR template.

## Implementer/reviewer loop (tasks)

1. Give the implementer agent the **full text of one prompt file** (not a summary).
2. When it reports done, give a **fresh agent** (never the same one) the full text of
   `development/policies/review_protocol.md` plus the task file's "Review checklist"
   section.
3. Iterate implementer ↔ reviewer until the reviewer's verdict is `approve`.
4. Merge only after approve. One branch and one PR per task.
