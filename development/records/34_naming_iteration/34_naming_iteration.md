# Task 34 — naming-convention iteration: evaluation of the owner's seven points

**Branch:** `task/34-naming-iteration` · **Date:** 2026-07-14 · **Deliverable:** this
evaluation (nothing moved or renamed; the migration is a later task, executed after the
owner settles §9). Analysis of `main` = `90d38a0`, post task-33 + TD-33.4.

---

## 0. Executive summary

The owner's seven points are evaluated one by one. Verdicts up front:

1. `DECISIONS.md` → **`REGISTRY.md`**: adopt, and let the rename do more work — the file
   becomes the single registry for *both* document numbers and trunk decisions (§1).
2. The repo-layout document **is** policy material: move it to
   `development/policies/repo_layout.md` as a living policy, remove it from the published
   site (§2).
3. The `NNN_<slug>_<kind>` scheme: adopt with **one global sequence** and **one number per
   work unit** shared across its idea/spec/plan/record files; full remap table in §3.
4. Terminology sweep ("step"/"task"/"prompt" → kind vocabulary): adopt for **living files
   and tooling only** — frozen records keep their historical wording under the
   content-frozen rule (ADR-0002); anything else would retro-edit history (§4).
5. `development/README.md` lifecycle + conventions section: adopt as specified (§5).
6. Classification audit of `plans/` and `specs/`: everything is correctly placed; no moves.
   One forward-looking rule falls out of the audit (§6).
7. Retroactive ADRs: **two** are worth writing (docs stack; grid-generator adoption), plus
   one new ADR for this naming scheme itself (§7).

The migration this implies is sized in §8: ~65 renames, a path-retarget pass over the
development tree, a terminology sweep across ~13 living files, and one `docs/` edit — the
same mechanics as task 33, fully covered by the ADR-0002 sanctioned-migration class.

## 1. `DECISIONS.md` → `REGISTRY.md`

Adopt. "DECISIONS.md sitting next to a folder of decision records" is a genuine confusion;
the reviewer-facing distinction (ledger rows vs reasoning documents) does not survive first
contact with the two names. `REGISTRY.md` also names what the file actually does better
than `DECISIONS.md` ever did — it *registers* things.

**Proposal — let the rename absorb the number allocator too.** The task-number register
currently lives in `development/plans/README.md` (a leftover of its `plan/prompts/` origin).
With the unified numbering of §3, the allocator is no longer about plans — it numbers every
lifecycle document. One file, two tables:

- **Document register** (the allocator): `NNN | slug | kinds present | status` — one row
  per work unit or standalone document, allocated at assignment, strictly monotonic, never
  reused, gaps never backfilled (rules unchanged, just re-homed).
- **Decision register**: the TD rows exactly as today (IDs, `TD-PENDING:` contract,
  same-PR row rule, statuses — all untouched).

`plans/README.md` keeps only the how-to-use-a-plan instructions (implementer/reviewer loop,
give-the-full-text rule). Inbound references to `DECISIONS.md`: 6 living files (policies,
READMEs, root README, adr files) — direct updates; ~8 frozen records — mechanical path
retarget, the same class C2 already applied when `TRUNK_DECISIONS.md` became `DECISIONS.md`.
The folder stays lowercase `adr/` (TD-33.3); the owner's `ADRs/` spelling in the request is
read as referring to it, not as a rename instruction.

## 2. `docs/architecture/symcon_repo_layout.md` → `development/policies/repo_layout.md`

Adopt the move. Content audit: the file is (a) the repo tree with per-directory rationale,
(b) packaging/namespace rules, (c) the import-boundary contracts that lint-imports
enforces, (d) typing/caching conventions. All four are *rules the repository follows* —
policy by this project's own definition — and none of it is the scientific architecture
that `symcon_architecture.md` (v1.3) canonicalizes. The authority-order sentence cites only
`symcon_architecture.md`, so the constitutional doc set is untouched by the move.

Consequences, priced:

- The file changes liveness: trunk-frozen → living policy (trunk-gated like every policy).
  That is an *upgrade* for this content — the layout drifts with the repo (task 33's
  TD-33.4 diff was exactly such a drift-fix, needing owner ceremony a policy would not).
- It leaves the published site. `docs/index.md` drops one toctree line (73) and rewrites
  the line-47/48 prose to link only the architecture document (the layout mention becomes
  a plain-prose pointer, per the docs-boundary policy). Site users lose a page that was
  always developer-facing; sphinx `-W` re-verified at migration.
- The `Edit(docs/architecture/**)` deny glob then protects exactly the one canonical doc —
  cleaner, not weaker.
- Content is restructured into the policies format (scope line, sections, last-review
  header) — a rewrite is legitimate because the policy becomes the living source; the
  frozen original remains readable at its old path in git history.
- Inbound: `README.md`, `docs/index.md`, `REGISTRY.md` cells (living, direct edits);
  5 frozen records + the task-33 diff artifact (mechanical path retarget).

## 3. The `NNN_<slug>_<kind>` naming scheme

Adopt, with three clarifications the owner's sketch leaves open:

1. **One global sequence** (the owner's example — `001_…_spec.md`, `002_…_adr.md` — numbers
   consecutively across kinds). NNN = allocation order in the document register (§1), three
   digits, zero-padded.
2. **One number per work unit, shared across its lifecycle files.** A feature's idea, spec,
   plan, and record all carry the same NNN with different kind suffixes
   (`005_vault_plan_t1_spec.md` / `_plan.md` / `_record/`). This preserves the join that
   makes register rows, branches, and `REFERENCES.lock` step ids line up — the alternative
   (a fresh number per document) would give one feature four unrelated numbers.
   Single-kind documents (an ADR, a standalone record) simply consume one number.
3. **Kind suffix = singular of the folder name**: `idea`, `spec`, `plan`, `record`, `adr`.
   Multi-file deliverables become a *folder* named `NNN_<slug>_<kind>/`; inner files keep
   their names (frozen files are moved, never renamed-and-reworded).

**Exemptions (decision point 3b).** `policies/*` stay unnumbered snake_case: policies are
living, topical, looked up by subject, and have no meaningful "order"; numbering them buys
nothing and costs churn in the most-cited filenames (`verification_gates.md` is referenced
from every plan). Also exempt: `README.md` files, `REGISTRY.md`, and `archive/` contents
(documents arrive there under their dying names). If the owner prefers literal "always",
policies can take numbers too — the migration cost is small; the recommendation stands.

### Remap of the existing corpus

Existing numbers are preserved where they exist (they are cited as *words* in frozen
records, which never change); previously-unnumbered or scheme-colliding documents get fresh
numbers at migration, in the order below. The full old→new table becomes a permanent
section of `REGISTRY.md` (greppable, and the bridge for historical `REFERENCES.lock` step
ids like "S08", which stay as written — the lock is untouchable).

| Old | New |
|---|---|
| `records/00_OVERVIEW.md` | `records/000_overview_record.md` (pre-history keeps the zero) |
| `specs/S01…S14_<slug>.md` | `specs/001…014_<slug>_spec.md` |
| `plans/S01…S14_<slug>.md` | `plans/001…014_<slug>_plan.md` |
| `records/S01…S14_<slug>/` | `records/001…014_<slug>_record/` (inner `STATUS.md` etc. unchanged) |
| `plans/{20,21,22,23,24,25,28,30,33}_<slug>.md` | `plans/0NN_<slug>_plan.md` (same numeric value) |
| `records/{26,28,31}_<slug>_REPORT.md` | `records/0NN_<slug>_record.md` |
| `records/{27,29,32,33}_<slug>/` | `records/0NN_<slug>_record/` |
| `records/34_naming_iteration/` (this doc) | `records/034_naming_iteration_record/` |
| *(035 = the migration task itself)* | `plans/035_naming_migration_plan.md` + `records/035_naming_migration_record/` |
| `records/IMPLEMENTATION_REPORT.md` | `records/036_implementation_report_record.md` |
| `ideas/P2…P7_<slug>.md` | `ideas/037…042_p2…p7_<slug>_idea.md` (phase tag survives in the slug) |
| `adr/0001…0003-…` | `adr/043…045_<slug>_adr.md` (four-digit kebab → global three-digit snake) |
| *(new ADRs, §7)* | `adr/046_document_naming_scheme_adr.md`, `047_docs_stack_adr.md`, `048_gridgen_adoption_adr.md` |

Numbers 015–019 remain gaps forever (the review protocol consumed 10 before becoming a
policy; 15–19 were never allocated) — consistent with the never-backfill rule. Next free
number after migration: 049.

## 4. Terminology sweep — scope and limits

Adopt for living files and tooling; the kind vocabulary ("work unit 021", "the spec", "the
plan", "the record") replaces "step S21", "task 21", "prompt". Surfaces:

- `AGENTS.md`, `CLAUDE.md`, root `README.md`, PR template, all 8 policies, the 5 folder
  READMEs, `development/README.md`, `REGISTRY.md` column headers and header rules.
- **Tooling**: `.claude/commands/implement-step.md` + `.opencode` twin → renamed
  `implement-plan.md` (argument: NNN or NNN_slug); `review-step.md` → `review-work.md`;
  `CLAUDE.md`'s `/implement-step` mention updated; the `.claude/settings.json` glob already
  targets `development/specs/**` and survives the rename pattern unchanged.
- **Branch convention** (forward-only): `step/SXX-*` / `task/NN-*` → `work/NNN-<slug>`.
  Existing remote branches keep their historical names.

**Hard limit (decision point 4b):** frozen records keep their historical wording — "step
S08", "task 26", "prompt" stay wherever a frozen document says them. The owner's "change or
remove explicitly all existing mentions" cannot reach frozen content without repealing
ADR-0002 (content-frozen); the sweep therefore covers every *living* surface, and the
REGISTRY remap table translates historical vocabulary. `REFERENCES.lock`: historical `step`
fields stay; future entries put the NNN work-unit number in the same field (schema note
appended is not needed — the field is free-text by schema).

## 5. `development/README.md` — conventions and lifecycle

Adopt as specified. The README gains: (a) the naming convention of §3 in five lines;
(b) the lifecycle — *idea* (`ideas/`, living until graduated) → *spec* (`specs/`, the
frozen contract: requirements, interfaces, acceptance criteria) → *plan* (`plans/`, the
frozen work instructions an agent executes) → *record* (`records/`, the frozen account of
what actually happened, written at merge) — with the cross-cutting instruments (policies =
standing rules, adr = reasoning behind structural decisions, REGISTRY.md = numbers +
sign-offs); (c) `archive/` explained as the home for superseded/no-longer-relevant
documents kept for historical reference — dead, never authoritative, never linked as a
source of rules.

## 6. Classification audit of `plans/` and `specs/`

Audited all 24 plans and 14 specs against the kind definitions:

- The 14 S-series SPEC/PLAN pairs are correctly split (contracts vs work instructions) —
  they were *born* as that split.
- The 9 ex-prompt plans (020–025, 028, 030, 033) are work instructions with embedded
  acceptance criteria and review checklists — plans, correctly placed. None is a spec in
  disguise: none defines a frozen *interface contract* independent of its execution
  instructions; their acceptance criteria are gate conditions for the work, not product
  contracts.
- `plans/README.md` content splits per §1 (allocator → REGISTRY, usage → stays).
- Ideas (P-outlines) and records spot-checked: correctly placed.

**No historical moves.** One forward rule falls out, for `records_and_liveness.md`: when a
future work unit needs a real contract (frozen interfaces, tolerances), it gets a separate
`NNN_<slug>_spec.md`; plans embed only *gate* criteria. This is what S-series always did
and what one-shot maintenance work units may skip.

## 7. Retroactive ADRs

Reviewed the register and the record corpus against the ADR rule of thumb ("changes how
future code/docs are structured"). Worth writing (both have their reasoning already
recorded, so these are extractions, not inventions):

- **`047_docs_stack_adr.md`** — Sphinx 8 + MyST + Napoleon + furo + Pages-artifact flow,
  Google-style docstrings, convert-on-touch policy. Source: TD-27.1–3 + the task-27 plan
  record. Structural: every docs contribution follows it.
- **`048_gridgen_adoption_adr.md`** — icon-grid-generator as archive-independent fixture
  source with the **not-for-parity boundary**, version-keyed cache, quarantine in
  `symcon.icon.testing`. Source: task-26 record. Structural: the boundary constrains every
  future validation/convergence work unit (P7's ladder cites it).

Plus **`046_document_naming_scheme_adr.md`** for this iteration itself (global sequence,
number-per-work-unit, kind suffixes, exemptions, remap). Not worth ADRs: tolerance
sign-offs (ledger rows by ADR-0003), the wgtfacq/graupel findings (bug records, not
decisions), the pinned-reference-pair rules (already `reference_mining.md` policy), the
L4-reference freeze (already `verification_gates.md` caches policy).

## 8. Migration sizing (plan = work unit 035, written after §9 is settled)

| Move class | Count |
|---|---|
| `git mv` renames (specs 14, plans 23, records 22+folders, ideas 6, adr 3, layout doc 1) | ~65 |
| Fresh documents (2 retro ADRs, 1 naming ADR, REGISTRY restructure, README sections) | ~6 |
| Path retargets inside development/ (old filenames cited in living + frozen docs) | est. 150–250 strings |
| Living-file terminology sweep | ~13 files |
| `docs/` edits | `docs/index.md` only (2 spots) + sphinx re-verify |
| Tooling renames | 4 command files + CLAUDE.md |
| Register work | REGISTRY rename + allocator absorption + remap table + TD rows (TD-34.x) |

Same commit discipline as task 33 (pure-rename commit, retarget-only commit, new-content
commits, purity checks); all frozen-content edits confined to path strings under ADR-0002.

## 9. Decision points for the owner

1. **REGISTRY scope**: rename only, vs rename + absorb the number allocator (one registry
   for numbers and decisions). — *Recommend absorb (§1).*
2. **Layout doc**: move to `policies/repo_layout.md` and unpublish, vs keep in
   `docs/architecture/`. — *Recommend move (§2).*
3. **Numbering**: (a) one global sequence with number-per-work-unit as in §3 — *recommend*;
   (b) exempt policies/READMEs/REGISTRY/archive from NNN, vs literal "always". —
   *Recommend exempt (§3).*
4. **Terminology sweep**: (a) living files + tooling + forward branch convention
   `work/NNN-<slug>` — *recommend*; (b) confirm frozen records keep historical wording
   (the content-frozen rule) — *recommend confirm; the alternative repeals ADR-0002.*
5. **Remap table** (§3): confirm the number assignments, incl. gaps 015–019 staying open,
   ADRs renumbered into the global sequence, and `000` for the overview.
6. **Retroactive ADRs**: the two proposed (docs stack, gridgen), vs more/fewer. —
   *Recommend exactly these two + the naming ADR.*

---
*(end of evaluation — migration plan, work unit 035, to be commissioned after §9 is answered)*
