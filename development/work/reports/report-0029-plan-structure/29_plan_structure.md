# Task 29 — Plan/memory/documentation structure: analysis and unified-structure proposal

**Branch:** `task/29-plan-structure` · **Deliverable:** this document (analysis + proposal
only — **nothing existing was moved, renamed, or edited**; every change below is *proposed*,
and the execution is specced as a liftable task in §8). · **Date:** 2026-07-12 (analysis of
`main` = `cbbec36`, post task-28 merge).

**Where this document lives, and the bootstrapping irony.** This proposal was commissioned
into `development/work/reports/report-0029-plan-structure/29_plan_structure.md` — a location chosen
*before* the naming convention it proposes existed. Under the convention of §3 (which
blesses the task-27 pattern: a task whose deliverable *is a document* gets a
`reports/NN_<name>/NN_<name>.md` subdirectory; a task whose deliverable is *executed work*
gets a flat `reports/NN_<name>_REPORT.md`), this address is exactly right — but only
because the proposal retroactively legitimizes it. Had the analysis concluded that design
documents belong in a separate `plan/design/` tree, this file would have been born
misfiled under its own rules. The circularity is resolved the only honest way: the
location is ratified here as an instance of the convention, and TD-29.1 asks the trunk to
confirm it.

---

## 0. Executive summary

The repo's memory system is in unusually good shape for something that grew across 14
step implementations and 9 post-slice tasks: authority order is explicit, provenance is
ledgered, records are treated as immutable, and cross-references are dense and mostly
accurate. The five real structural problems, in order of cost:

1. **The sign-off/trunk-decision ledger is buried and unmarked.** The single
   most-load-bearing content (what needs human sign-off; what the trunk decided) lives in
   the frozen `development/work/reports/report-0036-implementation-report.md` §5, in three unmerged TD items inside a
   report subdirectory (`27_docs_plan.md` §3), and in ~25 scattered STATUS flags with **no
   machine-greppable token** — the flags use at least four spellings ("HUMAN SIGN-OFF
   REQUIRED", "flag for human sign-off", "needs trunk", a warning glyph) and "TD-" appears
   nowhere in any STATUS file.
2. **The task-number register is stale and has no allocation rule.** Prompts 26, 27, 29
   were consumed by tasks that have committed outputs but no committed prompt file; the
   `development/work/plans/README.md` execution-order table lists only 20–25 and 30. Numbering
   collisions between concurrent task assignments are currently prevented by nothing.
3. **`development/records/` mixes three kinds** — task execution reports (26, 28), a
   design document (27), and (once tasks 23/24 run) external-facing drafts
   (`upstream/`, `prs/`) — with no index saying which is which, and two naming patterns
   (`NN_name_REPORT.md` flat vs `NN_name/` subdir) with no stated rule.
4. **STATUS.md structure drifted heavily** (evidence in §2.3): frontmatter regressed to
   nothing by S14, a numbered-outline style appears at S11, the same concept has up to
   ~8 heading spellings, and 6 of 14 SPECs silently omit "Frozen interfaces" so absence
   is ambiguous between "none" and "forgot".
5. **The public face is stale or diverged:** the root `README.md` still says
   "pre-implementation… no framework code exists yet" (the slice is merged); the layout
   doc calls the architecture doc "v1.2" (it is v1.3), omits itself from its own `docs/`
   tree, and its §4 `docs/` description diverges from the post-task-28 reality in ten
   enumerable ways (§6).

**The proposal moves nothing.** Every existing path stays (§4). The fix is: three new
files (`development/archive/plan_tree_map.md`, `development/REGISTRY.md`, `development/work/reports/README.md`),
two content refreshes of *living* documents (root `README.md`, the register table in
`development/work/plans/README.md`), one canonical sign-off marker convention going forward, and
one trunk-owned layout-doc revision (drafted as a diff in §6.3, not applied). Rationale:
the cross-reference census (§4.3) found ~90 inbound references to plan paths across
prompts, agent tooling, CI-adjacent files, *executed* task records, and — critically —
**hard-coded paths in committed test code** (`test_order_ode.py`,
`test_order_burgers.py` construct `development/work/reports/report-0004-coupling-algebra/artifacts` at
runtime). Any move therefore either breaks the weak-model prompt workflow, edits
historical records (forbidden), or touches test code for zero functional gain. A
beautiful greenfield tree loses to registers and indexes here.

---

## 1. Inventory

Every memory/planning/documentation file, grouped; line counts from the working tree.

### 1.1 Root

| Path | Lines | Kind (§2) | State |
|---|---|---|---|
| `README.md` | 47 | external-facing entry point | **STALE** — "Status: pre-implementation… No framework code exists yet"; Contents table predates prompts/, reports/, docs site |
| `AGENTS.md` | ~50 | working agreement (canonical) | current; authority order, hard rules, workflow |
| `CLAUDE.md` | ~15 | working-agreement shim (imports AGENTS.md) | current |
| `REFERENCES.lock` | 472 | provenance ledger (append-only, TOML-ish `[[ref]]` schema in header) | current; append-at-mining-time discipline held |

### 1.2 `plan/` root

| Path | Lines | Kind | State |
|---|---|---|---|
| `development/work/reports/report-0000-overview.md` | 69 | plan overview: agent contract, DAG, lanes, reference corpus, phases | current; §5 points at `outlines/` |
| `development/work/reports/report-0036-implementation-report.md` | 206 | process record of the S01–S14 slice; §2 merge ledger, §4 findings, **§5 human sign-off ledger**, §6 standing follow-ups | frozen historical record *containing living content* (§5, §6) — the central misfit (M2) |

### 1.3 `development/{specs,plans,records}/` — 14 triads

All 14 steps have exactly `SPEC.md` + `PLAN.md` + `STATUS.md`. S04 additionally has an
on-disk `artifacts/` (2 PNGs) which is **gitignored and untracked**
(`.gitignore:32 development/records/*/artifacts/`) — generated locally by
`test_order_ode.py`/`test_order_burgers.py`; the STATUS "Artifacts" sections describe
them but git carries none.

| File class | Template | Drift |
|---|---|---|
| `PLAN.md` (×14) | uniform: single `# Sxx — Plan` heading, no `##` sections; 6–11 lines | none |
| `SPEC.md` (×14) | common core: Goal · In scope · Acceptance criteria; 15–31 lines | "Frozen interfaces" present in 9 (S01–S07, S11), **absent in 6** (S08–S10, S12–S14); "Out of scope" only S01–S03 |
| `STATUS.md` (×14) | none stable; 79 → 330 lines over the series | heavy — §2.3 |

### 1.4 `development/ideas/` — 6 files

`P2_distributed.md` … `P7_presets_docs_anemoi.md`, each exactly 3 lines on a shared
micro-template: `# PX — Title (outline)` · `**After:** <dep>` · one dense prose paragraph
of `(a)…(b)…` sub-steps. Zero references to `docs/`, CONTRIBUTING, or CHANGELOG. They are
the input contract for prompt 30 (phase-spec authoring); phase steps, when specced,
continue the S-series under `development/{specs,plans,records}/`.

### 1.5 `development/plans/` — register + protocol + 8 task prompts

| Path | Lines | Notes |
|---|---|---|
| `README.md` | 115 | the *register*: how-to, execution-order table (**lists only 20–25, 30**), invariants, verification-gate baselines (kept current through task 26/28 merges), caches |
| `10_REVIEW_PROTOCOL.md` | 91 | reusable reviewer protocol; the template other prompts' "Review checklist" sections append to |
| `20_gpu_validation.md` | 93 | unexecuted; output → `reports/20_gpu_validation_REPORT.md` |
| `21_ci_hardening.md` | 145 | unexecuted; output → `reports/21_ci_hardening_REPORT.md` |
| `22_plan_hash_config_digest.md` | 134 | unexecuted; output → `reports/22_plan_hash_REPORT.md` |
| `23_upstream_reports.md` | 90 | unexecuted; output → `reports/upstream/` (3 named drafts) |
| `24_pr_publication.md` | 69 | unexecuted; output → `reports/prs/` (`SXX_pr_body.md`, `INDEX.md`, `publish.sh`) |
| `25_cf_multistage_t1.md` | 113 | unexecuted; output → `reports/25_cf_multistage_REPORT.md` |
| `28_docs_implementation.md` | 217 | **executed**; lifted from 27 §5 |
| `30_author_phase_specs.md` | 103 | unexecuted; output → `reports/30_specs_<phase>_REPORT.md` |

Common prompt template (the "register format"): title `# Task NN — …` · `**Branch:**
task/NN-…` line · `## Hard rules (restated; full list in development/work/plans/README.md)` ·
body (`## Item A…F` or `## Procedure`/`## Design`) · `## Acceptance criteria` ·
`## Verification gates` · `## Review checklist (appended to 10_REVIEW_PROTOCOL.md for
this task)`. Deviations: 24 adds "What NOT to do"; 25 adds "History"/"Stop rules".

**Numbers 26, 27, 29 have no prompt file** yet each has (or is) a committed output:
`reports/26_gridgen_integration_REPORT.md`, `reports/27_docs_plan/`, this document.
Those tasks were evidently assigned by ad-hoc prompt text never committed to the repo.

### 1.6 `development/records/`

| Path | Lines | Kind |
|---|---|---|
| `26_gridgen_integration_REPORT.md` | 73 | task execution report (flat, `_REPORT` suffix) |
| `27_docs_plan/27_docs_plan.md` | 742 | **design document** (stack evaluation, TD-1/2/3, docstring policy, liftable task 28 spec) — subdir, no suffix |
| `28_docs_implementation_REPORT.md` | 295 | task execution report (flat) |
| `upstream/`, `prs/` | — | **do not exist yet**; targets of unexecuted tasks 23/24 |

### 1.7 `docs/`

| Path | Kind | Notes |
|---|---|---|
| `architecture/symcon_architecture.md` | canonical architecture (trunk-owned, edit-forbidden) | v1.3; since task 28 *also* a Sphinx source, read-only |
| `architecture/symcon_repo_layout.md` | canonical layout companion | calls the architecture doc "v1.2" (L283); omits itself from its own §4 `docs/` tree; §4 diverged from reality (§6) |
| `conf.py` | Sphinx config (task 28) | header cites `development/work/reports/report-0027-docs-plan/27_docs_plan.md §3`; `exclude_patterns = ["_build", "api/README.md"]` |
| `index.md`, `glossary.md` | hand-written site pages (MyST) | index L51 mentions `plan/` as prose only — no link into plan/ from the published site |
| `tutorials/` (index + T0/T1/T2) | hand-written tutorial track | link `../architecture/symcon_architecture.md` (relative, inside docs/) |
| `names_registry.md` | **generated, committed** (`GENERATED FILE — do not edit… tools/names_audit.py`) | a committed generated artifact in the docs tree — layout doc silent (M10) |
| `api/` (index + 13 module stubs + README) | hand-curated MyST stubs wrapping `automodule`; prose is autodoc-pulled at build | `api/README.md` says "built, not committed" of the *HTML*, is excluded from the build (M11) |
| `_build/` | build output | gitignored (task 28), never committed |

### 1.8 Agent tooling and CI-adjacent

`.claude/commands/{implement-step,review-step}.md` + `.claude/settings.json`
(permission glob `Edit(development/specs/**)`); mirrored `.opencode/command/*` +
`opencode.json`; `.github/PULL_REQUEST_TEMPLATE.md` (**step-shaped only**: header
`development/specs/____ — one step per PR`); `.github/workflows/{docs,lint,test-cpu,test-gpu,test-mpi}.yml`
— note `nightly.yml` is promised by layout §4 and does not exist; `docs.yml` exists and
is not in layout §4. No workflow references any plan path.

---

## 2. Taxonomy

### 2.1 Kinds

| # | Kind | Liveness | Instances |
|---|---|---|---|
| K1 | Canonical architecture | trunk-edited only | `docs/architecture/*.md` (2) |
| K2 | Working agreement | living, trunk-gated | `AGENTS.md`, `CLAUDE.md` |
| K3 | Provenance ledger | append-only | `development/references/lock.toml` |
| K4 | Plan overview / register | living | `development/work/reports/report-0000-overview.md`, `development/work/plans/README.md` |
| K5 | Step contract (SPEC) | frozen at step start | `development/specs/SXX_*.md` (14) |
| K6 | Step how-to (PLAN) | frozen at step start | `development/plans/SXX_*.md` (14) |
| K7 | Step record (STATUS) | frozen at merge (historical) | `development/records/SXX_*/STATUS.md` (14) |
| K8 | Phase outline | frozen until specced | `development/ideas/P*.md` (6) |
| K9 | Review protocol | living, versioned by task checklists | `development/policies/review_protocol.md` |
| K10 | Task prompt | frozen at assignment | `development/plans/2x/30_*.md` (8) |
| K11 | Task execution report | frozen at task merge | `reports/26_*_REPORT.md`, `28_*_REPORT.md` |
| K12 | Design document / proposal | frozen; decisions extracted to register | `reports/27_docs_plan/`, this file |
| K13 | External-facing draft | frozen after human publishes | future `reports/upstream/`, `reports/prs/` |
| K14 | Process report (slice-level) | frozen | `development/work/reports/report-0036-implementation-report.md` |
| K15 | Generated artifact | regenerate, never hand-edit | `docs/names_registry.md` (committed); `docs/_build/`, `development/records/*/artifacts/` (untracked) |
| K16 | Published site source | living | `docs/{conf.py,index.md,glossary.md,tutorials/,api/}` |
| K17 | Agent tooling / CI templates | living | `.claude/`, `.opencode/`, `.github/PULL_REQUEST_TEMPLATE.md` |
| — | **Missing kind: living decision register** | living, append-mostly | **none — the gap §5 fills** |

### 2.2 Misfits (evidence-backed)

- **M1** `27_docs_plan.md` is a K12 design document living under `reports/` among K11
  execution reports, in the only subdirectory, with no suffix — three simultaneous
  deviations from its siblings. (Resolution: bless, don't move — §3.)
- **M2** `development/work/reports/report-0036-implementation-report.md` is a frozen K14 record whose §5 (sign-off
  ledger) and §6 (standing follow-ups) are *living* content: prompts 20/24/30 point
  agents at §5/§4–6 as current state, but the file can never be updated without editing
  a historical record. Liveness mixing, not location, is the defect.
- **M3** Tasks 23/24 route K13 external-facing drafts (upstream issue text, PR bodies,
  `publish.sh`) into the process-memory `reports/` tree, unnumbered and thematic
  (`upstream/`, `prs/`) — a third naming pattern and an audience mismatch (these files
  are written *to be pasted outside the repo*).
- **M4** Register staleness: prompts/README's table lacks rows for 26–29; numbers were
  consumed invisibly; no allocation or collision rule exists anywhere.
- **M5** STATUS drift — §2.3.
- **M6** SPEC "Frozen interfaces" absent in S08–S10/S12–S14: the section that AGENTS.md
  calls load-bearing for concurrent lanes is sometimes just missing, so absence cannot
  be read as "this step freezes nothing".
- **M7** Root README stale (pre-implementation claim; Contents table missing
  `development/plans/`, `development/work/reports/report-0036-implementation-report.md`, the docs site).
- **M8** PR template hard-codes the step shape; tasks 20–30 also land by PR and get a
  template whose first line is wrong for them.
- **M9** Layout doc: "v1.2" mislabel (L283), self-omission from §4, §4 `docs/` and
  workflows divergence (§6).
- **M10** `docs/names_registry.md` is a committed generated file; the layout doc's own
  convention ("plan artifacts are cache, not source") has no carve-out for it.
- **M11** `docs/api/README.md` describes the directory as "built, not committed" while
  its 14 sibling `.md` stubs are committed hand-curated sources; the file is excluded
  from the Sphinx build to paper over the wording.

### 2.3 STATUS structural drift (early vs late)

Comparing S01–S03 against S12–S14 (full heading census in the underlying inventory):

| Axis | Early (S01–S03) | Late (S12–S14) |
|---|---|---|
| Frontmatter | `**Branch:** … · **Date:** … · **State:** ready for PR` | S12/S13 drop Date, State becomes a cross-ref; **S14 has no frontmatter at all** |
| Outline style | bare `## Name` | numbered `## N. Name` from S11 onward |
| Section order | Built → Gates → Deviations → Follow-ups → Artifacts | S12 puts Deviations before Acceptance; S13 leads with a Tolerances section; Gates drift to the end |
| Vocabulary | "Gate results (local)" | ~6 spellings of the gate section, ~4 of Acceptance, **~8 of Deviations** ("Deviations", "Interpretations & deviations", "Deviations (and why)", "Deviations & decisions (none silently resolved)", "Deviations / disagreements", "Deviations / disagreements / findings", "Deviations and interpretations (with rationale)", "Deviations / decisions / findings") |
| New late-only sections | — | dedicated sign-off/tolerance sections (S10, S13 §2); benchmark-artifact section (S14 §4); ALL-CAPS dossier/root-cause verdicts (S12, S13 §5) |
| Sign-off marking | none needed | flags from S05 on, in ≥4 spellings, **no greppable token**; one flag even self-RESOLVES in prose (S13 L324) |
| Length | 79–196 | 220–330 |

Verdict: the drift is *organic enrichment*, not decay — late STATUS files are better
documents. But (a) the sign-off flags are unfindable mechanically, and (b) the next
14 steps (P2+) will re-drift from scratch unless the enriched shape is written down.
Existing STATUS files are historical records: **no retro-normalization**; the fix is a
forward template (§3.3) and the register (§5.1).

---

## 3. Naming conventions

### 3.1 Current schemes (observed)

| Series | Scheme | Examples | Gaps/quirks |
|---|---|---|---|
| Steps | `SXX_<snake>` dirs; fixed triad filenames | `S01_repo_scaffold` … `S14_plan_through_dycore` | none; two-digit, zero-padded |
| Phases | `PN_<snake>.md` | `P2_distributed` … `P7` | P1 implicitly = the slice; never named |
| Prompts | `NN_<snake>.md`, tens-banded | `10_REVIEW_PROTOCOL` (protocol), `20`–`25`, `28`, `30` | 26/27/29 consumed without files; 10-band vs 20+-band unstated |
| Reports | `NN_<snake>_REPORT.md` flat | 26, 28 | vs `report-0027-docs-plan/27_docs_plan.md` (subdir, no suffix) vs future `upstream/`, `prs/` (thematic, unnumbered) |
| Plan root | `00_`-prefixed overview | `00_OVERVIEW.md` | `IMPLEMENTATION_REPORT.md` unprefixed |

### 3.2 Proposed single convention

One integer namespace for *post-slice work units* (the "N-series"), two letter-prefixed
namespaces for *plan units* (S-series steps, P-series phases), fixed filenames inside
step folders. Concretely:

1. **S-series** (implementation steps): `development/{specs,plans,records}/SXX_<snake>` with `SPEC.md`,
   `PLAN.md`, `STATUS.md`, optional untracked `artifacts/`. Phase steps continue the
   series (S15+…) as prompt 30 already specifies. Zero-padded two digits until S99.
2. **P-series** (phase outlines): `development/ideas/PN_<snake>.md`. Retired when the phase
   is specced into steps (file stays as record).
3. **N-series** (tasks): two-digit, strictly monotonic, **never reused, gaps never
   backfilled**. Bands: `0x` = plan-root ordering prefixes (only `00_OVERVIEW`),
   `10–19` = protocols (only `10_REVIEW_PROTOCOL`), `20+` = tasks.
   - Prompt file: `development/plans/NN_<snake>.md`. **Allocation rule (new):** the number is
     allocated by adding a row to the prompts/README register table *at assignment*,
     even when the prompt text is delivered ad hoc and never committed — the row then
     reads "prompt: ad hoc (not committed)". This retroactively regularizes 26/27/29 and
     is the collision rule: the register is the single allocator; first row wins; a
     colliding latecomer takes the next free number.
   - Execution report: `development/records/NN_<snake>_REPORT.md` (flat, suffixed).
   - Document-deliverable (design doc/proposal, or any multi-file deliverable):
     `development/records/NN_<snake>/NN_<snake>.md` (+ sidecars). This blesses the
     task-27 pattern; task 29 (this file) conforms.
   - External-facing drafts: thematic subdirs under `reports/` as their prompt names
     them (`upstream/`, `prs/`) — kept, because tasks 23/24 hard-code these paths and
     are unexecuted; indexed and kind-labelled by `reports/README.md` (§5.1). Whether
     *future* external drafts get a `plan/drafts/` home is TD-29.6.
4. **Forward STATUS/SPEC templates** (next steps only, no retro-edits): §3.3.
5. **Canonical sign-off marker** (new, forward): any line in any STATUS/report that
   requires trunk/human action carries the literal token `TD-PENDING:` and is mirrored
   as a row in `development/REGISTRY.md` within the same PR. `grep -rn "TD-PENDING"`
   must return only lines whose register row is still open.

### 3.3 Forward templates (to be appended to prompts/README by the migration task)

- **SPEC**: Goal · In scope · Out of scope (may be "nothing excluded") · **Frozen
  interfaces (mandatory; write "none" explicitly)** · Acceptance criteria. Absence of a
  frozen-interface section is thereby made impossible to misread (fixes M6 forward).
- **STATUS**: header `**Branch:** · **Date:** · **State:**` · `## 1. What was built` ·
  `## 2. Acceptance criteria → tests` · `## 3. Deviations` (one heading spelling,
  subsume disagreements/findings as list prefixes) · `## 4. Tolerances & sign-off flags`
  (each flag on a `TD-PENDING:` line) · `## 5. Gates (dated)` · `## 6. Follow-ups` ·
  `## 7. Artifacts` · `## 8. Review fixes (round N)`. This is the S11–S14 enriched shape,
  named once. **Artifact-reference rule:** `development/records/*/artifacts/` is gitignored, so a
  STATUS "Artifacts" entry that names a path is dangling on a fresh clone (S04's two
  convergence PNGs are the existing case — they survive only because the generating
  tests are committed). Rule: every untracked artifact is cited *with its regeneration
  command* (e.g. `uv run pytest packages/symcon-core/tests/test_order_ode.py`), never as
  a bare path.

---

## 4. Unified target tree and migration table

### 4.1 Target tree (NEW = created by the migration task; everything else byte-identical)

```
symcon/
├── README.md                                  REFRESH (content edit; living file)
├── AGENTS.md  CLAUDE.md  development/references/lock.toml      stays (byte-identical)
├── plan/
│   ├── README.md                              NEW — taxonomy map (§2.1), naming rules (§3.2),
│   │                                          forward templates (§3.3), plan/<->docs/ boundary policy (§5.2)
│   ├── TRUNK_DECISIONS.md                     NEW — the living decision/sign-off register (§5.1)
│   ├── 00_OVERVIEW.md                         stays
│   ├── IMPLEMENTATION_REPORT.md               stays, frozen (TRUNK_DECISIONS supersedes its §5/§6 going forward)
│   ├── steps/S01…S14/{SPEC,PLAN,STATUS}.md    stays (all 42 files byte-identical)
│   ├── outlines/P2…P7.md                      stays (6 files)
│   └── prompts/
│       ├── README.md                          REFRESH (register rows 26–31 + allocation rule + §3.3 templates)
│       ├── 10_REVIEW_PROTOCOL.md              stays
│       ├── 20…25, 28, 30_*.md                 stays (8 files, incl. unexecuted)
│       └── reports/
│           ├── README.md                      NEW — index: kind (K11/K12/K13) per entry, naming rule
│           ├── 26_gridgen_integration_REPORT.md   stays
│           ├── 27_docs_plan/27_docs_plan.md       stays (pattern blessed, not moved)
│           ├── 28_docs_implementation_REPORT.md   stays
│           ├── 29_plan_structure/29_plan_structure.md   (this file)
│           └── upstream/  prs/                created by tasks 23/24 when executed (unchanged targets)
├── docs/                                      stays entirely (trunk-owned layout revision drafted in §6.3, human-applied)
└── .github/, .claude/, .opencode/             stays (PR-template generalization = TD-29.5, one-line, trunk)
```

### 4.2 Migration table

| Existing path | Target | Action |
|---|---|---|
| `README.md` | same | content refresh (status paragraph + Contents rows for `development/plans/`, `development/work/reports/report-0036-implementation-report.md`, `development/REGISTRY.md`, docs site) |
| `AGENTS.md`, `CLAUDE.md`, `development/references/lock.toml` | same | none |
| `development/work/reports/report-0000-overview.md` | same | none |
| `development/work/reports/report-0036-implementation-report.md` | same | none (stays frozen; superseded-by relationship declared *in* TRUNK_DECISIONS, not by editing the report) |
| `development/{specs,plans,records}/**` (42 files) | same | none — zero content edits, zero moves |
| `development/ideas/**` (6 files) | same | none |
| `development/work/plans/README.md` | same | content refresh (register + rules + templates) |
| `development/plans/10,20–25,28,30_*.md` | same | none (executed AND unexecuted prompts untouched) |
| `development/records/26,28_*_REPORT.md` | same | none |
| `development/work/reports/report-0027-docs-plan/` | same | none |
| `docs/**` (all) | same | none by the agent task; layout-doc diff (§6.3) is trunk/human |
| `.github/`, `.claude/`, `.opencode/` | same | none by the agent task; PR template = TD-29.5 |
| — | `development/archive/plan_tree_map.md` | NEW |
| — | `development/REGISTRY.md` | NEW |
| — | `development/work/reports/README.md` | NEW |

Zero `git mv`. Zero edits to K1/K5/K6/K7/K10/K11/K12/K14 files. The only edited files
are living documents (K2-adjacent README, K4 register), which is what "minimize churn,
fix the real inconsistencies" buys: link breakage risk is structurally zero.

### 4.3 Cross-reference census (what pins the tree in place)

Full inbound-reference map to plan paths (grep across the repo including `.github/`,
`docs/conf.py`, agent tooling; `docs/_build` and caches excluded). Since the proposal
moves nothing, **no link updates are required**; the census is recorded so any future
move can price itself.

| Target | Referenced by (file: approx. lines) |
|---|---|
| `development/{specs,plans,records}/**` | `AGENTS.md` (10, 23, 44), `CLAUDE.md` (9), `README.md` (21), `.github/PULL_REQUEST_TEMPLATE.md` (3), `.claude/commands/implement-step.md` (3, 12), `.claude/settings.json` (29: permission glob `Edit(development/specs/**)`), `.opencode/command/implement-step.md` (6, 15), `development/work/plans/README.md` (44), `10_REVIEW_PROTOCOL.md` (27), prompts 20 (31–34), 21 (9), 23 (23, 38–39), 25 (27), 30 (19–20, 31, 54, 81), `IMPLEMENTATION_REPORT.md` (11), **test code:** `packages/symcon-core/tests/test_order_burgers.py` (87), `test_order_ode.py` (9, 101) — runtime `parents[3]/"development/work/reports/report-0004-coupling-algebra/artifacts"`; **benchmarks:** `benchmarks/dispatch_overhead/jw_step.py` (4), `benchmarks/s05_dispatch.py` (4); `.gitignore` (32) |
| `development/work/reports/report-0000-overview.md` | `AGENTS.md` (10, 45), `README.md` (20, 41), `development/work/plans/README.md` (114), prompt 30 (18, 79–80), 27 report (330) |
| `development/work/reports/report-0036-implementation-report.md` | `development/work/plans/README.md` (112), prompts 20 (14), 24 (11, 19), 30 (23, 58), 27 report (84, 103, 121, 130) |
| `development/ideas/` | `README.md` (22), `development/work/plans/README.md` (115), prompt 30 (15), 27 report (604) |
| `development/work/plans/README.md` | `10_REVIEW_PROTOCOL.md` (32), prompts 20–22, 25, 28, 30 ("Hard rules" headers), 27 report (394), 28 report (293) |
| `development/records/**` | `docs/conf.py` (1–2: `27_docs_plan.md §3`), prompts 20 (57), 21 (127), 22 (107), 23 (5, 70, 75, 86 → `upstream/`), 24 (21, 33, 42, 54, 58 → `prs/`), 25 (95), 28 (1, 10, 195), 30 (83), 27 report (self, 391, 576) |
| `docs/architecture/*` | `AGENTS.md` (4, 35), `README.md` (18–19), `development/work/plans/README.md` (34, 44), `10_REVIEW_PROTOCOL.md` (27), prompt 30 (17), `packages/symcon-core/README.md` (3), `packages/symcon-icon/README.md` (3), `docs/index.md` (47–48), `docs/tutorials/00_*` (47), `01_*` (74), 27 report (18, 281), 28 report (33), layout doc self-ref (283, mislabelled "v1.2") |
| `development/references/lock.toml` | ~30 files: AGENTS/CLAUDE/README, PR template, both command sets, prompts README + most prompts, most STATUS files, `constraints/cpu-ci.txt` (1), and provenance comments across `packages/**` source and tests, `validation/L4_idealized/*` |

False-positive guard for any future migration grep: `plan/` also names the **source
module** `symcon/core/plan/` (`plan/bind.py`, `plan/ops.py`, `plan/native/templates/`)
in `docs/architecture/symcon_repo_layout.md` (104, 150, 156, 300, 303) and
`development/work/proposals/proposal-0037-p2-distributed.md` (3) — never rewrite those.

Priced-out alternatives this census kills:

| Rejected move | Would touch |
|---|---|
| `development/records/` → `plan/reports/` | ~15 references in ~10 files, incl. 5 *unexecuted* prompts (their literal output paths are the contract a weak model follows), 2 *executed* records, and `docs/conf.py` |
| `27_docs_plan/` → `plan/design/` | `docs/conf.py` header + executed prompt 28 (1, 10) + self-refs — edits to two frozen records |
| `IMPLEMENTATION_REPORT.md` → `plan/reports/` | 10 references in 5 files incl. 3 unexecuted prompts |
| any `development/{specs,plans,records}/` reshaping | test code at runtime, permission glob, both agent command sets, PR template |

---

## 5. Missing files: verdicts

| Candidate | Verdict | Rationale |
|---|---|---|
| **`development/REGISTRY.md`** | **Needed NOW** | The single most-referenced-hardest-to-find content. Today it is: `IMPLEMENTATION_REPORT.md` §5 (7 rows, frozen), 27 §3 TD-1/2/3 (signed off implicitly by task 28's execution — nowhere recorded), and ~25 STATUS flags across S05–S13 with no common token (S05:104 "HUMAN SIGN-OFF REQUIRED (PR)…", S08:137 "…CONSERVATION_RTOL_COLD = 1e-3…", S10:109 heading "Tolerance note (flag for human sign-off)", S13:109 "JW initializer signature CHANGE (frozen interface — needs trunk…", S13:324 a flag *self-resolving in prose*). Format in §5.1. |
| Decision-record convention (ADR) | **Needed now, as register rows — not an ADR directory** | The 27 pattern (full analysis in a K12 document, decision extracted to a register row with a link) already works and produced better artifacts than one-page ADRs would. A `plan/adr/` tree would add a fourth document kind for zero information. Revisit only if P7's release process wants published decision history. |
| **`CONTRIBUTING.md`** | **Needed LATER — at task 24 (publication)** | Today every contributor is an agent bound by AGENTS.md + prompts/README; a third entry point would drift. The moment the repo is pushed and PRs invite humans (task 24), add a *thin* CONTRIBUTING.md that points at AGENTS.md, the gate table, and the PR template — one screen, no duplicated rules. Add as an item to task 24's scope at execution (its prompt is unexecuted; scope addition is a trunk call, TD-29.4). |
| CHANGELOG / policy | **Not needed now; policy decision now, file at P7** | Nothing is released; versioning + release automation are explicitly P7-scoped (`development/ideas/P7`). Record the policy as a TRUNK_DECISIONS row ("no CHANGELOG until P7 versioning step; then Keep-a-Changelog or towncrier decided with the release tooling") so the question stops being re-asked. |
| **`plan/` ↔ `docs/` boundary policy** | **Needed NOW** (a section in the new `development/archive/plan_tree_map.md`, §5.2) | Task 28 made the boundary real: the Sphinx site publishes `docs/` only, and today the only plan-mention in the site is prose (`docs/index.md` L51, no link). Unwritten, the next tutorial author will hyperlink `development/work/reports/report-0036-implementation-report.md` (T2/T4/T6/T7 in 27 §1.2 all cite it as *source material*) and either 404 the published site or drag process memory into it. |
| `docs/coupling.md`, `docs/porting_guide.md` | **Needed later — P7-owned; do not create** | Promised by layout §4; 27 §6 already fences both to P7 ("the nav gets no placeholder that would imply a promise"). Noted here; no action. |
| `development/archive/plan_tree_map.md` | **Needed NOW** | The taxonomy/naming/boundary content of this proposal needs a durable, discoverable home; `00_OVERVIEW.md` is the *slice plan* and prompts/README is the *task register* — neither should absorb repo-memory policy. |
| `development/work/reports/README.md` | **Needed NOW** | Three kinds (K11/K12/K13) and three naming patterns coexist in one directory; a 20-line index labelling each entry ends M1/M3 without moving anything. |
| Others considered | not needed | `MAINTAINERS`/CODEOWNERS (single-owner repo), `SECURITY.md` (pre-publication), a plan glossary (docs/glossary.md exists and is user-facing; AGENTS.md defines the process terms). |

### 5.1 `development/REGISTRY.md` — specified format

Append-mostly table + one rule paragraph. Columns:
`ID` (`TD-NN.k`, NN = originating task/step number, k = ordinal) · `Date` · `Decision`
(one sentence, verbatim tolerances) · `Status` (`pending` / `signed-off` / `rejected` /
`superseded(TD-…)`) · `Source` (file §/line of the full analysis) · `Evidence`
(commit/PR of the sign-off).
Seed content, copied *verbatim* from sources (no paraphrase — tolerances are contracts):
the 7 rows of `IMPLEMENTATION_REPORT.md` §5 (S05, S08, S09, S10, S12, S13 ×2, S14);
TD-1/TD-2/TD-3 from 27 §3 (status: signed-off — task 28 executed them; evidence: merge
`cbbec36`); the CHANGELOG-deferral row (above); the TD-29.x rows of §7. Forward rule:
every new `TD-PENDING:` line in a STATUS/report lands here in the same PR.

### 5.2 Boundary policy (to live in `development/archive/plan_tree_map.md`)

1. `plan/` is repo-internal process memory. It is never a Sphinx source, never linked
   from `docs/` site pages (prose mentions without links allowed), never deployed.
2. `docs/` is the published surface. Its only trunk-frozen zone is `architecture/`;
   everything else is living K16.
3. Plan content wanted user-facing is *rewritten* under `docs/` (as task 28's tutorials
   did with IMPLEMENTATION_REPORT findings — cited as source material, no links), never
   included or symlinked. P7's "architecture canonicalization" owns any future exception.
4. Generated files: committed under `docs/` only with a `GENERATED FILE` header naming
   the regeneration command (the `names_registry.md` precedent, to be ratified in the
   layout doc — §6.3).

---

## 6. Task-28 conflict analysis: layout doc §4 vs the actual `docs/` tree

### 6.1 Divergence enumeration

Layout §4 promises: `architecture/symcon_architecture.md` ("the v1.2 document,
canonical"), `coupling.md`, `porting_guide.md`, `api/` ("sphinx + autodoc from py.typed
sources"); workflows `lint / test-cpu / test-mpi / test-gpu / nightly`.

| # | Divergence | Introduced by | Covered by 27 §3.2 TD-1 additive clarification? | Needs trunk layout-doc action? |
|---|---|---|---|---|
| D1 | `docs/conf.py` exists (Sphinx+MyST+Napoleon+furo) | task 28 | **Yes** (named explicitly) | folded into D-diff |
| D2 | `docs/index.md` + hand-written MyST pages | task 28 | **Yes** (named) | folded |
| D3 | `docs/tutorials/` (T0–T2 + index) | task 28 | **Yes** (named) | folded |
| D4 | Google-docstring/Napoleon note | task 28 (TD-3) | **Yes** (named) | folded |
| D5 | `docs/glossary.md` | task 28 | **No** — TD-1 doesn't name it | yes (one tree line) |
| D6 | `docs/names_registry.md`: committed *generated* file; tension with "artifacts are cache, not source" (§5 conventions) | task 26/28 lineage | **No** | yes — needs an explicit generated-file carve-out |
| D7 | `api/` reality: hand-curated committed MyST stubs invoking autodoc; rendered HTML gitignored; `api/README.md` excluded from build with self-contradictory wording (M11) | task 28 | **Partly** — TD-1 argues the line "is satisfied as written"; the *stub-vs-built* nuance and the README exclusion are not stated | yes (reword the `api/` comment) |
| D8 | Architecture docs now double as read-only Sphinx sources | task 28 | **No** (implied, not stated) | yes (one annotation) |
| D9 | `.github/workflows/docs.yml` exists, absent from §4's workflow list | task 28 | **No** | yes (one line) |
| D10 | `docs/_build/` gitignored build output | task 28 | **No** | optional (covered by D7's "built, not committed") |
| D11 | Architecture doc mislabelled "the v1.2 document" (actual: v1.3) | pre-existing (bootstrap) | No | yes (one word) |
| D12 | Layout doc omits `symcon_repo_layout.md` from its own `docs/` tree | pre-existing | No | yes (one line) |
| D13 | `nightly.yml` promised, never built | pre-existing gap (not 28) | No | no doc action — an implementation follow-up; record as TRUNK_DECISIONS row or P2+ item |
| D14 | `coupling.md` / `porting_guide.md` promised, absent | pre-existing; P7-owned | n/a — 27 §6 fences them | no — keep the lines (they are the promise) |

Count: **10 divergences attributable to task 28 (D1–D10)**, of which TD-1's additive
clarification covers four fully (D1–D4) and one partly (D7); **six need a
trunk-acknowledged layout-doc revision** (D5–D9 + the D7 remainder), plus two
pre-existing errata (D11, D12) best fixed in the same trunk edit.

### 6.2 Judgment

None of D1–D10 is a *violation* — task 28 stayed inside TD-1's "comply via MyST"
reading and never edited the layout doc. The layout doc is simply one revision behind
its own repo, and AGENTS.md forbids everyone but the trunk from fixing that. The
following diff is therefore **drafted, not applied**.

### 6.3 Proposed layout-doc revision (trunk to apply; verbatim diff against §4 and L283/§4-workflows)

```diff
 docs/
-├── architecture/symcon_architecture.md  # the v1.2 document, canonical
+├── architecture/                        # canonical documents — trunk-owned; also included
+│   │                                    #   read-only as Sphinx sources since task 28
+│   ├── symcon_architecture.md           # the v1.3 document, canonical
+│   └── symcon_repo_layout.md            # this document
+├── conf.py                              # Sphinx + MyST + Napoleon + furo (task 28;
+│                                        #   decided in development/records/27_docs_plan §3, TD-1/TD-2)
+├── index.md                             # site landing page (MyST, hand-written)
+├── glossary.md                          # science-in software glossary backing the tutorials
+├── tutorials/                           # tutorial track T0–T8 (T0–T2 landed; MyST, hand-written)
+├── names_registry.md                    # GENERATED by tools/names_audit.py — committed with a
+│                                        #   do-not-edit header; the one sanctioned generated source
 ├── coupling.md                          # operator semantics, preset catalogue, validated/experimental
 ├── porting_guide.md                     # bridge → GT4Py port workflow against ladder L2
-└── api/                                 # sphinx + autodoc from py.typed sources
+└── api/                                 # curated MyST stub pages invoking sphinx autodoc over the
+                                         #   py.typed sources; rendered HTML goes to docs/_build/
+                                         #   (gitignored — built, never committed)
```

```diff
 .github/workflows/
 ├── lint.yml                             # ruff, mypy --strict on core, import-linter contracts
+├── docs.yml                             # sphinx-build + GitHub Pages artifact deploy (task 28)
 ├── test-cpu.yml                         # unit tests + examples smoke + L2/L7-cheap, matrix over constraints/
```

```diff
-├── architecture/symcon_architecture.md  # the v1.2 document, canonical
+├── architecture/symcon_architecture.md  # the v1.3 document, canonical
```
(the L283 errata; the §4 hunk above already carries it — apply once.)

---

## 7. Open questions (trunk decisions, TD-numbered — to be seeded into TRUNK_DECISIONS.md)

- **TD-29.1** Ratify the zero-move structure: keep `development/records/` as the single
  deliverables tree with kind-labelled index; ratify this document's own location as the
  K12 pattern instance. (Alternative: `plan/design/` split — priced out in §4.3.)
- **TD-29.2** Create `development/REGISTRY.md` per §5.1 and adopt the `TD-PENDING:`
  marker; amend AGENTS.md (one sentence in Workflow item 6) and prompts/README
  (invariants) to route future sign-off flags through it. AGENTS.md is trunk-owned —
  this needs the sign-off before the migration task may touch either file.
- **TD-29.3** Adopt the N-series allocation rule (§3.2 item 3) and the forward
  SPEC/STATUS templates (§3.3), recorded in prompts/README; existing files exempt.
- **TD-29.4** Extend unexecuted task 24's scope with the thin `CONTRIBUTING.md`
  (verdict table, §5) — editing an unexecuted prompt is cheap but is still an edit of
  another task's file, hence trunk.
- **TD-29.5** Generalize `.github/PULL_REQUEST_TEMPLATE.md` line 3 from
  `development/specs/____ — one step per PR` to `development/specs/____ or task NN — one step/task
  per PR` (one line; the DoD checklist already fits both).
- **TD-29.6** Whether K13 external-facing drafts *beyond* tasks 23/24 get a
  `plan/drafts/` home, or `reports/<theme>/` stays the pattern. No action until a third
  external-draft task exists; 23/24 paths stay as written either way.
- **TD-29.7** Apply the §6.3 layout-doc revision (trunk-only edit; supersedes and
  absorbs 27 §3.2's narrower additive clarification — D1–D4 — into one revision with
  D5–D9, D11, D12).
- **TD-29.8** Root README refresh (M7): replace the pre-implementation status paragraph
  with the current state (slice merged, docs site, task register) — content proposed in
  the migration task, trunk approves wording at PR review like any other living-doc PR.

---

## 8. Ready-to-lift migration task spec

Written in the `development/plans/` register (cf. `21_ci_hardening.md`); allocate as
`development/plans/31_plan_structure_migration.md` (next free N-series number; 29 = this
analysis, 30 = phase-spec authoring).

---

# Task 31 — Plan-structure migration: registers and indexes (zero moves)

**Branch:** `task/31-plan-structure-migration` (from `main`; verify
`git branch --show-current` before every commit). One commit per item A–E (5 commits +
report). **Prerequisite:** trunk sign-off on TD-29.1/29.2/29.3 (and 29.8 for item D) in
`development/work/reports/report-0029-plan-structure/29_plan_structure.md` §7. TD-29.4/29.5/29.7 are
NOT in scope here (24-prompt edit, PR template, and `docs/architecture/*` are other
tasks'/trunk's files).

## Hard rules (restated; full list in development/work/plans/README.md)

- This task moves and renames NOTHING: `git diff main..HEAD --stat` must show only
  added files and the two named refreshes; any `rename` or `delete` line is an
  automatic failure. Zero edits to `docs/architecture/*`, any `development/{specs,plans,records}/S*` file, any
  prompt file other than `development/work/plans/README.md`, any `reports/*` file other than the
  new `reports/README.md`, `development/references/lock.toml`, or anything under `packages/`, `docs/`,
  `.github/`, `.claude/`, `.opencode/`.
- When seeding `development/REGISTRY.md`, copy decision text **verbatim** from the
  cited source lines (tolerances, signatures — character-exact). If a source line does
  not say what §5.1 of the task-29 proposal claims it says, STOP on that row and report
  the discrepancy; do not paraphrase around it.
- No tolerance changes, no pin changes, no data in git (nothing here should go near any
  of these — their appearance in the diff is a stop condition).

## Item A — `development/archive/plan_tree_map.md`

**Change:** create it with exactly four sections lifted from the task-29 proposal:
(1) the taxonomy table (§2.1), (2) the naming convention (§3.2, incl. the N-series
allocation rule), (3) the forward SPEC/STATUS templates (§3.3), (4) the plan/docs
boundary policy (§5.2). Link the proposal as the rationale record; do not restate its
analysis.

**Verify:** `grep -c "^## " development/archive/plan_tree_map.md` → 4; every relative path mentioned in the
file exists (`grep -oE 'plan/[A-Za-z0-9_/.]+' development/archive/plan_tree_map.md | sort -u | while read p;
do test -e "$p" || echo "MISSING $p"; done` → no output).

## Item B — `development/REGISTRY.md`

**Change:** create the register per proposal §5.1: rule paragraph + table. Seed rows,
each with `Source` pointing at the exact file+section/line: the seven
`IMPLEMENTATION_REPORT.md` §5 rows (status `pending` unless the PR sign-off evidence
exists); 27 §3 TD-1/TD-2/TD-3 (status `signed-off`, evidence: task-28 merge
`cbbec36`); the CHANGELOG-deferral row; the eight TD-29.x rows with their trunk
verdicts as decided. Do NOT edit `IMPLEMENTATION_REPORT.md` — the register declares
that it supersedes §5/§6 going forward; the report stays frozen.

**Verify:** every `Source` path+anchor resolves (same missing-path loop as item A);
row count ≥ 19; `grep -c "TD-PENDING" plan/ -r` — record the count in the report
(expected 0 today; the marker is forward-only).

## Item C — `development/work/plans/README.md` register refresh

**Change:** in the execution-order table, add rows for 26 (executed; prompt ad hoc,
not committed; report committed), 27 (executed; deliverable
`reports/27_docs_plan/`), 28 (executed), 29 (executed; deliverable
`reports/29_plan_structure/`), 30 (unchanged), 31 (this task); add one "Number
allocation" paragraph (proposal §3.2 item 3) and a pointer line to `development/archive/plan_tree_map.md`
for taxonomy/templates. Touch nothing else in the file — the invariants, gate table,
and caches sections are load-bearing verbatim.

**Verify:** `git diff main..HEAD -- development/work/plans/README.md` shows additions only
inside the table region plus the two new paragraphs (no deleted lines other than
table-row reflow); the gate-baseline table is byte-identical.

## Item D — root `README.md` refresh (needs TD-29.8)

**Change:** replace the "Status: pre-implementation…" paragraph with a current status
(vertical slice S01–S14 merged; post-slice task register in `development/plans/`; docs site
built from `docs/` via task 28); extend the Contents table with
`development/work/reports/report-0036-implementation-report.md`, `development/REGISTRY.md`, `development/plans/`; keep the
Bootstrap section but retitle it as historical or update the commands to the current
entry points (`/implement-step`, the prompts register). Do not change License/Contents
rows that are still accurate.

**Verify:** `grep -n "pre-implementation\|No framework code exists" README.md` → empty;
missing-path loop over all `plan/`/`docs/` paths named in the file → no output.

## Item E — `development/work/reports/README.md`

**Change:** create a ≤40-line index: one row per existing entry (26, 27, 28, 29) with
kind labels per the taxonomy (execution report / design document), plus the two
declared-future thematic dirs (`upstream/` ← task 23, `prs/` ← task 24, kind:
external-facing drafts) marked "created by their tasks — do not pre-create", and the
flat-vs-subdir naming rule.

**Verify:** every path row exists on disk except the two future dirs, which must NOT
exist (`test ! -e development/records/upstream -a ! -e development/records/prs`).

## Acceptance criteria

1. Items A–E done exactly as scoped (or explicitly reported blocked), one commit each.
2. Diff scope: `git diff main..HEAD --stat` touches ONLY `development/archive/plan_tree_map.md`,
   `development/REGISTRY.md`, `development/work/plans/README.md`, `README.md`,
   `development/work/reports/README.md`, and the task report. No renames, no deletions.
3. All link/existence loops (items A–E) pass; the two docs-site checks below pass.
4. Report `development/work/reports/report-0031-plan-structure-migration.md` committed:
   per-item verification output, the TRUNK_DECISIONS row count and any verbatim-copy
   discrepancies found, and the recorded gate numbers.

## Verification gates

```
uv run sphinx-build -E -W --keep-going -b html docs /tmp/task31-docs-check   # exit 0 — proves docs untouched
uv run ruff check .                                                          # All checks passed!
uv run ruff format --check .                                                 # same file count as main (markdown-only task)
git diff main..HEAD --stat                                                   # exactly the 6 files of acceptance 2
uv run pytest packages -m "not gpu and not slow" -q                          # counts equal the prompts-README baselines (nothing executable changed)
```
The fast partition is the only pytest gate required (no test, source, config, or
dependency file is in the allowed diff; the other partitions cannot be affected — state
this in the report with the diff listing as evidence).

## Stop rules

- Any item would require editing `docs/architecture/*`, any `development/{specs,plans,records}/S*` file, any
  prompt other than the register, an executed report, `development/references/lock.toml`, or anything
  outside the acceptance-2 file list → STOP that item, mark "blocked — needs trunk
  decision", continue others.
- A TRUNK_DECISIONS source line disagrees with the proposal's characterization → STOP
  that row, report verbatim both texts.
- Any verification loop prints a MISSING path → fix the link if it is YOUR new text,
  STOP if the broken reference exists on `main`.

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Re-run every verification gate yourself, including the sphinx `-W` build and the
  missing-path loops (run them from the repo root, not the report's word).
- Diff discipline: confirm zero renames/deletions and the exact 6-file scope; confirm
  `development/work/plans/README.md`'s gate-baseline table and invariants section are
  byte-identical to `main` (`git diff main..HEAD -- development/work/plans/README.md` inspected
  hunk by hunk).
- TRUNK_DECISIONS spot-check: pick 5 rows at random, open the cited Source, confirm
  character-exact tolerance/signature text and correct status; confirm TD-1/2/3 rows
  cite the 27 report §3 and evidence `cbbec36`.
- Confirm `upstream/` and `prs/` were NOT created and no existing report file changed.
- Confirm the README refresh makes no claim the repo state contradicts (run
  `git log --oneline -3` and the fast gate line against what README now says).

---
*(end of liftable task text)*
