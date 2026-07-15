# naming_conventions — document naming, work ids, and allocation

Scope: how development-memory files are named, how work ids are allocated, and the
sign-off marker. The scheme is TD-50.1 (`ADR-0006`, superseding the sequence/suffix
clauses of TD-35.1/`ADR-0003`); the proposal, spec, plan, and report of one work unit
share one number.

- **Work documents** (`work/{proposals,specs,plans,reports}/`):
  `<kind>-<NNNN>-<kebab-slug>.md`, or `report-NNNN-<kebab>/` for multi-file
  deliverables (inner files keep their names; optional untracked
  `report-NNNN-<kebab>/artifacts/`).
  - `NNNN` = four-digit zero-padded work id; allocation order = assignment order;
    numeric values preserved from the pre-0050 three-digit scheme (never
    compact-renumbered).
  - One number per work unit, shared across its lifecycle files:
    `spec-0005-vault-plan-t1.md` / `plan-0005-…` / `report-0005-…/`. Single-kind
    documents consume one number.
  - Kind prefix = singular of the subfolder: `proposal-`, `spec-`, `plan-`, `report-`.
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
- **Case split (deliberate):** kebab-case for the numbered documents in `work/` and
  `ADRs/`; snake_case for `policies/*` (unnumbered, topical, living rules).
- **Exemptions:** `policies/` files are unnumbered snake_case, one topic each; all
  `README.md` files, `REGISTRY.md`, and `archive/` contents (documents arrive there
  under their dying names) are also exempt.
- **History:** the corpus was renamed to `NNN_<slug>_<kind>` by work unit 035 and to
  this scheme by work unit 0050. The former S-series ("S08"), P-series, and N-series
  names and the 035 names survive only as historical wording in frozen documents and
  as `lock.toml` `step` ids — the remap tables in `development/REGISTRY.md` §2 and §2b
  are the bridge (two hops for pre-035 names). Never renumber history.
- **Branch convention:** `work/NNNN-<kebab>` (forward-only; existing remote branches
  keep their historical `step/SXX-*` / `task/NN-*` / `work/NNN-*` names).
- **Sign-off marker:** any line in a report that requires trunk/human action carries
  the literal token `TD-PENDING:` and gets a row in `development/REGISTRY.md` in the
  same PR. `grep -rn "TD-PENDING" development/` must only return lines whose register
  row is still open.
