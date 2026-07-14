Review the implementation of work unit $ARGUMENTS ($ARGUMENTS = NNN_<slug>) on the
current branch as a skeptical reviewer, per development/policies/review_protocol.md.

Check, in order: (1) every acceptance criterion of development/specs/$ARGUMENTS_spec.md
(or of the plan development/plans/$ARGUMENTS_plan.md where the work unit has no spec)
has a test and it passes — run them; (2) Frozen interfaces match the spec signatures
exactly; (3) REFERENCES.lock entries exist for the sources the plan told the
implementer to mine, with SHAs; (4) tolerances match spec values — flag any loosening
and check the record justifies it; (5) no data files, no dep bumps, import-linter
clean; (6) the record development/records/$ARGUMENTS_record/ is honest about
deviations. Produce a review report with verdict: approve / request-changes, listing
findings by severity.
