## Work unit

`development/specs/____` / `development/plans/____` — one work unit per PR.

## Definition of done (AGENTS.md)

- [ ] Every spec acceptance criterion has a passing test (list any waived, with justification in the record)
- [ ] Frozen interfaces match the spec exactly
- [ ] `REFERENCES.lock` updated for all mined sources (SHAs included)
- [ ] Gate green: pytest (`not gpu` minimum + required markers), ruff, mypy (core strict), lint-imports
- [ ] No data files, no dependency pin changes
- [ ] Record written (`development/records/NNN_*_record/`): built / deviations / follow-ups / artifacts

## Deviations & notes for the reviewer

<!-- tolerances touched? interfaces clarified? upstream surprises? -->
