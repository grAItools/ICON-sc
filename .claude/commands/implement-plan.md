Implement work unit $ARGUMENTS ($ARGUMENTS = NNN_<slug>, e.g. 025_cf_multistage_t1).

1. Read development/specs/$ARGUMENTS_spec.md in full if the work unit has a spec, then
   development/plans/$ARGUMENTS_plan.md, then AGENTS.md if not already in context.
   Confirm all dependency work units (spec header) are merged on the current base; stop
   and report if not.
2. Create branch work/$ARGUMENTS with the first underscore as a dash (work/NNN-<slug>).
3. Execute the plan in order. Reference mining first: discover real module paths, append
   every consulted source to REFERENCES.lock with commit SHAs.
4. Implement against the spec's Frozen interfaces exactly. Write the acceptance tests as
   you go — acceptance criteria are the definition of done, not an afterthought.
5. Run the full gate (development/policies/verification_gates.md). Iterate until green.
6. Write the record development/records/$ARGUMENTS_record/ (template in
   development/policies/records_and_liveness.md) and commit everything on the branch
   with clear messages. Do not push; report readiness for PR.
