# Work unit 0051 — kebab-case everywhere + flat reports with sibling artifact folders

**Branch:** `work/0051-kebab-and-flat-reports` · One PR. **Deliverable:** the migration +
`development/work/reports/report-0051-kebab-and-flat-reports.md`.

Frozen at assignment. Owner mandate (2026-07-15, direct instruction — no evaluation round):
(1) kebab-case for ALL filenames under `development/` — including `policies/` — never
snake or mixed (the ADR-0006 kebab/snake split is superseded); (2) reports are FILES
`report-<NNNN>-<kebab>.md`; only when a report has extra artifacts do they live in a
sibling folder `report-<NNNN>-<kebab>/` next to the file. Rename everything existing and
update all references. On conflict with reality: stop, record, resolve only the
mechanical-and-obvious.

## 1. Binding rules

- `git branch --show-current` = `work/0051-kebab-and-flat-reports` before every commit;
  never commit to main; never push; `Co-Authored-By:` trailer.
- No data, no pins, no tolerances. `lock.toml` untouched entirely this time (no header
  edits). `docs/architecture/symcon_architecture.md` untouched.
- Frozen documents: path-string retargets only; the flattening renames (STATUS.md →
  report file) are pure `git mv`, content byte-identical.
- `README.md` files keep their name everywhere (conventional, not snake). `lock.toml`,
  `STATUS.md`-era inner names disappear via flattening, not renaming-in-place.
- `packages/`/`benchmarks/` edits: exactly the path strings in §5.3.

## 2. Rename map (commit C1 — `git mv` only, 35 renames)

**policies/ (8):** `agent_workflow.md → agent-workflow.md`,
`docs_boundary.md → docs-boundary.md`, `document_kinds.md → document-kinds.md`,
`naming_conventions.md → naming-conventions.md`,
`reference_mining.md → reference-mining.md`, `repo_layout.md → repo-layout.md`,
`review_protocol.md → review-protocol.md`,
`verification_gates.md → verification-gates.md`.

**references/ (4):** `icon_fortran.md → icon-fortran.md`,
`icon_grid_generator.md → icon-grid-generator.md`,
`icon_tutorial_2025.md → icon-tutorial-2025.md`, `ubbiali_thesis.md → ubbiali-thesis.md`
(gt4py/icon4py/sympl/tasmania have no underscores — unchanged).

**archive/ (1):** `plan_tree_map.md → plan-tree-map.md`.

**work/reports/ flattening (21 main documents):**
- The 14 STATUS folders: `report-<NNNN>-<kebab>/STATUS.md → report-<NNNN>-<kebab>.md`
  for 0001–0014 (e.g. `report-0001-repo-scaffold/STATUS.md → report-0001-repo-scaffold.md`).
- `report-0027-docs-plan/27_docs_plan.md → report-0027-docs-plan.md`
- `report-0029-plan-structure/29_plan_structure.md → report-0029-plan-structure.md`
- `report-0032-docs-development-structure/32_docs_development_structure.md → report-0032-docs-development-structure.md`
- `report-0033-structure-migration/REPORT.md → report-0033-structure-migration.md`
- `report-0034-naming-iteration/34_naming_iteration.md → report-0034-naming-iteration.md`
- `report-0035-naming-migration/REPORT.md → report-0035-naming-migration.md`

**sidecar kebab (1):**
`report-0033-structure-migration/layout_doc_revision.diff → report-0033-structure-migration/layout-doc-revision.diff`
(the folder survives as 0033's artifacts folder — exactly the owner's pattern).

**Untracked artifacts (plain `mv`, before C1, never `git add`ed):**
`report-0004-coupling-algebra/artifacts/*.png` (2 files) →
`report-0004-coupling-algebra/*.png`; remove the empty `artifacts/` subdir. The folder
`report-0004-coupling-algebra/` survives on disk as the artifacts folder beside the new
flat report file.

After C1: purity — 35 `^ rename` lines in `git show --summary -M100 HEAD` (count first,
explain any delta against this map in the record), zero non-`R100`;
`find development -type d -empty` empty (the 18 emptied report folders vanish with their
last file; 0004 and 0033 legitimately persist — 0004 holds only untracked PNGs so it is
absent from git but present on disk).

## 3. Path retargeting (commit C2 — path strings only)

Old→new per §2, over every `.md`/`.diff` under `development/` and the living root files.
Notes:

- Policy filenames are cited from AGENTS.md, CLAUDE.md, README.md, the PR template, both
  command sets, and many frozen documents — all path-string class.
- Flattened report paths: `…/report-<NNNN>-<kebab>/STATUS.md` → `…/report-<NNNN>-<kebab>.md`;
  same for the seven named inner docs. A reference to a report *folder* that meant the
  document now points at the file; a reference that means 0033's artifacts keeps the
  folder form. Judgment calls listed in the record.
- Never touch: source code paths, `lock.toml`, `docs/architecture/`, the §2 map in THIS
  plan, and the established self-exempt set (033/035/0050 plans' and reports' own
  mapping tables and quoted outputs, the 034/049 analyses) — same judgment as 0050's C2;
  list every left-alone case.

Purity: word-diff = path strings only. Commit C2.

## 4. Content updates (commit C3)

1. **`ADRs/0007-kebab-everywhere-flat-reports.md`** — Nygard, ≤50 lines, from this
   plan's preamble: kebab for all `development/` filenames (README.md excepted as
   conventional; lock.toml a fixed name); flat reports + sibling artifacts folder
   (folder exists ONLY when artifacts exist, named exactly like the report file minus
   `.md`); supersedes ADR-0006's kebab/snake-split clause and the folder-report shape;
   alternatives (status quo mixed; folder-per-report) rejected by owner mandate.
   Update ADR-0006's `Status:` line (mutable field):
   `accepted; kebab/snake split and folder-report shape superseded-by-0007 (all other clauses stand)`.
   Update `ADRs/README.md` (index 0000–0007, next 0008).
2. **REGISTRY.md**: allocate row
   `0051 | kebab-and-flat-reports | plan + report | this work unit`; next free **0052**;
   append **§2c — remap (work 0051)**: the complete §2 old→new table; decision rows
   TD-51.1 (kebab everywhere, source ADR-0007), TD-51.2 (flat reports + artifacts-folder
   rule + per-folder gitignore convention) — pending/(merge). Retarget policy-file paths
   in existing cells (path-string class).
3. **Policies content**: `naming-conventions.md` — kebab everywhere (drop the
   kebab/snake split section), the flat-report shape, the artifacts-folder rule, the
   gitignore convention (each report folder holding ONLY untracked artifacts gets its
   own explicit `.gitignore` line; folders holding tracked sidecars are not ignored);
   `document-kinds.md` — report shape row updated (file + optional sibling folder);
   `repo-layout.md` — tree node redrawn if it lists the old shapes. Other policies:
   path updates only.
4. **READMEs**: `development/README.md`, `work/README.md`, `work/reports/README.md`
   (the shape explanation + index), `references/README.md` (card filenames),
   `archive/README.md` if it names the map file, `policies/README.md` (index).

## 5. Living-file edits and tooling (commit C4)

1. **AGENTS.md / CLAUDE.md / root README / PR template**: policy path updates (e.g.
   `development/policies/verification-gates.md`).
2. **Commands** (`.claude/commands/implement-plan.md`, `review-work.md` + `.opencode`
   twins): the report deliverable is `development/work/reports/report-$ARGUMENTS.md`,
   with artifacts (if any) in `development/work/reports/report-$ARGUMENTS/`.
3. **Code path strings** (only these):
   `packages/symcon-core/tests/test_order_ode.py` (docstring + path line) and
   `test_order_burgers.py`: `…/report-0004-coupling-algebra/artifacts` →
   `…/report-0004-coupling-algebra`;
   `benchmarks/s05_dispatch.py:4`: `report-0005-vault-plan-t1/STATUS.md` →
   `report-0005-vault-plan-t1.md`;
   `benchmarks/dispatch_overhead/jw_step.py:4`: `report-0014-plan-through-dycore/STATUS.md`
   → `report-0014-plan-through-dycore.md`.
4. **`.gitignore`**: `development/work/reports/*/artifacts/` →
   `development/work/reports/report-0004-coupling-algebra/` (the one untracked-artifacts
   folder today; the per-folder convention is §4.3's policy text).
5. **`docs/conf.py:2`** comment: the 0027 path → `…/report-0027-docs-plan.md`.

## 6. Gates (C5 = record; battery + checks before it)

Baselines unchanged (fast 739/1 · slow 31 · data 43 · data-slow 76/1 · ruff clean/173 ·
mypy 50 · lint-imports 2 · sphinx `-E -W` exit 0). Detached sentinel logs
`/tmp/gate0051_*.log`, actively polled, partitions sequential; the **slow** partition
must write the S04 PNGs at the NEW location
`development/work/reports/report-0004-coupling-algebra/*.png`. Checks:

```bash
grep -rnE "development/(policies|references)/[a-z0-9]+_[a-z0-9_]+\.md" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rnE "report-[0-9]{4}-[a-z0-9-]+/(STATUS\.md|REPORT\.md|[0-9]{2}_)" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rn "plan_tree_map\|layout_doc_revision" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rn "artifacts/" .gitignore development/work/reports/ packages/symcon-core/tests/
```

Each: hits only in frozen by-design (plans/reports own tables + quoted output — the
established self-exempt set) + this plan + REGISTRY remap tables; enumerate every hit in
the record. Plus: the link checker (0 BROKEN), husk check (`find development -type d
-empty` empty), untouchables diff (`git diff main -- docs/architecture constraints/
uv.lock` empty; `packages/` diff = only §5.3 lines), `git status --porcelain` clean at
the end, TOML validity of lock.toml unchanged (51 entries; the file must be untouched:
`git diff main -- development/references/lock.toml` empty).

## 7. Record and review

Record per `policies/document-kinds.md` template at
`development/work/reports/report-0051-kebab-and-flat-reports.md` (flat — its own rule):
rename ledger, retarget stats + judgment calls, verbatim dated gate lines, deviations,
by-design hits one line each, follow-ups. Review checklist (fresh reviewer; protocol at
`development/policies/review-protocol.md` post-C1): C1 purity 35 (verify every pair,
incl. the 0004 untracked relocation on disk), C2 whole-commit word-diff, frozen
byte-identity of ≥3 flattened STATUS reports vs their main blobs, ADR-0007 + 0006 Status
scoping, REGISTRY §2c completeness + TD-51.1–2, policy/README content vs the mandate,
gates re-run (or dated-log-verify long partitions), residual greps + link + husk +
untouchables re-run, record honesty. Verdict per protocol.
