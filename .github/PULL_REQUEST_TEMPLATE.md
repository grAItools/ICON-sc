## Step

`plan/steps/____` — one step per PR.

## Definition of done (AGENTS.md)

- [ ] Every SPEC acceptance criterion has a passing test (list any waived, with STATUS.md justification)
- [ ] Frozen interfaces match the SPEC exactly
- [ ] `REFERENCES.lock` updated for all mined sources (SHAs included)
- [ ] Gate green: pytest (`not gpu` minimum + step-required markers), ruff, mypy (core strict), lint-imports
- [ ] No data files, no dependency pin changes
- [ ] `STATUS.md` written: built / deviations / follow-ups / artifacts

## Deviations & notes for the reviewer

<!-- tolerances touched? interfaces clarified? upstream surprises? -->
