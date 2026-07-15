# references/ — per-source reference cards

One card per external source: canonical URL, the pin and where it is decided, license,
role in the project, gotchas, and a pointer into the consultation ledger.

**Ownership rule:** cards are living but updated only when a pin or corpus decision
changes; `development/references/lock.toml` (repo root) is the machine ledger, appended per
consultation — the cards never duplicate its per-consultation entries.
Non-redistributable local documents (PDFs) live in `local/` (gitignored).

| Card | Source |
|---|---|
| `icon4py.md` | github.com/C2SM/icon4py — primary implementation donor |
| `gt4py.md` | github.com/GridTools/gt4py — DSL substrate |
| `icon_fortran.md` | ICON open-source Fortran — scientific ground truth |
| `sympl.md` | sympl upstream + stubbiali `oop` fork — component/property semantics |
| `tasmania.md` | github.com/stubbiali/tasmania — federation/coupling reference implementations |
| `icon_tutorial_2025.md` | DWD/MPI-M ICON tutorial 2025 — process ordering, idealized configuration |
| `ubbiali_thesis.md` | Ubbiali ETH thesis — coupling scheme definitions and convergence orders |
| `icon_grid_generator.md` | github.com/ofuhrer/icon-grid-generator — synthetic test grids |
