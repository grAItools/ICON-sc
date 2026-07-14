# Work unit 049 — `development/work/` iteration: evaluation of the owner's three points

**Branch:** `work/049-structure-iteration` · **Date:** 2026-07-14 · **Deliverable:** this
evaluation (nothing moved; the migration is work unit 050, executed after the owner
settles §5). Analysis of `main` = `e65b483`.

## 0. Executive summary

All three points are adoptable. Verdicts:

1. `adr/` → **`ADRs/`** with Nygard `<NNNN>-<kebab-title>` from `0000`, independent
   sequence: adopt. The independence *reverses one clause of adr 046* (the global
   sequence), but point 2 makes every kind's numbering independent anyway, so this is the
   consistent completion of the owner's direction, recorded as a new superseding ADR (§1).
2. `work/{proposals,specs,plans,reports}` with `<kind>-<NNNN>-<kebab-slug>`: adopt, with
   one load-bearing clarification — **numeric values are preserved (widened to four
   digits), not compact-renumbered** (§2). `ideas→proposals` and `records→reports`: adopt.
3. `REFERENCES.lock` → `development/references/lock.toml`: adopt — the file parses as
   valid TOML today (51 `[[ref]]` entries, verified with a TOML parser), so the extension
   is honest, and the move completes `references/` as the one home for cards + machine
   ledger + local copies (§3).

Target tree in §4; decision points in §5. Migration sizing: ~80 renames + retargets
(~110 lock-path references dominate), the third and final terminology sweep, REGISTRY
re-key — work-unit-050 scale ≈ 035's.

## 1. `ADRs/` + Nygard `<NNNN>-<kebab-title>`, independent from zero

- **Uppercase `ADRs/`** breaks the all-lowercase folder rule twice affirmed before; the
  owner's re-proposal is read as a deliberate exception for an initialism. Adopt; the
  naming policy records it as the *only* non-lowercase folder, so it never becomes a
  precedent by accident.
- **Independent `NNNN` from zero**: with point 2 giving every work kind its own sequence,
  a shared global sequence no longer exists to join; ADRs keeping 043+ would be a fossil
  of a dead scheme. Remap (order preserved): `043→0000-development-tree-reorganization`,
  `044→0001-content-frozen-records`, `045→0002-decision-register-and-adrs`,
  `046→0003-document-naming-scheme`, `047→0004-docs-stack`, `048→0005-gridgen-adoption`.
  The new ADR for THIS iteration becomes `0006-work-tree-and-kind-prefixed-names`, and
  `0003`'s status becomes `superseded-by-0006` **for its sequence/suffix clauses only**
  (its work-unit-number-sharing and exemption clauses survive and are restated in 0006).
- **Citation form**: `ADR-0006` (four digits + prefix is unambiguous against kind-prefixed
  work ids). The `adr 04N` citation form from 035 dies with the remap; living files sweep.

## 2. `development/work/` + `<kind>-<NNNN>-<kebab-description-slug>`

**The grouping** cleanly splits the tree into the lifecycle stream (`work/`) and the
cross-cutting instruments (`policies/`, `ADRs/`, `references/`, `archive/`, `REGISTRY.md`,
`README.md`) — those six are absent from the owner's sketch and are read as *staying*,
not deleted (decision point 5c). One level deeper is a fair price for the split.

**The renames** `ideas→proposals`, `records→reports`: adopt. "Proposals" matches how the
folder is actually used; "reports" kills the records-vs-ADRs ambiguity the owner names.
Consequences swept in living files: the lifecycle vocabulary becomes
proposal → spec → plan → report; the policy `records_and_liveness.md` is renamed
`document_kinds.md` (its subject is kinds + liveness, and "records" would be a stale word
in its own filename); the kind suffix `_record` in filenames becomes the kind prefix
`report-`.

**The numbering — the one place the sketch needs interpretation.** "`NNNN` start from
zero, independent of ids outside `work/`, matching within subfolders for related items."
Two readings:

- *(a) Compact renumber from 0000* — every work unit gets its third id in three days;
  the REGISTRY remap chain becomes two hops (`S08 → 008 → 00NN?`); every frozen-document
  path retargeted again to *different numbers*; nothing is gained but density.
- *(b) Preserve numeric values, widen to four digits* — `000→0000` (overview),
  `001–014 → 0001–0014`, `020–036 → 0020–0036`, `037–042 → 0037–0042` (proposals),
  `049 → 0049` (this document). "From zero" is satisfied (0000 exists), independence is
  satisfied (ADRs leave the sequence), cross-subfolder matching is preserved
  (`spec-0005-vault-plan-t1.md` / `plan-0005-…` / `report-0005-…`), and the
  `REFERENCES.lock` bridge stays one lookup (`S08 → 0008`). Gaps (0015–0019 etc.) remain
  open per the never-backfill rule.

**Recommend (b), strongly.** Decision point 1.

**Slug case**: kebab inside `work/` and `ADRs/` per the sketch; `policies/` stay
snake_case unnumbered (their exemption is untouched). The mixed convention is recorded in
the naming policy as deliberate: kebab for numbered lifecycle/decision documents, snake
for topical living rules.

**Folder-shaped reports**: multi-file deliverables keep the folder form —
`reports/report-0004-coupling-algebra/` (inner `STATUS.md`, `artifacts/` unchanged).
Everything single-file is flat: `reports/report-0026-gridgen-integration.md`.

## 3. `REFERENCES.lock` → `development/references/lock.toml`

Adopt. Evidence and consequences:

- **Format**: parses as valid TOML (51 entries; inline comments and multi-line strings
  all conformant). `.toml` gains syntax highlighting and machine-readability signaling;
  nothing about the append-only discipline changes.
- **Location**: `references/` then holds the complete provenance story — 8 living cards
  (human layer), `lock.toml` (machine ledger), `local/` (gitignored copies). The
  root-level visibility the lock had is replaced by pointers that already exist in
  AGENTS.md and `policies/reference_mining.md` (both living).
- **Cost**: ~110 files mention `REFERENCES.lock` (13 living — direct edits; the rest
  frozen — mechanical path retargets under the ADR-0001-content-frozen rule, the same
  class as both prior migrations). The lock's own header title line is updated
  (append-only binds the entries, not the schema comment); `[[ref]]` entries are NOT
  touched — their `step` ids stay historical and resolve via the REGISTRY remap table.
- The `.gitignore` and tooling do not reference the lock; `docs/` does not link it.

## 4. Target tree (owner's sketch + the six retained instruments)

```
development/
├── README.md                 map + lifecycle (proposal → spec → plan → report)
├── REGISTRY.md               work-id register (4-digit) + remap tables + decision register
├── policies/                 snake_case, unnumbered (incl. records_and_liveness.md → document_kinds.md)
├── ADRs/                     NNNN-<kebab-title>.md, own sequence from 0000 (next: 0007)
├── work/
│   ├── proposals/            proposal-NNNN-<kebab>.md          (ex-ideas, 0037–0042)
│   ├── specs/                spec-NNNN-<kebab>.md              (0001–0014 + future)
│   ├── plans/                plan-NNNN-<kebab>.md              (0001–0014, 0020–0035 + future)
│   └── reports/              report-NNNN-<kebab>(.md|/)        (ex-records, incl. 0000 overview)
├── references/               cards (8, snake) + lock.toml (ex-REFERENCES.lock) + local/
└── archive/                  unchanged (dying names)
```

Tooling/code surfaces the migration must carry (same classes as 035): the
`Edit(development/specs/*_spec.md)` deny glob → `Edit(development/work/specs/spec-*.md)`;
`implement-plan`/`review-work` command files (argument becomes `NNNN-<kebab>`); the
`.gitignore` artifacts glob → `development/work/reports/*/artifacts/`; the two
order-test path strings and two benchmark docstrings → `work/reports/report-0004-…` /
`report-0005-…` / `report-0014-…`; branch convention `work/NNNN-<kebab>` (4-digit).

## 5. Decision points for the owner

1. **Numbering remap**: preserve numeric values widened to 4 digits (recommended, §2) vs
   compact renumber from 0000.
2. **ADR sequence**: independent from 0000 with the §1 remap and `ADR-0006` superseding
   the sequence clauses of `0003` — confirm.
3. **`records_and_liveness.md` → `document_kinds.md`** policy rename — confirm or name it
   otherwise.
4. **Lock move**: `development/references/lock.toml` with the header title updated —
   confirm (alternative: keep at repo root for visibility).
5. Confirm sketch omissions are retentions: (a) `REGISTRY.md` stays at `development/`
   root; (b) `archive/` stays; (c) folder `README.md`s and reference cards stay; kebab in
   `work/`+`ADRs/`, snake in `policies/` as §2 states.

---
*(end of evaluation — migration = work unit 0050, commissioned after §5 is answered)*
