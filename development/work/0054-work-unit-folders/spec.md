# 0054 — Per-work-unit folders (transpose `work/` from by-kind to by-unit)

**Depends on:** 0050, 0051 (the current `work/` layout they built) · **Source:** owner-requested (this session, 2026-07-19) · **Policies:** `policies/naming-conventions.md`, `policies/document-kinds.md`, `policies/agent-workflow.md`, `policies/verification-gates.md`

## Goal

Regroup `development/work/` so that all lifecycle documents of one work unit live in **one
folder named for the unit**, transposing the tree from kind-major to unit-major:

```
# before (kind-major, today)                # after (unit-major, this work unit)
work/specs/spec-0005-vault-plan-t1.md       work/0005-vault-plan-t1/spec.md
work/plans/plan-0005-vault-plan-t1.md       work/0005-vault-plan-t1/plan.md
work/reports/report-0005-vault-plan-t1.md   work/0005-vault-plan-t1/report.md
work/proposals/proposal-0037-…​.md           work/0037-p2-distributed/proposal.md
```

This is a **pure reorganization with no content change and no behavior change** — a
transposition, not a redesign. The lifecycle (proposal → spec → plan → report), the
four-digit work-id scheme, the never-reuse/never-backfill allocation rule, and the
`REGISTRY.md` single-allocator invariant all survive unchanged. It is the natural
completion of the 0049→0050 direction ("a work unit is the atomic thing"): 0050 grouped the
lifecycle *stream* under `work/`; this groups each *unit's* documents together.

This is a **trunk decision** (tree-structure change; `AGENTS.md` hard rules, TD register).
It is registered as work unit 0054 and gated on owner acceptance of the decision points in
§ *Open decisions*.

## In scope

1. **Move every existing work document** into a per-unit folder
   `development/work/<NNNN>-<kebab-slug>/`, renamed to its bare kind
   (`proposal.md` / `spec.md` / `plan.md` / `report.md`). All 43 current units, 87 tracked
   files. Only the documents that exist move; folders are never padded with placeholders.
2. **Move report artifacts** into a per-unit `artifacts/` subfolder (§ Frozen interfaces):
   the one tracked sidecar
   `report-0033-structure-migration/layout-doc-revision.diff` →
   `0033-structure-migration/artifacts/layout-doc-revision.diff`; the untracked
   `report-0004-coupling-algebra/` PNGs → `0004-coupling-algebra/artifacts/`.
3. **Retarget path references** (the ~296 reference lines across ~60 files the sweep found):
   living files edited directly; frozen files get **mechanical path-string retargeting
   only**, isolated in a sanctioned migration commit and verified by `git diff --word-diff`
   (ADR-0001 content-frozen rule; identical discipline to 0050/0051). Frozen evaluations
   whose *subject* is the old path layout (notably this migration's own future report and
   `report-0049-work-structure-iteration.md`) are left byte-identical and bridged by the
   remap table.
4. **Update the tooling that hardcodes the by-kind paths** (§ Frozen interfaces — tooling):
   `tools/spec_freeze_guard.py` (+ its `.opencode/plugins/spec-freeze-guard.js` twin
   docstring), `.claude/commands/{implement-plan,review-work}.md` (+ `.opencode/command/`
   twins), `.claude/settings.json` if it references the paths, and `.gitignore`.
5. **Consolidate the four per-kind folder READMEs** (`work/{specs,plans,reports,proposals}/README.md`)
   into `development/work/README.md`, preserving their durable, non-redundant content
   (§ Open decisions DP3); the per-unit folders get **no** README.
6. **Register the change:** `REGISTRY.md` row 0054, next-free bump, a new **§2d** old→new
   remap table (the fourth hop of the historical bridge), and TD rows for the tree change
   and the freeze-guard change.
7. **Living-prose updates** naming the layout: `AGENTS.md`, `CLAUDE.md`, root `README.md`,
   `policies/{naming-conventions,document-kinds,agent-workflow,review-protocol,repository-layout}.md`,
   `.github/PULL_REQUEST_TEMPLATE.md`, and any `docs/` comment paths.

## Out of scope

- **Any content, wording, tolerance, reduction-order, dependency-pin, or behavior change.**
  `uv.lock`/`constraints/` untouched; the gate baselines are unchanged (criterion 7).
- **Renumbering.** Numeric ids are preserved exactly (never compact-renumbered — same
  ruling as TD-50.1); gaps (0015–0019) stay open; ids consumed without a work folder
  (0043–0048, now `ADRs/`) are untouched.
- **The trunk-frozen architecture doc** `docs/architecture/icon-sc_architecture.md`
  (`Edit(docs/architecture/**)` denied): verified to contain **zero** `work/` path
  references, so the migration never needs to touch it.
- **Everything outside `work/`'s document layout:** `policies/` filenames, `ADRs/`,
  `references/` (incl. `lock.toml` and its historical `step` ids), `archive/`, and the
  `REGISTRY.md` §2/§2b/§2c remap tables — all keep their names and historical wording; §2d
  is *added*, the older tables are never rewritten (rewriting them would falsify the bridge,
  per TD-53.3's reasoning).
- **Widening freeze-guard coverage.** The guard keeps guarding exactly `spec.md` writes for
  frozen ids (not `plan.md`/`report.md`); only the *path shape* it matches changes. Scope
  expansion would be a separate decision.

## Frozen interfaces

The target layout is the load-bearing interface (implement exactly).

**Directory & file scheme**

| Element | Form | Notes |
|---|---|---|
| Unit folder | `development/work/<NNNN>-<kebab-slug>/` | `<NNNN>` = existing 4-digit id; `<slug>` = the unit's single existing slug (verified unique across all 43 units) |
| Lifecycle files | `proposal.md`, `spec.md`, `plan.md`, `report.md` | bare kind name; only those that exist; the id/slug live once, in the folder name |
| Artifacts | `development/work/<NNNN>-<kebab-slug>/artifacts/` | present only when the unit has artifacts; replaces the old sibling `report-<NNNN>-<kebab>/` |
| Cross-reference form | `development/work/<NNNN>-<kebab-slug>/<kind>.md` | e.g. `development/work/0005-vault-plan-t1/spec.md` |
| Branch convention | `work/NNNN-<kebab>` | **unchanged** |

**Gitignore convention (unchanged in spirit):** a unit whose `artifacts/` holds ONLY
untracked files gets its own explicit `.gitignore` line
(`development/work/0004-coupling-algebra/artifacts/`); an `artifacts/` holding a tracked
sidecar (0033) is not ignored. Untracked artifacts stay cited in their report with a
regeneration command, never a bare path.

**Tooling contract**

- `tools/spec_freeze_guard.py`: the spec-path match becomes
  `…/development/work/(\d{4})-[^/]*/spec\.md$` (and the Bash-token variant likewise); the
  id-frontier walk keys off the **unit directory name** `^(\d{4})-` instead of the four
  filename-stem prefixes. Its `advice()`/`is_frozen()` semantics, the `REGISTRY.md`
  next-free/row parsing, and **fail-open** behavior are unchanged. Net effect: it denies a
  write to a frozen unit's `<NNNN>-<slug>/spec.md` and allows the in-flight unit's; the walk
  is simpler and more robust (list `work/` subdirs, not stems across four folders).
- `.claude/commands/{implement-plan,review-work}.md` + `.opencode/command/` twins: the three
  hardcoded paths collapse to `development/work/$ARGUMENTS/{spec,plan,report}.md` (with
  `$ARGUMENTS = <NNNN>-<kebab>`, which now equals the unit folder name); the artifacts path
  becomes `development/work/$ARGUMENTS/artifacts/`.
- `.opencode/plugins/spec-freeze-guard.js`: docstring path updated (delegation unchanged).

**Allocation invariant (unchanged):** `REGISTRY.md` §1 remains the single allocator —
strictly monotonic, never reused, never backfilled. The unit-major tree makes the frontier
*trivially visible* (`ls work/` → max id + 1) and simplifies the guard's walk, but does
**not** replace the register: ad-hoc/consumed ids without a work folder still exist, so
"max folder + 1" is a convenience check, not the source of truth.

## Acceptance criteria

1. **Layout:** every current work unit resolves to `development/work/<NNNN>-<slug>/` holding
   its existing documents as bare-kind files; `git ls-files development/work/{specs,plans,reports,proposals}/`
   is empty, those four subfolders (and their READMEs) no longer exist, and
   `find development/work -type d -empty` returns nothing.
2. **Move purity:** the reorganization commit shows the file moves as renames
   (`git show --summary -M` → `R###`, count reported); the retarget commit is path-strings-only —
   `git diff --word-diff` over ≥5 frozen documents across kinds shows added/removed fragments
   that are all path strings, **no wording changes** (a wording change in frozen content is a
   MAJOR review finding).
3. **Artifacts:** `development/work/0033-structure-migration/artifacts/layout-doc-revision.diff`
   is tracked; `development/work/0004-coupling-algebra/artifacts/` is gitignored; the S04
   `slow`-marked order tests write `…/0004-coupling-algebra/artifacts/convergence_{ode,burgers}.png`
   under the slow gate (mtimes checked), proving the retargeted path is exercised.
4. **Tooling proven, not just edited:** a write to a frozen unit's `spec.md` (e.g.
   `development/work/0005-vault-plan-t1/spec.md`) is **denied** by the guard, and a write to
   the in-flight unit's `spec.md` is **allowed** (demonstrated by feeding the guard a crafted
   PreToolUse payload, or a small added test); `implement-plan`/`review-work` reference only
   `work/$ARGUMENTS/…`; `.gitignore` names the new artifacts path.
5. **Residual grep:** `grep -rInE "work/(specs|plans|reports|proposals)/"` over the repo
   (excluding `.git`, `.venv`, `docs/_build`) returns only (a) historical wording inside
   frozen documents and (b) the `REGISTRY.md` remap tables — every hit enumerated one-line in
   the report; **zero** hits in living policy/README/AGENTS/CLAUDE/command/tooling files.
6. **Register:** `REGISTRY.md` has row `0054 | work-unit-folders`, "**Next free number:
   0055**", a complete **§2d** old→new remap (verified against the filesystem: every unit ↔
   its folder), and TD rows for the tree transposition and the freeze-guard path change, each
   mirrored by a `TD-PENDING:` line in the report.
7. **No behavior change — full gate battery green with baselines identical to `main`**
   (`policies/verification-gates.md`): fast/slow/data/data-slow passed/skipped counts
   unchanged, `ruff check`/`format --check` clean, `mypy --strict -p icon_sc.core` Success,
   `lint-imports` **2 kept, 0 broken**, `sphinx-build -E -W --keep-going` exit 0;
   `git diff main -- docs/architecture constraints/ uv.lock packages/` shows only the two
   S04 test path-string lines.
8. **Report** `development/work/0054-work-unit-folders/report.md` (at its **new** path — this
   unit migrates its own files, like 0050/0051 before it) per the `document-kinds.md`
   template: the move ledger with observed counts, the retarget statistics and every
   left-byte-identical judgment call, the enumerated frozen-history residuals, dated gate
   lines, and deviations.

---

## Rationale & alternatives considered

**Why it is worth doing.** (1) *Locality* — a work unit is the atomic object of this
process; its proposal/spec/plan/report are facets of one thing, and co-locating them matches
how they are read and written (open `work/0013-diffusion-jw-l4/`, see everything). (2) *Slug
becomes single-source-of-truth* — the slug is encoded once (the folder) instead of 2–4 times
(each file), so a slug rename is one `git mv` of a folder. The 0052 `parallel→disjoint`
rename touched four files plus retargets; under this layout it is one folder. (3) *Simpler,
more robust tooling* — the freeze-guard frontier and the command files stop enumerating four
kind-folders and key off the unit directory instead, which is exactly the "next number = max
folder + 1" ergonomics the request calls out.

**The honest costs.** This is the sixth structure/naming migration (0031, 0033, 0035, 0050,
0051, 0053); each moves ~90 files, retargets ~300 path strings across frozen docs, adds a
remap hop, and runs the multi-hour gate battery. The historical bridge grows §2→§2b→§2c→§2d.
And there is one genuine ergonomic **regression**: a bare `spec.md` is context-free out of
its path — 43 identically-named `spec.md`/`report.md` files can muddy filename-fuzzy editor
navigation (mitigated by the folder path and by the freeze-guard's simpler frontier, but
real). On balance the structural wins outweigh it, and the corpus is still small (43 units /
87 files) — the migration only gets more expensive as the corpus grows, so doing it now is
strictly cheaper than deferring.

**Rejected alternatives.** (a) *Keep `<kind>-<NNNN>-<slug>.md` names inside the unit folder* —
redundant with the folder name, defeats the single-slug win. (b) *Artifacts directly in the
unit folder* (as 0004's PNGs sit in the report folder today) — would collide with the
`*.md` lifecycle files; a dedicated `artifacts/` subfolder is required. (c) *Do nothing /
defer* — legitimate given churn fatigue, but the cost grows monotonically with the corpus and
the request's ergonomic gains are real; recorded here so a future unit does not re-litigate.

## Open decisions (owner to confirm at acceptance; recommended defaults in **bold**)

- **DP1 — in-folder file names.** **`proposal.md` / `spec.md` / `plan.md` / `report.md`**
  (the request's sketch) vs. keeping the id/slug in the filename. Bold recommended.
- **DP2 — artifacts subfolder name.** **`<NNNN>-<slug>/artifacts/`** (clear intent; matches
  the existing `validation/*/artifacts/` gitignore convention and the pre-0051 `.../artifacts/`
  form) vs. `<NNNN>-<slug>/report/` (mirrors the old "named like the report file minus
  `.md`"). Bold recommended.
- **DP3 — README consolidation.** Fold the four per-kind READMEs into
  `development/work/README.md`; keep the durable bits (the lifecycle description; the plans
  README's "execution order (pending work units)" table and background-reading list; the
  reports README's slice-level / artifact-rule notes) and **drop what is now redundant with
  `REGISTRY.md` §1** (the report-to-unit mapping table). Confirm this split, or name another
  home (e.g. the execution-order table → `REGISTRY.md`).
- **DP4 — no per-unit README.** Confirm the unit folders carry only lifecycle documents +
  `artifacts/`, never a README (avoids 43 near-empty READMEs).
