---
description: Skeptical review of a work-unit implementation against its spec and plan
---
Review the implementation of work unit $ARGUMENTS ($ARGUMENTS = NNNN-<kebab>) on the
current branch as a skeptical reviewer, per development/policies/review-protocol.md.

Check, in order: (1) every acceptance criterion of development/work/$ARGUMENTS/spec.md
(or of the plan development/work/$ARGUMENTS/plan.md where the work unit has no
spec) has a test and it passes — run them; (2) Frozen interfaces match the spec
signatures exactly; (3) development/references/lock.toml entries exist for the sources
the plan told the implementer to mine, with SHAs; (4) tolerances match spec values —
flag any loosening and check the report justifies it; (5) no data files, no dep bumps,
import-linter clean; (6) the report development/work/$ARGUMENTS/report.md (artifacts, if any, in development/work/$ARGUMENTS/artifacts/)
is honest about deviations. Produce a review report with verdict: approve /
request-changes, listing findings by severity.
