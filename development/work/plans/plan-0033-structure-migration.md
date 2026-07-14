# Task 33 — migrate the project memory to the `development/` tree

**Branch:** `task/33-structure-migration` (this plan is committed on it; execution continues
on the same branch — one PR for the task). **Prerequisite:** `task/32-docs-development-structure`
must be merged to `main` first (its report folder is in the move map §4), and this branch
rebased/merged onto that `main` before execution starts.

**Deliverable:** the migration executed per this plan + the execution report
`development/records/033_structure_migration_record/REPORT.md` (born in the new tree).

This prompt is frozen at assignment. Do not "improve" it beyond its stated scope. Where it
conflicts with reality (a file listed here does not exist, a path already changed), stop,
record the discrepancy in your report, and resolve it only if the resolution is mechanical
and obvious; otherwise report and stop.

---

## 1. Context and the agreed decisions (binding for this task)

The owner has agreed a full reorganization of the repo's process memory (analysis:
`plan/prompts/reports/32_docs_development_structure/32_docs_development_structure.md`,
as amended by owner iteration). The agreed decisions, which this plan implements:

1. All development memory moves to a **top-level `development/` tree** (not under `docs/`).
   `docs/` stays a pure Sphinx site source — **nothing under `docs/` moves**; no `docs/user/`
   nesting; no conf.py `exclude_patterns` change.
2. **Full migration, no frozen-in-place archive.** Every document moves to its kind-folder;
   history is preserved by git (`git mv`, `git log --follow`). `plan/` is deleted at the end.
   Documents with no ongoing relevance go to `development/archive/` instead of a kind-folder.
3. **Policy amendment (owner-confirmed):** "frozen" means **content-frozen** — mechanical
   path-retargeting confined to link/path strings is permitted in a sanctioned migration
   commit. This is ADR-0002 (§3) and register row TD-33.2. Moves and link-rewrites live in
   **separate commits** so "content unchanged" is verifiable by diff (§6).
4. `drafts/` is **dropped** (external-facing texts are their task's records). `records/`
   exists and holds outcome documents, frozen at merge.
5. `plan/TRUNK_DECISIONS.md` is renamed **`development/DECISIONS.md`** and lives at the
   `development/` root (living ledger; the only living file at that level).
6. Future IDs continue the S-series/N-series; spec, plan, and record of one work unit share
   one ID. The task-number register survives as `development/plans/README.md` and keeps its
   allocation rules unchanged.

### Target tree

```
AGENTS.md · CLAUDE.md        root, thinned: authority order + hard rules + pointers to policies/
REFERENCES.lock              root, UNCHANGED (append-only machine ledger — do not touch)
docs/                        pure Sphinx site source — only two one-line edits (§5.9, §5.10)
development/
├── README.md                map of the tree (new)
├── DECISIONS.md             living sign-off/decision register (moved + renamed)
├── policies/                living rules (7 files + README, §3.2)
├── adr/                     NNNN-<kebab-title>.md (3 seeds + README, §3.1)
├── ideas/                   future proposals; migrated phase outlines P2–P7 (+ README)
├── specs/                   S01–S14 SPECs + future, `SXX_<snake>.md` (+ README)
├── plans/                   S01–S14 PLANs + task prompts + README.md = task-number register
├── records/                 STATUS files, task reports, IMPLEMENTATION_REPORT + future (+ README)
├── archive/                 no-longer-relevant documents (+ README)
└── references/              per-source cards (8) + README + local/ (gitignored)
plan/                        DELETED after migration
references/                  DELETED (content absorbed into development/references/local/)
```

## 2. Hard rules (restated; violations = stop and report)

- Never commit to `main`; verify `git branch --show-current` = `task/33-structure-migration`
  before every commit. Commit messages end with the `Co-Authored-By:` trailer for your model.
- **No data files in git. No dependency pin changes. No tolerance changes. No test edits**
  beyond the two path-string updates in §5.11 (and their docstrings).
- **`REFERENCES.lock` is not modified** — not even path strings; its `step` fields are bare
  IDs and its `paths` fields describe *external* repos.
- **`docs/architecture/*` is never edited** (deny-listed). The one planning-path reference in
  `docs/architecture/symcon_repo_layout.md:104` is handled as a proposed-diff artifact for
  owner sign-off (§5.13, TD-33.4) — not as an edit.
- Frozen documents (SPECs, PLANs, STATUS files, executed prompts/reports, the outlines'
  bodies, IMPLEMENTATION_REPORT) receive **only** path-string retargeting per the table in
  §5.1 — no wording, formatting, or content changes. The two sanctioned exceptions:
  the `Status:` header line *added above* each outline (§4 row 8) and the supersede header
  *added above* `archive/plan_tree_map.md` (§4 row 3). Additions above the original text,
  never edits within it.
- Every gate in §7 must be green before the PR. Never use `-x`, `--ignore`, `-k`, marker
  edits, or assertion deletions to get there.

## 3. Phase A — governance documents (write these first, commit C3)

### 3.1 ADRs (`development/adr/`), Nygard format

Each file: `# NNNN — <title>`, then `**Status:** accepted · **Date:** <merge date>`,
then sections `## Context`, `## Decision`, `## Consequences`, `## Alternatives considered`.
Write them from §1 of this plan and the task-32 evaluation; keep each under ~60 lines.

- `0001-development-tree-reorganization.md` — the tree of §1; full migration over
  freeze-in-place (alternatives: zero-move [TD-29.1, superseded], freeze-as-archive
  [task-32 recommendation, overridden by owner]); `docs/` untouched; drafts/ dropped;
  DECISIONS.md rename (STATUS.md rejected: collides with the fourteen per-step
  `STATUS.md` records).
- `0002-content-frozen-records.md` — frozen = content-frozen; mechanical path retargeting
  allowed only in sanctioned migration commits, isolated so `git diff --word-diff` shows
  path strings only; header-line *additions* sanctioned case-by-case by the migration plan.
- `0003-decision-register-and-adrs.md` — register and ADRs are two instruments, no merge:
  `DECISIONS.md` is the sign-off ledger (rows, statuses, `TD-PENDING:` grep contract);
  `adr/` holds reasoning for architecture-shaped decisions; such decisions get both, the
  row's Source pointing at the ADR.
- `README.md` — index table (number, title, status) + one paragraph on when to write an ADR
  vs only a register row (rule of thumb from ADR-0003).

### 3.2 Policies (`development/policies/`)

Living rule documents, snake_case, one topic each. **Content is extracted from the named
sources — reuse their wording; do not invent new rules.** Each file starts with a one-line
scope sentence. After extraction the *policy file is the single living source*; the old
locations either move to the archive (plan/README.md) or are thinned to pointers (AGENTS.md).

| File | Content source |
|---|---|
| `naming_conventions.md` | `plan/README.md` §2 (S/P/N series, allocation rule, `_REPORT` vs folder-deliverable, `TD-PENDING:` marker), retargeted to the new tree; add: ADR `NNNN-kebab` exception; spec/plan/record share one ID |
| `records_and_liveness.md` | `plan/README.md` §1 taxonomy table + §3 templates, rewritten for the new tree; add rows for the new kinds (policy=living; adr=frozen-after-accepted, Status field mutable; idea=living until graduated; spec/plan=frozen at acceptance/assignment; record=frozen at merge; reference card=living; archive=dead). Include the content-frozen rule (ADR-0002) and the artifact-reference rule |
| `docs_boundary.md` | `plan/README.md` §4 rewritten for the new geometry: published surface = `docs/`; `development/` is never a Sphinx source, never hyperlinked from site pages (prose mentions fine), never deployed; development content wanted user-facing is rewritten under `docs/`, never included mechanically; `GENERATED FILE` header rule |
| `verification_gates.md` | `plan/prompts/README.md` "verification gate" + baseline table + output-reading rules + "Caches" section, verbatim (these are load-bearing); keep-current rule: a merged task that changes counts updates this file in the same commit |
| `reference_mining.md` | AGENTS.md workflow item 3 + the REFERENCES.lock bullet from `plan/prompts/README.md` invariants (pinned pair with SHAs, dkrz mirror gotcha, append-at-consultation rule) |
| `agent_workflow.md` | AGENTS.md "Workflow for a step" rewritten for the new paths (read spec → plan → mine references → implement → gates → record → one PR), plus the implementer/reviewer-loop convention and branch naming (`step/SXX-*`, `task/NN-*`) |
| `review_protocol.md` | **moved** `plan/prompts/10_REVIEW_PROTOCOL.md` (§4 row 9), paths retargeted |
| `README.md` | index: one line per policy + the rule "policies are living, trunk-gated; agents follow them and propose changes via ideas/ or the register" |

### 3.3 Register edits (`development/DECISIONS.md`, after its move)

1. Retitle H1 to `# DECISIONS — trunk-decision and sign-off register` and add one line under
   the header rules: `Formerly plan/TRUNK_DECISIONS.md (renamed in task 33, TD-33.3).`
2. Retarget all path strings per §5.1 (Source/Evidence columns reference moved reports).
3. Append rows (Status `pending`; Date = the merge date, filled at merge like prior tasks):
   - **TD-33.1** — development/ tree reorganization adopted per task-32 evaluation as amended
     by owner iteration; full migration; `plan/` deleted. Source: ADR-0001 +
     `development/plans/33_structure_migration.md` §1. **Supersedes TD-29.1** (zero-move)
     **and TD-29.6** (external-drafts home: resolved as "no dedicated folder").
   - **TD-33.2** — content-frozen amendment (ADR-0002).
   - **TD-33.3** — register renamed/moved to `development/DECISIONS.md`; ledger/ADR
     no-merge relationship (ADR-0003).
   - **TD-33.4** — proposed revision of `docs/architecture/symcon_repo_layout.md` repo tree
     (§5.13 diff artifact); owner applies or rejects. Marks the re-draft of TD-29.7 —
     add to TD-29.7's Status cell: `superseded(TD-33.4)`.
4. Flip statuses: TD-29.1 → `superseded(TD-33.1)`, TD-29.6 → `superseded(TD-33.1)`,
   TD-29.7 → `superseded(TD-33.4)`. Do not touch any other cell of those rows.

## 4. Phase B — the move map (commit C1: `git mv` only, plus physical moves of untracked files)

Before C1, physically relocate **untracked** files (plain `mv`, they never enter git):
`references/*.pdf` (3), `references/prompts-backups.md`, `plan/outlines/prompts-backups.md`,
and `plan/steps/S04_coupling_algebra/artifacts/` (2 PNGs) →
`development/references/local/` and `development/records/S04_coupling_algebra/artifacts/`
respectively. List every relocated untracked file in your report.

Tracked moves — every row is a `git mv`; nothing else goes into C1:

| # | From | To |
|---|---|---|
| 1 | `plan/00_OVERVIEW.md` | `development/records/00_OVERVIEW.md` |
| 2 | `plan/IMPLEMENTATION_REPORT.md` | `development/records/IMPLEMENTATION_REPORT.md` |
| 3 | `plan/README.md` | `development/archive/plan_tree_map.md` |
| 4 | `plan/TRUNK_DECISIONS.md` | `development/DECISIONS.md` |
| 5 | `plan/steps/SXX_<n>/SPEC.md` (14×) | `development/specs/SXX_<n>.md` |
| 6 | `plan/steps/SXX_<n>/PLAN.md` (14×) | `development/plans/SXX_<n>.md` |
| 7 | `plan/steps/SXX_<n>/STATUS.md` (14×) | `development/records/SXX_<n>/STATUS.md` |
| 8 | `plan/outlines/P{2..7}_*.md` (6×) | `development/ideas/P{2..7}_*.md` |
| 9 | `plan/prompts/10_REVIEW_PROTOCOL.md` | `development/policies/review_protocol.md` |
| 10 | `plan/prompts/{20,21,22,23,24,25,28,30}_*.md` (8×) | `development/plans/<same name>` |
| 11 | `plan/prompts/README.md` | `development/plans/README.md` |
| 12 | `plan/prompts/33_structure_migration.md` (this file) | `development/plans/33_structure_migration.md` |
| 13 | `plan/prompts/reports/{26,28,31}_*_REPORT.md` (3×) | `development/records/<same name>` |
| 14 | `plan/prompts/reports/27_docs_plan/` | `development/records/27_docs_plan/` |
| 15 | `plan/prompts/reports/29_plan_structure/` | `development/records/29_plan_structure/` |
| 16 | `plan/prompts/reports/32_docs_development_structure/` | `development/records/32_docs_development_structure/` |
| 17 | `plan/prompts/reports/README.md` | `development/records/README.md` |
| 18 | `references/README.md` | `development/references/local/README.md` |

Rows 5–7 as a loop (folder names are `S01_repo_scaffold` … `S14_plan_through_dycore`):

```bash
for d in plan/steps/S*_*/; do n=$(basename "$d")
  git mv "$d/SPEC.md"  "development/specs/$n.md"
  git mv "$d/PLAN.md"  "development/plans/$n.md"
  mkdir -p "development/records/$n" && git mv "$d/STATUS.md" "development/records/$n/STATUS.md"
done
```

After C1: `git commit`; then `git show --stat -M100 HEAD | grep -cE "^ rename"` must equal
the tracked-move count (66) and `git show -M100 --name-status HEAD | grep -vE "^R100"` must
show nothing but the commit header — any `M`/`A`/`D` line means C1 is impure; fix before
proceeding. Empty `plan/` and `references/` directories disappear with their last file.

## 5. Phase C — retargeting and living edits

### 5.1 Path-retarget table (commit C2 — applies to every `.md` now under `development/`)

Rewrite path strings left→right. Longest-prefix wins (apply top to bottom):

| Old string | New string |
|---|---|
| `plan/steps/<SXX_n>/SPEC.md` | `development/specs/<SXX_n>.md` |
| `plan/steps/<SXX_n>/PLAN.md` | `development/plans/<SXX_n>.md` |
| `plan/steps/<SXX_n>/STATUS.md` | `development/records/<SXX_n>/STATUS.md` |
| `plan/steps/<SXX_n>/artifacts` | `development/records/<SXX_n>/artifacts` |
| `plan/steps/` (generic, e.g. `plan/steps/SXX_*/`) | rewrite naming the kind's new home, e.g. `development/specs/SXX_*.md` (SPECs), `development/records/SXX_*/STATUS.md` (STATUS) — pick per what the sentence refers to |
| `plan/prompts/10_REVIEW_PROTOCOL.md` | `development/policies/review_protocol.md` |
| `plan/prompts/reports/` | `development/records/` |
| `plan/prompts/README.md` | `development/plans/README.md` |
| `plan/prompts/` | `development/plans/` |
| `plan/outlines/` | `development/ideas/` |
| `plan/TRUNK_DECISIONS.md` | `development/DECISIONS.md` |
| `plan/00_OVERVIEW.md` | `development/records/00_OVERVIEW.md` |
| `plan/IMPLEMENTATION_REPORT.md` | `development/records/IMPLEMENTATION_REPORT.md` |
| `plan/README.md` | `development/archive/plan_tree_map.md` |
| `references/` (the top-level PDF-drop dir) | `development/references/local/` |
| bare `plan/` meaning the tree (e.g. "the plan/ folder") | `development/` |

**Never touch** (source code, not the planning tree): `symcon/core/plan/`, `core/plan/`,
`plan/ops.py`, `plan/bind.py`, `symcon.core.plan`, `plans/<plan-hash>`,
`$XDG_CACHE_HOME/symcon/plans/`, the words "plan"/"plans" not part of a repo path, and
anything inside `docs/architecture/`. When a match is ambiguous, read the sentence; if
still ambiguous, leave it and list it in your report.

In frozen documents C2 changes path strings **only** (§2). In living documents
(`development/plans/README.md`, `development/records/README.md`, `DECISIONS.md`) fuller
edits happen in C4/C5, but the path strings may land here.
Commit C2, then verify purity: `git show HEAD --word-diff=porcelain | grep -E "^\+"` —
every added fragment must be a path string from the New column (spot-check; the reviewer
re-checks).

### 5.2–5.13 New files and living-file edits (commits C3–C5)

Commit boundaries: **C3** = governance + skeleton (ADRs §3.1, policies §3.2,
`development/README.md`, folder READMEs, reference cards §5.3, outline `Status:` headers,
archive header §5.4). **C4** = living md rewrites (§5.5–§5.7, register edits §3.3).
**C5** = code/config/tooling (§5.8–§5.12) + the diff artifact (§5.13).

2. **`development/README.md`** (new): one-paragraph purpose ("repo-internal process memory;
   not a Sphinx source — see `policies/docs_boundary.md`"), the tree with one line per
   folder (§1), where to start for: implementing (specs+plans), reviewing
   (policies/review_protocol.md), deciding (DECISIONS.md, adr/), and the pointer
   "history of the S01–S14 slice: `records/`, overview in `records/00_OVERVIEW.md`".
3. **Reference cards** `development/references/*.md` (8 files + README): `icon4py.md`,
   `gt4py.md`, `icon_fortran.md`, `sympl.md`, `tasmania.md`, `icon_tutorial_2025.md`,
   `ubbiali_thesis.md`, `icon_grid_generator.md`. Template per card: `# <name>` ·
   `**Source:** <canonical URL>` · `**Pinned:** <version/SHA and where the pin is decided
   (constraints/, uv.lock, or "corpus pin, see records/00_OVERVIEW.md §3")>` ·
   `**License:** …` · `## Role in the project` (2–4 sentences) · `## Gotchas` (e.g.
   icon_fortran: "gitlab.dwd.de does not resolve; use the gitlab.dkrz.de mirror";
   sympl: upstream + stubbiali `oop` fork) · `## Consultation ledger` → one line pointing
   at `REFERENCES.lock` (grep by source id). Facts come from `records/00_OVERVIEW.md` §3,
   `REFERENCES.lock` entries, and `constraints/cpu-ci.txt` — **no facts from memory**.
   `README.md`: card index + the ownership rule (cards are living, updated only when a pin
   or corpus decision changes; the lock is the machine ledger, appended per consultation).
   `local/` keeps the moved README (row 18) — rewrite its first line to name the new path.
4. **Archive**: `development/archive/README.md` (new, 3–5 lines: "documents with no ongoing
   relevance, kept for reference; nothing here is authoritative"). Prepend to
   `archive/plan_tree_map.md` (above the original H1): a one-line note
   `> Superseded by the development/ tree (task 33, TD-33.1); kept for reference.`
5. **`development/plans/README.md`** (living rewrite): retitle for the new home; the
   task-number register table stays with all rows, `Deliverable` paths retargeted to
   `records/`; execution-order table stays; the gate battery + baselines + caches sections
   are **replaced by a pointer** to `policies/verification_gates.md` (single living source);
   the invariants list stays (it is the anti-drift restatement source) with paths updated.
   Add register rows: `32 | structure evaluation | ad hoc (not committed) | executed |
   records/32_docs_development_structure/` and `33 | structure migration |
   33_structure_migration.md | executed | records/33_structure_migration/`.
6. **`development/records/README.md`** (living rewrite): extend the moved reports index to
   cover all records: the S01–S14 `SXX_<n>/STATUS.md` records (one table), task reports
   (existing table, paths updated), `00_OVERVIEW.md`, `IMPLEMENTATION_REPORT.md`. Document
   the two shapes: flat `NN_<snake>_REPORT.md` vs folder `NN_<snake>/` (sidecars), and
   `SXX_<n>/STATUS.md` (+ untracked `artifacts/` with the regeneration-command rule).
7. **Folder READMEs** for `ideas/` and `specs/` (new, short): purpose, naming, liveness,
   and for `ideas/` the `Status:` header convention
   (`proposed / accepted / accepted-roadmap / rejected / superseded / graduated → spec SXX`).
   Prepend to each moved outline, above its H1: `**Status:** accepted-roadmap (graduates to
   development/specs/ via task 30).`
8. **Root `README.md`**: rewrite the repo-map table rows for `plan/*` (lines ~23–29) into
   the `development/` folders + `DECISIONS.md`; update lines 13–14, 38, 41 (paths only,
   keep the wording).
9. **`docs/index.md:51`**: the prose sentence mentioning `plan/` → `development/`
   (no hyperlink — boundary policy). **`docs/conf.py:2`**: update the comment's report path.
   Nothing else under `docs/` changes.
10. **AGENTS.md + CLAUDE.md** (thin, keep binding content): AGENTS.md keeps authority order
    (updated: `docs/architecture/symcon_architecture.md` (v1.3) > `development/specs/SXX_*.md`
    > `development/plans/SXX_*.md`), the Hard rules verbatim (with `plan/steps` → new paths
    in rule 5's wording), Environment, and replaces the Workflow and Reference-corpus bodies
    with 2–3-line summaries pointing at `development/policies/agent_workflow.md`,
    `reference_mining.md`, and `development/references/`. CLAUDE.md line 9 → "Specs/plans
    live in `development/specs/` and `development/plans/`". Do not delete any rule that has
    no policy-file home.
11. **Test/benchmark path strings**: `packages/symcon-core/tests/test_order_ode.py` lines
    9 and 101, `test_order_burgers.py` line 87 →
    `development/records/S04_coupling_algebra/artifacts` (the `parents[3]` depth is
    unchanged — verify the resulting path exists at runtime via the gate run);
    `benchmarks/s05_dispatch.py:4` and `benchmarks/dispatch_overhead/jw_step.py:4`
    docstrings → new STATUS paths. No other code lines change.
12. **Config/tooling**: `.claude/settings.json:29` deny glob `Edit(plan/steps/**/SPEC.md)` →
    `Edit(development/specs/**)`. `.gitignore`: `plan/steps/*/artifacts/` →
    `development/records/*/artifacts/`; `references/*` + `!references/README.md` →
    `development/references/local/*` + `!development/references/local/README.md`.
    `.claude/commands/implement-step.md` and `.opencode/command/implement-step.md`: rewrite
    the step file paths (SPEC → `development/specs/$ARGUMENTS.md`, PLAN →
    `development/plans/$ARGUMENTS.md`, STATUS → `development/records/$ARGUMENTS/STATUS.md`
    — note `$ARGUMENTS` is the step folder name, e.g. `S15_foo`).
    `.github/PULL_REQUEST_TEMPLATE.md:3` → `development/specs/____`. Check
    `.claude/commands/review-step.md` and the `.opencode` twin for planning paths (none
    found at plan-writing time; verify).
13. **Layout-doc diff artifact** (do NOT edit the doc): produce
    `development/records/033_structure_migration_record/layout_doc_revision.diff` — a unified diff
    against `docs/architecture/symcon_repo_layout.md` replacing the `plan/` node in the §4
    repo tree (line ~104) with the `development/` tree (one line per folder) and deleting
    the top-level `references/` node if present. The owner applies it (TD-33.4).

## 6. Commit sequence (fixed)

| Commit | Content | Purity check |
|---|---|---|
| C1 | `git mv` moves only (§4) | 66 renames, zero non-`R100` lines |
| C2 | path retargeting in moved md files (§5.1) | word-diff = path strings only |
| C3 | new files + sanctioned header additions (§3.1, §3.2, §5.2–5.4, §5.7 headers) | only `A` lines + the two header-prepend `M`s |
| C4 | living md rewrites (§3.3, §5.5, §5.6, §5.8) | named files only |
| C5 | code/config/tooling + diff artifact (§5.9–§5.13) | named files only |
| C6 | report + any review-round fixes | — |

## 7. Verification gates (all must pass; run from the repo root)

1. **Residual-path grep** — must return exactly one hit
   (`docs/architecture/symcon_repo_layout.md:104`, owner-owned via TD-33.4):

   ```bash
   grep -rnE "plan/(steps|prompts|outlines|README\.md|00_OVERVIEW|IMPLEMENTATION_REPORT|TRUNK_DECISIONS)" . \
     --exclude-dir=.git --exclude-dir=docs/_build
   ```

   Any other hit is an unfinished retarget. `grep -rn "TRUNK_DECISIONS" . --exclude-dir=.git`
   must return nothing outside `development/DECISIONS.md`'s own "formerly" line and ADR/record
   prose that names the old file historically (list such hits in the report).
2. **Relative-link check** — every markdown link target under `development/` and `docs/`
   must exist:

   ```bash
   fail=0
   while IFS=: read -r f l m; do
     t="${m#*(}"; t="${t%)}"; t="${t%%#*}"
     case "$t" in http*|mailto:*|"") continue;; esac
     [ -e "$(dirname "$f")/$t" ] || [ -e "$t" ] || { echo "BROKEN $f:$l -> $t"; fail=1; }
   done < <(grep -rnoE '\]\([^)]+\)' development docs README.md AGENTS.md CLAUDE.md --include='*.md')
   exit $fail
   ```

   Zero `BROKEN` lines (gitignored targets like `artifacts/` files count as broken —
   records must cite them with regeneration commands, not links; report any found).
3. **TD-PENDING audit**: every `grep -rn "TD-PENDING" development/` hit corresponds to an
   open (`pending`) row in `development/DECISIONS.md`.
4. **Full gate battery** (baselines from `development/policies/verification_gates.md`,
   identical to the pre-move table: fast 739 passed/1 skipped; slow-no-data 31;
   data-not-slow 43; data-slow 76/1 skipped; ruff `All checks passed!` + `173 files already
   formatted`; mypy 50 files; lint-imports 2 kept — **no count may change**: this task adds
   no `.py` files and no tests):

   ```bash
   uv run pytest packages -m "not gpu and not slow" -q
   uv run pytest packages -m "slow and not gpu and not data" -q
   uv run pytest packages -m "data and not slow and not gpu" -q
   uv run pytest packages -m "data and slow and not gpu" -q
   uv run ruff check . && uv run ruff format --check .
   uv run mypy --strict -p symcon.core
   uv run lint-imports
   ```

   Runtimes exceed a 10-minute shell cap — run in background or split by file, never skip a
   partition. The S04 order tests (in the fast partition) exercise the §5.11 path change and
   must write `development/records/S04_coupling_algebra/artifacts/*.png`.
5. **Sphinx**: `uv run sphinx-build -E -W --keep-going -b html docs docs/_build/html`
   exits 0.
6. **Tree checks**: `git ls-files plan/ references/` outputs nothing; `[ ! -d plan ]`;
   `ls development/` shows exactly the §1 folders + `README.md` + `DECISIONS.md`.

## 8. Report — `development/records/033_structure_migration_record/REPORT.md`

Header (branch/date/state per the STATUS template in `policies/records_and_liveness.md`),
then: (1) move ledger — confirm §4 executed, list every deviation; (2) retarget statistics —
hits rewritten per §5.1 row, ambiguous matches left + why; (3) untracked files relocated;
(4) gate outputs — the summary line of each §7 command verbatim, dated; (5) register rows
added and statuses flipped; (6) the §5.13 diff artifact pointer and any hits from §7.1/7.2
left by design; (7) follow-ups.

## 9. Review checklist (fresh reviewer agent; protocol at `development/policies/review_protocol.md` after C1)

Scope first: the diff touches only §4–§5 files. Then verify, with evidence per finding:

1. C1 purity (`git show --stat -M100 <C1> | grep -cE "^ rename"` = 66; no non-rename lines)
   and C2 purity (word-diff on 5 randomly chosen frozen files: path strings only — any
   wording change in a frozen document is MAJOR).
2. Re-run §7.1, §7.2, §7.3, §7.6 yourself; re-run the full §7.4 battery and §7.5 build;
   compare counts to `policies/verification_gates.md` (must be identical to pre-move).
3. `git diff main -- docs/architecture REFERENCES.lock constraints/ uv.lock` is empty.
4. ADRs 0001–0003 state the §1 decisions faithfully; DECISIONS.md rows TD-33.1–4 exist,
   TD-29.1/29.6/29.7 statuses flipped exactly as §3.3, no other row cells changed.
5. Policies contain the load-bearing content (spot-check: gate baselines table present
   verbatim in `verification_gates.md`; allocation rule in `naming_conventions.md`;
   templates in `records_and_liveness.md`); AGENTS.md lost no hard rule (diff it).
6. Reference cards: every `**Pinned:**` value matches `constraints/cpu-ci.txt` /
   `REFERENCES.lock` — a card fact with no source is MAJOR.
7. Report honesty: gate outputs dated and verbatim; deviations declared.

Verdict per protocol: `approve` or `request-changes` with MAJOR/MINOR/INFO findings,
file:line evidence each.
