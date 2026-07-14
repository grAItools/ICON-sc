# icon_fortran

**Source:** ICON open-source release — icon-model.org → gitlab.dwd.de/icon/icon-model;
consulted via the canonical public mirror https://gitlab.dkrz.de/icon/icon-model
**Pinned:** tag `icon-2026.04-public`
(`8597da45ef4b86323f3fb844caedc4ae5e1ffc01`) — corpus pin, see `REFERENCES.lock`
entries and `development/records/000_overview_record.md` §3.
**License:** BSD-3

## Role in the project

Scientific ground truth for algorithm reading: `mo_satad`, graupel (`gscp_*`),
`mo_solve_nonhydro`, `mo_nh_stepping`, `mo_nh_testcases*`, `mo_vertical_grid`.
When ICON Fortran and icon4py disagree, icon4py's serialized data is the
verification target and the disagreement goes in the step's STATUS record
(working agreement, `AGENTS.md`).

## Gotchas

- **gitlab.dwd.de does not resolve; use the gitlab.dkrz.de mirror.**
- The 2026.04 tag can be ahead of icon4py v0.2.0's algorithm state — e.g. `mo_satad`
  at this tag adds a `supsatfac` supersaturation factor absent from icon4py v0.2.0
  (both reduce to the same algorithm with the default namelist; recorded in the S07
  STATUS record), and no longer exposes satad-internal thermo functions (moved to
  `mo_thdyn_functions`).

## Consultation ledger

`grep -n 'id = "icon-fortran' REFERENCES.lock` — one `[[ref]]` entry per consultation.
