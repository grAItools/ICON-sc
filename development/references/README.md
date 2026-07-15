# references/ — reference cards, provenance ledger, local documents

One card per external source: canonical URL, the pin and where it is decided, license,
role in the project, gotchas, and a pointer into the consultation ledger.

**Ownership rule:** cards are living but updated only when a pin or corpus decision
changes; `lock.toml` (this folder) is the machine ledger, appended per consultation —
the cards never duplicate its per-consultation entries.
Non-redistributable local documents (PDFs) live in `local/` (gitignored).

| Card / file | Source |
|---|---|
| `lock.toml` | the machine provenance ledger — append-only, one `[[ref]]` per consulted source, schema in its header (ex-`REFERENCES.lock` at the repo root, moved by work unit 0050, TD-50.3) |
| `icon4py.md` | github.com/C2SM/icon4py — primary implementation donor |
| `gt4py.md` | github.com/GridTools/gt4py — DSL substrate |
| `icon-fortran.md` | ICON open-source Fortran — scientific ground truth |
| `sympl.md` | sympl upstream + stubbiali `oop` fork — component/property semantics |
| `tasmania.md` | github.com/stubbiali/tasmania — federation/coupling reference implementations |
| `icon-tutorial-2025.md` | DWD/MPI-M ICON tutorial 2025 — process ordering, idealized configuration |
| `ubbiali-thesis.md` | Ubbiali ETH thesis — coupling scheme definitions and convergence orders |
| `icon-grid-generator.md` | github.com/ofuhrer/icon-grid-generator — synthetic test grids |
