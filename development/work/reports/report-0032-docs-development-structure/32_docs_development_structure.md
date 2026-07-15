# Task 32 — `docs/development/` reorganization: evaluation of the owner's proposal

**Branch:** `task/32-docs-development-structure` · **Deliverable:** this document (evaluation
only — nothing moved, renamed, or edited; the migration plan is a *later* task, written only
after the owner agrees a final structure via §7). · **Date:** 2026-07-14 (analysis of
`main` = `3a744fa`, post task-31 merge).

**Standing of this evaluation vs TD-29.1.** TD-29.1 (signed-off 2026-07-13) ratified the
zero-move structure. The owner's proposal is a deliberate override: a full reorganization
supersedes it. The register handles this by its own convention — TD-29.1's `Status` becomes
`superseded(TD-32.1)` when the owner signs off the new structure (draft row in §6). Task 29's
*data* (inventory §1, cross-reference census §4.3, taxonomy §2) is reused throughout as fact;
only its *conclusion* ("move nothing") is on the table.

**Where this document lives.** It was commissioned into
`development/work/reports/report-0032-docs-development-structure/` per the current (task-29) convention.
Under the refined structure of §2 it would be
`docs/development/records/32_docs_development_structure/` — task deliverables are records.
The irony is the same bootstrapping one task 29 recorded; it resolves the same way: the
location is correct under the rules in force at commission time, and history freezes in place
(§5). Register note: per the allocation rule, number 32 needs a row in
`development/work/plans/README.md` — this task's file-scope constraint (new files only) means that row
lands with the migration task's PR; recorded here so the allocator does not drift.

---

## 0. Executive summary

The proposal's *taxonomy* is right and maps almost 1:1 onto the kinds the repo already
distinguishes (task 29 §2.1): policies ≈ K2/K4 living rules, ADRs ≈ the decision content now
squeezed into register rows, specs/plans ≈ K5/K6, references ≈ K3's human layer. Adopting it
for **future** work is a clear improvement over the zero-move status quo, which optimized for
link stability at the cost of a flat, register-mediated tree that only insiders can navigate.

Five verdicts up front:

1. **`docs/development/` must be excluded from the Sphinx build** — publishing it would put
   agent-facing process memory on the user site and, worse, feed hundreds of
   repo-relative-linked process files through the `-W` gate (every unresolvable target or
   orphan page fails CI). One `exclude_patterns` entry; policy in §4.
2. **The proposal names no home for historical records or the sign-off register** — the two
   most load-bearing content classes in the repo. §2.8 adds `records/` (future STATUS files,
   execution reports) and keeps `TRUNK_DECISIONS.md` as a ledger *beside* `adr/`, not merged
   into it.
3. **History freezes in place; only future work uses the new tree.** The task-29 census
   counts ~90 inbound references to `plan/` paths, including *runtime paths in committed test
   code* and agent permission globs. Migrating S01–S14 buys nothing and breaks records that
   must never be edited. `plan/` becomes a read-only archive with a banner. (§2.6, §5.)
4. **`plans/` absorbs `development/plans/`** — the owner's definition of plans ("usable as prompts
   for mid-tier LLM coding agents") *is* the existing prompt discipline; two trees for one
   kind would drift. The task-number register (single allocator) survives as
   `plans/README.md`. (§2.6.)
5. **`docs/user/` is adoptable but is the single most breakage-prone move** (conf.py,
   toctrees, ~23 relative links, `tools/names_audit.py`, published URLs). Do it atomically
   with the enumerated fix list in §2.1, or drop the nesting — decision point 3.

---

## 1. Ground rules the evaluation holds fixed

- `docs/` is a Sphinx source tree (task 28): `sphinx-build -b html docs …` runs in
  `lint.yml` (PR gate) and `docs.yml` (Pages deploy from `main`). The task-31 gate uses
  `-E -W --keep-going`; warnings are failures.
- `plan/` ↔ `docs/` boundary policy (`development/archive/plan_tree_map.md` §4): plan is never a Sphinx source,
  never linked from site pages, never deployed. The proposal *relocates* the boundary
  (development memory moves inside `docs/`); it must not *erase* it — §4 restates it for the
  new geometry.
- Frozen records are never retro-edited (AGENTS.md; `development/archive/plan_tree_map.md` §1 liveness column).
  Every structure decision below is priced against that rule.
- `REFERENCES.lock` is the append-only provenance ledger (51 entries, 41 source ids,
  schema in header, appended at mining time, referenced by ~30 files). Nothing here may
  weaken it.
- Authority order (`AGENTS.md`): architecture doc > SPEC > PLAN. Any structure change that
  moves the files named in that sentence touches every restatement of it.

---

## 2. Folder-by-folder evaluation

### 2.1 `docs/user/` (tutorials, api, …)

**Strengths.** Makes the audience split (scientists vs developers/agents) visible in the
tree, not just in prose; symmetric with `development/`; gives `glossary.md` and the
generated `names_registry.md` an obvious home.

**Weaknesses / cost.** Everything under `docs/` is live site source, so this is the one part
of the proposal that touches running machinery. Enumerated, everything that must move or
change together (from grep, this branch):

| # | Artifact | Change |
|---|---|---|
| 1 | `docs/tutorials/` (4 files), `docs/api/` (15 files), `docs/glossary.md`, `docs/names_registry.md` | `git mv` → `docs/user/…` (21 files) |
| 2 | `docs/conf.py` `exclude_patterns` | `"api/README.md"` → `"user/api/README.md"` |
| 3 | `docs/index.md` | 4 toctree entries + 4 body links (`tutorials/index`, `api/index`, `glossary`, `names_registry`) |
| 4 | Relative links inside tutorials | ~23 hits for `../architecture/…` / `glossary.md#…` in `00_*`/`01_*`; same-directory glossary links survive the move, `../architecture` becomes `../../architecture` |
| 5 | `tools/names_audit.py` | `DOCS_PAGE = REPO_ROOT / "docs" / "names_registry.md"` (line 19) + module docstring (line 4) — the generated file's path is code |
| 6 | Published URLs | `…/tutorials/*`, `…/api/*` → `…/user/…` — GitHub Pages has no server redirects; any circulated link 404s. Site is days old; cost ≈ zero *now*, grows monotonically |
| 7 | intersphinx | outbound only (`python`) — no inbound consumers yet; anchors change if anyone maps us later |
| 8 | CI workflows | **no change** — `docs.yml`/`lint.yml` build the whole `docs/` dir; `test-cpu.yml` examples-smoke runs `examples/*.py`, not docs paths |
| 9 | Historical mentions | `development/records/S01…/STATUS.md`, prompts 28, reports 27/28 cite `docs/api/`/`docs/tutorials/` — frozen, stay as written (archive banner covers the drift, §5) |

**Verdict.** Adoptable at a bounded, one-PR cost — but note the honest alternative: if
`development/` is excluded from the build (§2.2), then *everything published is already
user-facing*, and `user/` buys naming symmetry, not separation. Recommendation: adopt it
anyway (the tree should say what it means), atomically, now, while URL breakage is free.
Decision point 3.

**Placement details:** `docs/index.md` stays at `docs/` root (Sphinx master doc);
`docs/architecture/` stays where it is (§2.8-f).

### 2.2 `docs/development/` and the Sphinx-source tension

The pivotal question: everything under `docs/` is inside the build tree. Three options:

- **(a) Fully excluded** (`exclude_patterns += ["development"]`). The site stays user-only.
  The `-W` gate never sees process files. Process docs keep their current hygiene rules
  (repo-relative links, links to `packages/**`, to `REFERENCES.lock`, to gitignored
  artifacts) — none of which are Sphinx-resolvable. Cost: one conf.py line + the boundary
  policy restated (§4). Discoverability loss is minor: agents navigate by path, not by site.
- **(b) Fully published.** Audience mixing (weak-model prompts and tolerance ledgers on the
  user site), and a hard technical cost: every one of the dozens of process files must be in
  a toctree (else orphan warnings fail `-W`), with every link target resolvable. That
  converts the anti-drift prompt discipline into ongoing Sphinx-lint work for zero user
  value.
- **(c) Selective** (publish `policies/` + `adr/`, exclude the rest). Defensible at P7 when
  external contributors exist, but today it doubles the rule count for marginal benefit.

**Verdict: (a), revisit (c) at P7 publication** (the P7 outline already owns "presets, docs";
a published-decision-history want was anticipated by task 29 §5's ADR verdict). One further
alternative deserves the owner's eyes: keeping development memory *out* of `docs/` entirely
(top-level `development/`) preserves the clean invariant "docs/ = site source" with zero
conf.py coupling. The owner's grouping ("all documentation under docs/") is coherent and
this evaluation accepts it, but it is a genuine fork — decision point 1. Under (a) the
invariant becomes: *published surface = `docs/` minus `docs/development/`*; `docs.yml` and
`lint.yml` need no change since exclusion happens in conf.py.

### 2.3 `docs/development/policies/`

**Strengths.** Today's living rules are scattered across `AGENTS.md` (hard rules),
`development/archive/plan_tree_map.md` (taxonomy, naming, templates, boundary), and `development/work/plans/README.md`
(invariants, verification-gate baselines, caches). One policy per file, updated as needed,
is strictly better than three multi-purpose READMEs.

**Constraints.** (i) `AGENTS.md`/`CLAUDE.md` must stay at the repo root — agent harnesses
discover them there; they become thin: authority order + hard rules + pointers into
`policies/`. (ii) The weak-model anti-drift convention — *prompts restate the
non-negotiables inline* — must survive; policies are the source the restatements are copied
from, never a substitute for restating. (iii) The gate-baseline table and caches section are
load-bearing verbatim and update with merges; they become `policies/verification_gates.md`
with the same keep-current rule.

**Suggested initial split** (contents exist today, only re-homed): `naming_conventions.md`,
`records_and_liveness.md` (taxonomy + no-retro-edit rule + templates),
`docs_boundary.md` (§4), `verification_gates.md`, `reference_mining.md` (lock discipline),
`agent_workflow.md`. No numbering — policies are living and topical; snake_case; each with a
one-line header naming its owner (trunk) and last-review date; `README.md` index.

### 2.4 `docs/development/ADRs/` → recommend `adr/`

**Casing.** Every existing directory in the repo is lowercase (`plan/`, `docs/`, `steps/`,
`outlines/`, `prompts/`, `reports/`); `ADRs/` would be the sole exception, and the
adr-tools/Nygard ecosystem convention is `doc/adr/`. Recommend lowercase singular `adr/`.
(The sketch lists `ideas` without a trailing slash — read as a folder; noted for the record.)

**Numbering.** Nygard `NNNN-<kebab-title>.md` starting at `0001`, statuses
*proposed / accepted / superseded-by-NNNN* in the header, `README.md` index table. Kebab
inside adr filenames (ecosystem convention) vs snake elsewhere is a deliberate, contained
exception — or use snake for uniformity; decision point 5 carries both.

**Relationship to `TRUNK_DECISIONS.md` — the important part.** TD rows and Nygard ADRs
overlap but are not the same kind:

| | TD register row | Nygard ADR |
|---|---|---|
| Grain | one sentence, verbatim tolerances/signatures | context / decision / consequences / alternatives |
| Lifecycle | pending → signed-off/rejected/superseded; `TD-PENDING:` grep contract | proposed → accepted → superseded |
| Typical content | "CONSERVATION_RTOL_COLD = 1e-3" sign-off | "Sphinx+MyST over MkDocs, because…" |

Most of the 20 existing rows are *sign-offs on numbers* — they would make terrible ADRs (no
alternatives, no consequences; the analysis lives in the source STATUS/report). A handful
(TD-27.1 docs stack, TD-29.1 structure, this task's TD-32.1) are *architecture decisions
wearing a register row* — exactly what ADRs are for. **Recommend: no merge.** The register
stays the single sign-off ledger (the `TD-PENDING:` machinery, same-PR row rule, and
verbatim-tolerance rule are untouched); `adr/` is the home for decisions with architectural
consequences; such decisions get *both* — an ADR with the reasoning and a TD row whose
`Source` column points at the ADR. Rule of thumb for authors: if the decision changes how
future code/docs are structured, write an ADR; if it blesses a number or a deviation, a row
suffices. Retroactive ADR back-fill of TD-27.1/29.x: optional, low value, not recommended.

### 2.5 `docs/development/ideas/`

Sound as specified (idea, motivation, benefits, risks; reviewed/prioritized). Two existing
populations to place:

- **Phase outlines (`development/ideas/P2…P7.md`)** are *not* ideas — they are the accepted
  roadmap, input contract for task 30 (phase-spec authoring), and `development/work/reports/report-0000-overview.md` §5
  points at them. They freeze in the archive; their content graduates directly into `specs/`
  when a phase is specced. Copying them into `ideas/` would create a second source of truth.
- **Open questions parked in the register** (e.g., the old TD-29.6) are the ideas/ natural
  feedstock going forward.

Add a `Status:` header line (proposed / accepted → spec NN / rejected / superseded) so the
folder is reviewable at a glance; `README.md` index with status column; snake_case names,
no numbers (ideas churn; they get a number only on graduating to a spec, from the allocator).

### 2.6 `specs/` + `plans/` — and the existing S01–S14 corpus

**The mapping is nearly 1:1** with the existing triads: SPEC.md (frozen contract: goal,
scope, frozen interfaces, acceptance criteria) → `specs/`; PLAN.md (ordered tasks, mining
instructions, pitfalls) → `plans/`. The owner's plans/ definition — complete-but-minimal,
anti-drift, usable as prompts for mid-tier LLMs — is *verbatim* the discipline
`development/work/plans/README.md` already states ("written for LLM agents weaker than the ones that
built the slice… scope discipline is the main anti-drift device"). Two consequences:

1. **Merge `development/plans/` into `plans/`** (future tasks). A task prompt *is* an
   implementation plan under the new model. The register — the single N-number allocator,
   invariants pointer, execution-order table — becomes `plans/README.md` and keeps its
   allocation rule unchanged (row at assignment, monotonic, no reuse, no backfill).
   The review protocol (`10_REVIEW_PROTOCOL.md`) is not a plan; it moves to `policies/`
   (it is a living protocol other plans' checklists append to).
2. **The triad's third leg (STATUS) has no home in the proposal** — fixed by `records/`
   (§2.8-a). Spec, plan, and record of one work unit share one ID across three folders.

**Do S01–S14 (and tasks 20–31) migrate?** The task-29 census: ~90 inbound references to
`plan/` paths across AGENTS.md/CLAUDE.md/README, PR template, both agent command sets, a
`.claude/settings.json` permission glob (`Edit(development/specs/**)`), `.gitignore`,
prompts 20–25/30 (unexecuted — their literal paths are the contract a weak model follows),
`docs/conf.py`'s header, ~30 historical documents, **and runtime path construction in
committed test code** (`test_order_ode.py`, `test_order_burgers.py` build
`development/work/reports/report-0004-coupling-algebra/artifacts` at runtime). A `git mv` preserves blame but
every *content* citation inside frozen records dangles, and fixing them is forbidden
(no retro-edits). `REFERENCES.lock` `step` fields are bare ids ("S08"), not paths — safe
either way.

**Recommend: freeze in place.** `plan/` becomes a read-only archive: one banner paragraph
prepended to `development/archive/plan_tree_map.md` ("archive as of task 3X; future work lives in
`docs/development/`; paths cited inside are valid relative to this archive"), everything
else byte-identical. Future steps (S15+) and tasks (33+) are born in the new tree. The two
trees never overlap in IDs, so `grep -r S17` finds exactly one home. The one persistent
cost: two lookup roots during P2–P7 (mitigated by the banner and by `development/README.md`
mapping both). The alternative — full migration — is priced in §5 for the owner's
information; it is not recommended.

**Numbering (decision point 9).** Keep the existing series: S-series for architecture
steps, N-series (task numbers) for everything else, allocated by the register. Concretely:
`specs/S15_<snake>.md` + `plans/S15_<snake>.md` + `records/S15_<snake>.md`;
`plans/33_<snake>.md` + `records/33_<snake>_REPORT.md` for tasks (a task usually has no
spec; when it does — a design accepted from `ideas/` — the spec takes the same number).
Multi-file units get a folder of the same name. Per-feature freeform names are rejected:
the ID discipline is what lets records, register rows, branches (`step/S15-…`,
`task/33-…`), and REFERENCES.lock `step` fields join up, and it lets history and future
coexist without a rename wave. "One md per feature aspect" (owner's spec wording) is
compatible: sub-aspects are sections or `S15_<snake>/` sidecar files, not new ID schemes.

### 2.7 `references/` vs `REFERENCES.lock` (and the `local/` collision)

**The lock is load-bearing and stays at the repo root, unchanged.** Append-only, appended at
mining time, schema in header, cited by AGENTS.md, prompts, ~30 files; 51 entries over 41
source ids. Nothing in the new tree replaces it; per-consultation provenance (SHA, paths,
what was taken, which step) is ledger-shaped, not document-shaped.

**`references/` md cards are the human layer above it**: one card per *source* (icon4py,
gt4py, icon-fortran, sympl, tasmania, tutorial PDF, thesis — the §3 corpus of
`development/work/reports/report-0000-overview.md`, ≈8 cards), not per lock entry. Card contents: canonical URL, pinned
version/SHA and where the pin is decided (`constraints/`), license, role in the project,
gotchas (e.g., "gitlab.dwd.de does not resolve; use the gitlab.dkrz.de mirror"), and a
pointer to `REFERENCES.lock` for the consultation ledger. Hand-curated, living; **not**
generated from the lock (41 ids ≠ 8 sources; the mapping is editorial). Ownership rule going
forward: agents append to the lock exactly as today; a card is *updated* only when a pin or
corpus decision changes (trunk-adjacent, like today's pins).

**Naming collision — flag.** A top-level `references/` already exists with exactly the
proposed `local/` semantics: gitignored PDFs + README (`.gitignore` lines 35–36). Recommend
`docs/development/references/local/` absorbs it: move the README, update the two gitignore
lines, and AGENTS.md's "drop local PDFs into `references/`" sentence (trunk edit). PDFs are
untracked — each machine re-drops them once (three files). Keeping both directories is the
one outcome to refuse; if the owner prefers not to touch AGENTS.md yet, the top-level dir
can survive with the dev-tree card folder linking to it — decision point 8. Note
`references/local/` must be excluded from Sphinx *implicitly* by the `development` exclusion
(§2.2) — under option (c) it would need its own pattern.

### 2.8 Gaps in the proposal — homes assigned

- **(a) Historical records** — the proposal's biggest omission. New folder
  `docs/development/records/`: future STATUS files, task execution reports, review reports,
  frozen at merge, never retro-edited (the liveness rule moves into
  `policies/records_and_liveness.md`). Existing records stay in the `plan/` archive.
- **(b) Task prompts** — merged into `plans/` (§2.6); the register survives as
  `plans/README.md`; the review protocol goes to `policies/`.
- **(c) External-facing drafts** (upstream issue texts, PR bodies) — new
  `docs/development/drafts/<theme>/` (`upstream/`, `prs/`). This *resolves TD-29.6* (which
  was parked "until a third external-draft task exists" — the reorganization is the natural
  moment). Wrinkle: unexecuted prompts 23/24 hard-code `reports/upstream|prs` as output
  paths; re-target those two lines when the prompts move into `plans/` (they are unexecuted,
  so editing them is cheap, but it is a trunk call — decision point 10).
- **(d) `TRUNK_DECISIONS.md`** — moves to `docs/development/TRUNK_DECISIONS.md`, top of the
  dev tree next to `adr/` (relationship in §2.4). It is the living register; leaving the
  only living ledger inside a frozen archive would be incoherent. Cost: ~6 living files
  reference `development/REGISTRY.md` (root README, plan/README, prompts README, reports
  README, AGENTS-adjacent wording) — all living, all updatable; frozen citations (report 29,
  TD rows' own Source columns) stay valid via the archive banner.
- **(e) Phase outlines** — stay frozen in the archive (§2.5); future roadmap items are born
  in `ideas/`.
- **(f) `docs/architecture/*`** — **do not move.** The two canonical docs are trunk-frozen,
  published site content (index toctree), and named by the authority-order sentence in
  AGENTS.md, CLAUDE.md, prompts README, the review protocol, package READMEs, tutorials, and
  a dozen frozen records. They are also not "development policy" — they are the product's
  constitution, equally addressed to users (the site's "full design" link). Moving them
  under `development/` would unpublish them (under §2.2-a) and touch every authority
  statement in the repo for zero information gain. They stay at `docs/architecture/`;
  pending TD-29.7 (layout-doc §4 revision) should now be **re-drafted once against the
  final agreed tree** rather than applied twice — first as the task-29 diff, then again
  after this reorganization (decision point 13).

### 2.9 Naming and convention coherence (consolidated)

1. **Folders:** all lowercase (`user/`, `development/`, `policies/`, `adr/`, `ideas/`,
   `specs/`, `plans/`, `records/`, `drafts/`, `references/`). `ADRs/` → `adr/` (§2.4).
2. **IDs:** S-series and N-series continue, one allocator (`plans/README.md` register),
   shared across specs/plans/records/branches/lock `step` fields (§2.6). ADRs use their own
   `NNNN-` sequence (different kind, different lifecycle; no collision since the prefix
   shape differs).
3. **Files:** snake_case throughout, except adr's `NNNN-kebab` if the ecosystem convention
   is kept (decision point 5). Records keep the `_REPORT` suffix for flat execution
   reports vs folder-per-document deliverables — the task-29 rule, unchanged, just re-homed.
4. **Every folder gets a `README.md` index** (existing pattern: prompts, reports).
5. **Greppable markers unchanged:** `TD-PENDING:` (register contract), `GENERATED FILE`
   headers, `[[ref]]` schema. New under this proposal: ideas' `Status:` header line.
6. **Liveness is declared, not implied:** the taxonomy table (today `development/archive/plan_tree_map.md` §1)
   moves to `policies/records_and_liveness.md` and gains rows for the new kinds
   (policy=living, adr=frozen-after-accepted+status-field, idea=living-until-graduated,
   spec/plan=frozen at acceptance/assignment, record=frozen at merge, card=living).

---

## 3. Refined target tree (full; owner's proposal + gap fills)

```
AGENTS.md · CLAUDE.md          root, thinned: authority order + hard rules + pointers to policies/
REFERENCES.lock                root, unchanged (append-only machine ledger)
docs/
├── conf.py                    exclude_patterns += ["development"]        (§4)
├── index.md                   Sphinx master doc — stays at docs/ root
├── architecture/              UNMOVED: canonical pair, trunk-frozen, published (§2.8-f)
├── user/                                                  — PUBLISHED —
│   ├── tutorials/             moved from docs/tutorials/  (+ link fixes, §2.1)
│   ├── api/                   moved from docs/api/
│   ├── glossary.md            moved
│   └── names_registry.md      moved (generated; tools/names_audit.py path updated)
└── development/                                — EXCLUDED FROM BUILD —
    ├── README.md              map of this tree + pointer to the plan/ archive
    ├── TRUNK_DECISIONS.md     living sign-off/decision register (moved; §2.8-d)
    ├── policies/              living rules: naming, records/liveness+templates, docs boundary,
    │                          verification gates+baselines+caches, reference mining,
    │                          agent workflow, review protocol (ex-10_REVIEW_PROTOCOL)
    ├── adr/                   NNNN-<title>.md, Nygard; README index (§2.4)
    ├── ideas/                 <snake>.md with Status: header; README index (§2.5)
    ├── specs/                 future S15+/task specs, ID-named (§2.6)
    ├── plans/                 future plans ≡ agent prompts; README.md = the task-number
    │                          register (single allocator, unchanged rules)
    ├── records/               future STATUS files + execution/review reports (frozen at merge)
    ├── drafts/                external-facing: upstream/, prs/ (resolves TD-29.6)
    └── references/            per-source cards (~8) + local/ (gitignored; absorbs the
                               top-level references/ dir — §2.7)
plan/                          FROZEN ARCHIVE — byte-identical except a banner in development/archive/plan_tree_map.md;
                               all S01–S14 triads, outlines, prompts 10–31, reports stay put
references/                    dissolved into development/references/local/ (decision point 8)
```

## 4. docs/-publication policy (replaces `development/archive/plan_tree_map.md` §4 wording)

1. The published surface is `docs/` **minus `docs/development/`** (conf.py
   `exclude_patterns`; the `-W` build gate applies only to published sources).
2. `docs/development/` is repo-internal process memory: never in a toctree, never linked
   from published pages (prose mentions without links are fine — the existing
   `docs/index.md` "See AGENTS.md and plan/" sentence is the pattern), never deployed.
3. Development content wanted user-facing is *rewritten* under `docs/user/`, never
   included, symlinked, or excerpted mechanically (unchanged rule).
4. Generated files are committed under published `docs/` only with a `GENERATED FILE`
   header naming the regeneration command (unchanged; `names_registry.md` precedent).
5. Publishing `policies/`+`adr/` selectively is explicitly deferred to P7 (§2.2-c).

## 5. Migration-scale assessment (sizing only — the plan comes after the owner agrees)

| Move | Files | Reference blast radius | Verdict |
|---|---|---|---|
| `docs/{tutorials,api,glossary,names_registry}` → `docs/user/` | 21 moved | conf.py (1 pattern), index.md (~8 refs), ~23 in-tutorial links (most survive as same-dir), `tools/names_audit.py` (2 lines), published URLs; CI untouched | do atomically (§2.1) |
| Create `development/` skeleton (README, policies ×~7, adr/README, ideas/README, specs/plans/records/drafts/references READMEs + ~8 cards) | ~20 new | none (new files) | cheap |
| `TRUNK_DECISIONS.md` → `development/` | 1 moved | ~6 living files updated; frozen citations covered by archive banner | acceptable |
| `development/plans/` future merge into `plans/` | register content re-homed; 7 unexecuted prompts either stay archived or move | prompts are frozen-at-assignment: recommend *unexecuted* prompts 20–25/30 move (they are contracts not yet consumed; their internal `reports/…` output paths re-target to `records/`+`drafts/` — ~15 path lines across 7 files) — or stay and execute against the archive; decision point 10 | moderate |
| Top-level `references/` → `development/references/local/` | 1 README + 2 gitignore lines + 1 AGENTS.md sentence | PDFs untracked (re-drop) | cheap |
| AGENTS.md/CLAUDE.md thinning + `.claude`/`.opencode` command+glob updates for S15+ paths | ~6 living files | trunk-owned | required with new tree |
| **NOT moved:** S01–S14 triads (42 files), outlines (6), executed reports, IMPLEMENTATION_REPORT, `docs/architecture/` | 0 | avoids the ~90-reference census incl. runtime test paths | frozen archive (§2.6) |

Rough total: ~25 moved, ~20 created, ~15 living files edited, 0 frozen records touched.

## 6. Register ↔ ADR relationship and the TD-29.1 supersede row

Relationship as decided in §2.4: **two instruments, cross-referenced, no merge** — the
register is the sign-off *ledger* (numbers, tolerances, status lifecycle, `TD-PENDING:`
grep contract); `adr/` is the *reasoning record* for architecture-shaped decisions; an
architecture decision gets both, with the TD row's Source pointing at the ADR.

Draft rows for the migration task to append (owner signs off; dates = merge dates):

| ID | Date | Decision | Status | Source | Evidence |
|---|---|---|---|---|---|
| TD-32.1 | (merge) | Full docs/development reorganization adopted per task-32 evaluation §3 (as amended by the owner's §7 answers): future work under `docs/development/`, `docs/user/` split, `plan/` frozen as archive. **Supersedes TD-29.1** | pending | `…/32_docs_development_structure.md` §3, §7 | — |
| TD-32.2 | (merge) | `docs/development/` excluded from the Sphinx build; publication policy §4; selective publication deferred to P7 | pending | §2.2, §4 | — |
| TD-32.3 | (merge) | Register/ADR relationship: no merge; ledger + `adr/`, cross-referenced | pending | §2.4 | — |

And, on TD-32.1's sign-off: TD-29.1's `Status` cell → `superseded(TD-32.1)` (the register's
update-in-place-Status convention); TD-29.6's → `superseded(TD-32.1)` (drafts/ resolves it);
TD-29.7 stays pending but its diff is re-drafted against the final tree (§2.8-f).

## 7. Decision points for the owner

1. **Location of development memory:** `docs/development/` (grouped under docs, conf.py
   exclusion) vs top-level `development/`. — *Recommend `docs/development/` per your intent;
   the exclusion mechanism is one line and §4 keeps the boundary explicit.*
2. **Publication of `development/`:** fully excluded vs selective (`policies/`+`adr/`) vs
   published. — *Recommend fully excluded now; revisit selective at P7 (protects the `-W`
   gate and the audience split).*
3. **Adopt `docs/user/` nesting:** yes-atomically vs keep tutorials/api at `docs/` root. —
   *Recommend yes, now, while published-URL breakage is free; fix list is §2.1.*
4. **Historical corpus:** freeze `plan/` as a read-only archive (zero moves) vs `git mv`
   history into the new tree. — *Recommend freeze: ~90 inbound references incl. runtime test
   paths and frozen-record citations make migration all cost, no benefit.*
5. **adr conventions:** lowercase `adr/` with Nygard `NNNN-kebab-title.md` vs `ADRs/` /
   snake. — *Recommend `adr/` + `NNNN-kebab`: repo-consistent casing, ecosystem-standard
   files.*
6. **Register vs ADRs:** keep `TRUNK_DECISIONS.md` as the sign-off ledger + `adr/` for
   architecture decisions, cross-referenced vs full merge. — *Recommend no merge; tolerance
   sign-offs are ledger rows, not ADRs (§2.4).*
7. **Prompts ≡ plans:** merge `development/plans/` (future) into `plans/`, register becomes
   `plans/README.md` vs keep a separate prompts tree. — *Recommend merge; the definitions
   are identical and two trees would drift.*
8. **references/ collision:** absorb top-level `references/` into
   `development/references/local/` vs keep both with a pointer. — *Recommend absorb (one
   home); costs 1 README move, 2 gitignore lines, 1 trunk AGENTS.md sentence.*
9. **Future IDs:** continue S-series/N-series with spec/plan/record sharing one ID vs
   per-feature freeform names. — *Recommend continue: joins records, register, branches,
   and REFERENCES.lock `step` fields; lets history and future coexist.*
10. **Unexecuted prompts 20–25/30 and tasks 23/24 output paths:** move into `plans/` with
    output paths re-targeted (`records/`, `drafts/`) vs execute against the archive as
    written. — *Recommend move+re-target at migration; they are unconsumed contracts and
    editing them is a sanctioned trunk call.*
11. **`TRUNK_DECISIONS.md` home:** move to `docs/development/` vs stay in `plan/`. —
    *Recommend move; the living ledger cannot live inside a frozen archive.*
12. **Phase outlines:** stay frozen in the archive, content graduates into `specs/` via
    task 30 vs copy into `ideas/`. — *Recommend stay; copying makes a second source of
    truth for the accepted roadmap.*
13. **`docs/architecture/`:** stays put; TD-29.7's layout-doc revision re-drafted once
    against the final tree vs applied twice. — *Recommend stays + one re-drafted revision
    (§2.8-f); moving it touches every authority-order statement.*
14. **AGENTS.md/CLAUDE.md thinning:** thin to authority order + hard rules + policy
    pointers vs leave as-is with dual sources. — *Recommend thin at migration (trunk edit);
    duplicated living rules are the known drift vector.*

---
*(end of evaluation — migration plan to be commissioned after §7 is answered)*
