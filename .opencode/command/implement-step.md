---
description: Implement a symcon plan step end-to-end per the agent working agreement
---
Implement plan step $ARGUMENTS.

1. Read development/specs/$ARGUMENTS.md in full, then development/plans/$ARGUMENTS.md, then
   AGENTS.md if not already in context. Confirm all dependency steps (SPEC header) are merged
   on the current base; stop and report if not.
2. Create branch step/$ARGUMENTS (kebab-case the suffix).
3. Execute the PLAN in order. Reference mining first: discover real module paths, append
   every consulted source to REFERENCES.lock with commit SHAs.
4. Implement against the SPEC's Frozen interfaces exactly. Write the acceptance tests as you
   go — acceptance criteria are the definition of done, not an afterthought.
5. Run the full gate (AGENTS.md, Workflow item 5). Iterate until green.
6. Write development/records/$ARGUMENTS/STATUS.md (built / deviations / follow-ups / artifacts) and
   commit everything on the branch with clear messages. Do not push; report readiness for PR.
