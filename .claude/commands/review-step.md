Review the implementation of plan step $ARGUMENTS on the current branch as a skeptical
reviewer.

Check, in order: (1) every SPEC acceptance criterion has a test and it passes — run them;
(2) Frozen interfaces match the SPEC signatures exactly; (3) REFERENCES.lock entries exist
for the sources the PLAN told the implementer to mine, with SHAs; (4) tolerances match SPEC
values — flag any loosening and check STATUS.md justifies it; (5) no data files, no dep
bumps, import-linter clean; (6) STATUS.md is honest about deviations. Produce a review
report with verdict: approve / request-changes, listing findings by severity.
