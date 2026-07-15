# naming_conventions — document naming, the global sequence, and allocation

Scope: how development-memory files are named, how document numbers are allocated, and
the sign-off marker. The scheme is TD-35.1 (`adr 046`); the idea, spec, plan, and
record of one work unit share one number.

- **Lifecycle documents** (`ideas/`, `specs/`, `plans/`, `records/`, `adr/`):
  `NNN_<slug>_<kind>.md`, or `NNN_<slug>_<kind>/` for multi-file deliverables (inner
  files keep their names; optional untracked `NNN_<slug>_record/artifacts/`).
  - `NNN` = three-digit zero-padded global sequence, numbering consecutively across
    kinds; allocation order = assignment order.
  - One number per work unit, shared across its lifecycle files:
    `spec-0005-vault-plan-t1.md` / `_plan.md` / `_record/`. Single-kind documents (an
    ADR, a standalone record) consume one number.
  - Kind suffix = singular of the folder name: `idea`, `spec`, `plan`, `record`, `adr`.
- **Allocation rule:** the number is allocated by adding a row to the document register
  (`development/REGISTRY.md` §1) *at assignment*, even when the plan text is delivered
  ad hoc and never committed (the row then says so). The register is the single
  allocator: numbers are strictly monotonic, never reused; gaps are never backfilled
  (015–019 stay open). On a collision, the first-registered number wins and the
  latecomer takes the next free one.
- **Exemptions:** `policies/` files are unnumbered snake_case, one topic each; all
  `README.md` files, `REGISTRY.md`, and `archive/` contents (documents arrive there
  under their dying names) are also exempt.
- **History:** the corpus was renamed to this scheme by work unit 035. The former
  S-series ("S08"), P-series, N-series, and `NNNN-<kebab-title>` ADR names survive
  only as historical wording in frozen records and as `development/references/lock.toml` ids — the
  remap table in `development/REGISTRY.md` §2 is the bridge. Never renumber history.
- **ADR citation form:** `adr NNN` (e.g. `adr 044`). An accepted ADR is frozen except
  its `Status:` field.
- **Branch convention:** `work/NNN-<slug>` (forward-only; existing remote branches keep
  their historical `step/SXX-*` / `task/NN-*` names).
- **Sign-off marker:** any line in a record that requires trunk/human action carries
  the literal token `TD-PENDING:` and gets a row in `development/REGISTRY.md` in the
  same PR. `grep -rn "TD-PENDING" development/` must only return lines whose register
  row is still open.
