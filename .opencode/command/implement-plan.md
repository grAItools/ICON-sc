---
description: Implement a ICON-sc work unit end-to-end per the agent working agreement
---
Implement work unit $ARGUMENTS ($ARGUMENTS = NNNN-<kebab>, e.g. 0025-cf-multistage-t1).

1. Read development/work/specs/spec-$ARGUMENTS.md in full if the work unit has a spec,
   then development/work/plans/plan-$ARGUMENTS.md, then AGENTS.md if not already in
   context. Confirm all dependency work units (spec header) are merged on the current
   base; stop and report if not.
2. Create branch work/$ARGUMENTS.
3. Execute the plan in order. Reference mining first: discover real module paths, append
   every consulted source to development/references/lock.toml with commit SHAs.
4. Implement against the spec's Frozen interfaces exactly. Write the acceptance tests as
   you go — acceptance criteria are the definition of done, not an afterthought.
5. Run the full gate (development/policies/verification-gates.md). Iterate until green.
6. Write the report development/work/reports/report-$ARGUMENTS.md, with artifacts (if any) in development/work/reports/report-$ARGUMENTS/, (template in
   development/policies/document-kinds.md) and commit everything on the branch
   with clear messages. Do not push; report readiness for PR.
