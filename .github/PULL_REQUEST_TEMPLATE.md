## Work unit

`development/work/<NNNN>-<slug>/` (spec.md + plan.md) — one work unit per PR.

## Definition of done (AGENTS.md)

- [ ] Every spec acceptance criterion has a passing test (list any waived, with justification in the report)
- [ ] Frozen interfaces match the spec exactly
- [ ] `development/references/lock.toml` updated for all mined sources (SHAs included)
- [ ] Gate green: pytest (`not gpu` minimum + required markers), ruff, mypy (core strict), lint-imports
- [ ] No data files, no dependency pin changes
- [ ] Report written (`development/work/<NNNN>-<slug>/report.md`; artifacts, if any, in `<NNNN>-<slug>/artifacts/`): built / deviations / follow-ups / artifacts

## Deviations & notes for the reviewer

<!-- tolerances touched? interfaces clarified? upstream surprises? -->
