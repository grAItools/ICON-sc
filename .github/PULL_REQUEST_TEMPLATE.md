## Work unit

`development/work/specs/____` / `development/work/plans/____` — one work unit per PR.

## Definition of done (AGENTS.md)

- [ ] Every spec acceptance criterion has a passing test (list any waived, with justification in the report)
- [ ] Frozen interfaces match the spec exactly
- [ ] `development/references/lock.toml` updated for all mined sources (SHAs included)
- [ ] Gate green: pytest (`not gpu` minimum + required markers), ruff, mypy (core strict), lint-imports
- [ ] No data files, no dependency pin changes
- [ ] Report written (`development/work/reports/report-NNNN-*.md`; artifacts, if any, in `report-NNNN-*/`): built / deviations / follow-ups / artifacts

## Deviations & notes for the reviewer

<!-- tolerances touched? interfaces clarified? upstream surprises? -->
