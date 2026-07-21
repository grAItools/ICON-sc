# naming-conventions — document naming, work ids, and allocation

Scope: how development-memory files are named, how work ids are allocated, and the
sign-off marker. The scheme is TD-50.1 (`ADR-0006`, superseding the sequence/suffix
clauses of TD-35.1/`ADR-0003`) as amended by TD-51.1/51.2 (`ADR-0007`: kebab-case
everywhere, flat reports) and TD-54.1 (per-unit folders); the proposal, spec, plan, and
report of one work unit live in one folder `work/<NNNN>-<slug>/` and share one number.

- **Kebab-case everywhere:** every filename under `development/` is kebab-case —
  including `policies/`, `references/` cards, and `archive/` contents — never snake
  or mixed (TD-51.1, `ADR-0007`). Only `README.md` (conventional, kept everywhere)
  and `lock.toml` (a fixed name) are excepted.
- **Work documents** live in one folder per work unit, `work/<NNNN>-<kebab-slug>/`,
  holding the bare-kind files `proposal.md`, `spec.md`, `plan.md`, `report.md` — only
  those that exist (TD-54.1, superseding the per-kind-subfolder / `<kind>-<NNNN>-<slug>.md`
  filename scheme of TD-50.1 and the flat-report clause of TD-51.2).
  - **Artifacts folder:** only when a report has extra artifacts (tracked sidecars
    or untracked generated files) do they live in the unit's `artifacts/` subfolder
    (`work/<NNNN>-<kebab-slug>/artifacts/`), existing ONLY when artifacts exist.
  - **Gitignore convention:** an `artifacts/` folder holding ONLY untracked artifacts
    gets its own explicit `.gitignore` line (e.g.
    `development/work/0004-coupling-algebra/artifacts/`); folders holding
    tracked sidecars are not ignored. Untracked artifacts are cited in their report
    *with their regeneration command*, never as a bare path.
  - `NNNN` = four-digit zero-padded work id; allocation order = assignment order;
    numeric values preserved from the pre-0050 three-digit scheme (never
    compact-renumbered).
  - One folder per work unit; the id and slug are encoded once, in the folder name
    (`0005-vault-plan-t1/` → `spec.md` / `plan.md` / `report.md`). A single-kind work
    unit gets a folder with just that one file.
  - The work-id sequence is independent of everything outside `work/`.
- **ADRs** (`ADRs/` — the repo's *only* non-lowercase folder, a deliberate initialism
  exception, TD-50.2): Nygard `NNNN-<kebab-title>.md`, **own sequence from 0000**
  (next free in `ADRs/README.md`). Citation form: `ADR-NNNN` (e.g. `ADR-0001`). An
  accepted ADR is frozen except its `Status:` field.
- **Allocation rule:** the number is allocated by adding a row to the document register
  (`development/REGISTRY.md` §1) *at assignment*, even when the plan text is delivered
  ad hoc and never committed (the row then says so). The register is the single
  allocator: numbers are strictly monotonic, never reused; gaps are never backfilled
  (0015–0019 stay open; 0043–0048, consumed by the former ADR rows, are never reused).
  On a collision, the first-registered number wins and the latecomer takes the next
  free one.
- **Scheme exemptions (case is never exempt):** `policies/` files are unnumbered
  (kebab-case, one topic each); all `README.md` files, `REGISTRY.md`, and `archive/`
  contents (documents arrive there under their dying names, kebab-cased) are exempt
  from the `<NNNN>-<slug>` folder scheme only.
- **History:** the corpus was renamed to `NNN_<slug>_<kind>` by work unit 035, to
  the `work/` scheme by work unit 0050, kebab-cased/flattened by work unit 0051, and
  regrouped into per-unit folders `work/<NNNN>-<slug>/` by work unit 0054. The former
  S-series ("S08"), P-series, and N-series names, the 035 names, the pre-0051
  snake/folder names, and the pre-0054 by-kind paths (`work/specs/spec-…`) survive only
  as historical wording in frozen documents and as `lock.toml` `step` ids — the remap
  tables in `development/REGISTRY.md` §2, §2b, §2c, and §2d are the bridge (two hops for
  pre-035 names). Never renumber history.
- **Branch convention:** `work/NNNN-<kebab>` (forward-only; existing remote branches
  keep their historical `step/SXX-*` / `task/NN-*` / `work/NNN-*` names).
- **Sign-off marker:** any line in a report that requires trunk/human action carries
  the literal token `TD-PENDING:` and gets a row in `development/REGISTRY.md` in the
  same PR. `grep -rn "TD-PENDING" development/` must only return lines whose register
  row is still open.
