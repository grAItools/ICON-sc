# icon_tutorial_2025

**Source:** DWD/MPI-M ICON tutorial —
https://www.dwd.de/EN/ourservices/nwv_icon_tutorial/nwv_icon_tutorial.html
**Pinned:** 2025 edition — corpus pin, see `development/work/reports/report-0000-overview.md` §3;
local copy `development/references/local/icon-model-tutorial-2025.pdf`.
**License:** not recorded

## Role in the project

Process ordering, fast/slow semantics, JW/idealized configuration (ch. 3–4).
§3.7.2 is the coupling-position ground truth for the fast-physics calling sequence
(satad twice around microphysics) encoded as machine-checkable
`coupling_constraints`.

## Gotchas

- Local PDF only (not redistributable); obtain from the ICON training pages and drop
  into `development/references/local/`.
- §3.7.1 cadence rule ("rounded up to the next advective time step") disagrees with
  the frozen S03 `CallingFrequency` (nearest multiple, ties up) — disagreement
  recorded in the S09 STATUS record; both coincide where dt_slow is an exact
  multiple.

## Consultation ledger

`grep -n 'id = "icon-tutorial-2025' development/references/lock.toml` — one `[[ref]]` entry per
consultation.
