# naming_conventions — ID series, file naming, and the allocation rule

Scope: how development-memory files are named and how S/P/N-series numbers and ADR
numbers are allocated. The spec, plan, and record of one work unit share one ID.

- **S-series** (implementation steps): one ID `SXX_<snake>` across the kind-folders —
  `development/specs/SXX_<snake>.md`, `development/plans/SXX_<snake>.md`,
  `development/records/SXX_<snake>/STATUS.md`, optional untracked
  `development/records/SXX_<snake>/artifacts/`. Phase steps continue the series
  (S15+). Two digits, zero-padded.
- **P-series** (phase outlines): `development/ideas/PN_<snake>.md`. The file stays as
  a record after the phase is specced (`Status:` header per `development/ideas/README.md`).
- **N-series** (post-slice tasks): two-digit, strictly monotonic, never reused, gaps
  never backfilled. Bands: `0x` ordering prefixes (only `00_OVERVIEW`), `10–19`
  protocols, `20+` tasks.
  - Prompt file: `development/plans/NN_<snake>.md`. **Allocation rule:** the number is
    allocated by adding a row to the register table in `development/plans/README.md`
    *at assignment*, even when the prompt text is delivered ad hoc and never committed
    (the row then says so). The register is the single allocator; on a collision the
    first-registered number wins and the latecomer takes the next free one.
  - Execution report: `development/records/NN_<snake>_REPORT.md` (flat, suffixed).
  - Document-deliverable (design doc / proposal / multi-file): subdirectory
    `development/records/NN_<snake>/NN_<snake>.md` (+ sidecar files).
  - External-facing drafts: thematic subdirs under `development/records/` as the
    owning prompt names them; indexed in `development/records/README.md`.
- **ADRs** (the one exception to snake_case): `development/adr/NNNN-<kebab-title>.md`,
  four-digit, allocated by the next free number in `development/adr/README.md`'s index.
- **Policies**: `development/policies/<snake_topic>.md`, one topic each.
- **Sign-off marker:** any line in a STATUS or report that requires trunk/human action
  carries the literal token `TD-PENDING:` and gets a row in `development/REGISTRY.md`
  in the same PR. `grep -rn "TD-PENDING" development/` must only return lines whose
  register row is still open.
