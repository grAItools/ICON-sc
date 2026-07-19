# Work unit 0054 — per-work-unit folders (transpose `work/` to by-unit)

**Branch:** `claude/reorganize-work-folder-w0gpge` (this engagement's branch — verify with
`git branch --show-current` before every commit). **Not** `work/0054-work-unit-folders`
(the name the project convention would use); this task is pinned to the existing branch, no
new branch, **no push** (the orchestrator pushes).

**Deliverable:** the migration + the report
`development/work/0054-work-unit-folders/report.md` (written at its NEW path — 0054 migrates
its own files, like 0050/0051 before it).

Frozen at assignment. Implements `development/work/specs/spec-0054-work-unit-folders.md`
exactly (its Frozen interfaces + Acceptance criteria are binding; its Open decisions are
taken at the **bold recommended defaults**: DP1 bare-kind filenames, DP2
`<unit>/artifacts/`, DP3 consolidate the four per-kind READMEs into `work/README.md`, DP4 no
per-unit README). On any conflict with reality: stop, record it, resolve only the
mechanical-and-obvious.

## 1. The agreed decisions (binding)

1. Every work unit's documents move into one folder `development/work/<NNNN>-<kebab-slug>/`,
   renamed to bare kind: `proposal.md` / `spec.md` / `plan.md` / `report.md` (only those
   that exist). The `<NNNN>` and `<slug>` are the unit's existing id and its single existing
   slug (verified unique across all units). **44 units today** (0000–0054 with the standing
   gaps), **89 tracked files** after this plan file lands (`git ls-files development/work`
   — verify the live count before C1 and record it).
2. Report artifacts move into a per-unit `artifacts/` subfolder. Exactly two exist:
   `report-0033-structure-migration/layout-doc-revision.diff` (tracked) →
   `0033-structure-migration/artifacts/layout-doc-revision.diff`;
   `report-0004-coupling-algebra/` (untracked PNGs) → `0004-coupling-algebra/artifacts/`.
3. The four per-kind subfolders `work/{proposals,specs,plans,reports}/` and their four
   `README.md`s are removed; the READMEs' durable content consolidates into
   `development/work/README.md` (§5). No per-unit READMEs.
4. `REGISTRY.md` stays the single allocator; it gains a **§2d** old→new remap table (the
   fourth hop of the historical bridge). The older tables (§2/§2b/§2c) are never rewritten.
5. The lifecycle vocabulary, the four-digit ids, the never-reuse/never-backfill rule, and
   all document content are unchanged. **No behavior change** (gate baselines identical).

## 2. Hard rules (restated)

- `git branch --show-current` == `claude/reorganize-work-folder-w0gpge` before every commit.
  Never commit to `main`; **never `git push`**; end every commit message with the
  `Co-Authored-By:` / `Claude-Session:` trailer supplied by the orchestrator.
- No data, no dependency-pin changes, no tolerance/reduction-order/assertion/marker changes.
  `constraints/`, `uv.lock`, `docs/architecture/*` untouched (the architecture doc has **zero**
  `work/` path refs — verified — so it never needs touching; it is `Edit`-denied anyway).
- **Frozen documents:** path-string retargets only, isolated in commit C2, verified by
  `git diff --word-diff` (ADR-0001 content-frozen rule; same discipline as 0050/0051). No
  wording changes. Evaluations whose subject *is* the path layout are left byte-identical and
  bridged by §2d (enumerated in §4).
- **★ Freeze-guard handling (load-bearing).** `tools/spec_freeze_guard.py` is a live
  PreToolUse hook re-executed on every tool call; it DENIES any `git mv`/`Write`/`Edit` whose
  token is a frozen `spec-NNNN-*.md` path — at the OLD source path now, and at the NEW
  `<unit>/spec.md` destination once its regex is updated (units 0001–0053 are all frozen). Per
  the guard's own docstring ("for a sanctioned migration, disable this guard deliberately"),
  neutralize it for the mechanical phase:
  1. **Before any spec move**, edit `tools/spec_freeze_guard.py` to short-circuit — insert
     `return None` as the first statement of `_decide()` (the hook re-reads the script each
     call, so this takes effect immediately; editing the guard is itself allowed — its target
     is not a spec path). Keep this edit **unstaged** throughout C1–C3 (commit with explicit
     `git add <paths>` + `git commit`, never `git add -A`/`-u`, so the neuter is **never
     committed** — no commit ever contains a disabled guard).
  2. Perform C1 (moves) and C2 (retargets, which write to frozen `spec.md` files) with the
     guard neutered.
  3. In **C4**, discard the transient neuter and rewrite the guard to its final new-path
     logic (§6.1); `git add tools/spec_freeze_guard.py`; commit.
  4. **Prove** post-restore (record the outputs in the report): a crafted PreToolUse payload
     for a frozen unit is DENIED and the in-flight unit is ALLOWED —
     ```
     echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/development/work/0005-vault-plan-t1/spec.md"}}' | python3 tools/spec_freeze_guard.py   # → deny JSON
     echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/development/work/0054-work-unit-folders/spec.md"}}' | python3 tools/spec_freeze_guard.py   # → silent (allow)
     ```
  Record the whole maneuver in the report; it is TD-54.2.

## 3. Rename map (commit C1 — `git mv` only)

Slug rule: the slug is already kebab; the folder is `<NNNN>-<slug>`, the file is the bare
kind. Verify every target. **Uniform bulk (rule-rows):**

- `work/specs/spec-<NNNN>-<slug>.md` → `work/<NNNN>-<slug>/spec.md` (all specs)
- `work/plans/plan-<NNNN>-<slug>.md` → `work/<NNNN>-<slug>/plan.md` (all plans)
- `work/reports/report-<NNNN>-<slug>.md` → `work/<NNNN>-<slug>/report.md` (all flat reports)
- `work/proposals/proposal-<NNNN>-<slug>.md` → `work/<NNNN>-<slug>/proposal.md` (all proposals)

**Non-uniform (enumerate explicitly):**

- `work/reports/report-0033-structure-migration/layout-doc-revision.diff` →
  `work/0033-structure-migration/artifacts/layout-doc-revision.diff` (tracked sidecar; the
  `report-0033-structure-migration.md` flat file → `0033-structure-migration/report.md`).
- `work/reports/report-0004-coupling-algebra/` (untracked PNGs, gitignored) →
  `work/0004-coupling-algebra/artifacts/` (plain `mv`, not `git mv` — untracked; the flat
  `report-0004-coupling-algebra.md` → `0004-coupling-algebra/report.md` via `git mv`).
- `work/{proposals,specs,plans,reports}/README.md` (4 files) → **removed** (`git rm`; content
  consolidated in C3, §5). Not moved.

The mechanical way: a script that, for each tracked file under `work/{specs,plans,reports,
proposals}/` matching `<kind>-<NNNN>-<slug>.(md|…)`, computes `dest=work/<NNNN>-<slug>/<kind>.<ext>`
(with the two artifact special-cases and the four README removals), `mkdir -p` the unit dir,
`git mv src dest`. Generate, print, and eyeball the full list before running it.

**C1 purity:** `git show --summary -M100 HEAD | grep -cE "^ rename"` equals the moved-file
count (record it, reconcile against the §3 rules + the 4 README removals which show as
deletes); zero non-`R100`/non-delete lines except the 4 README `delete`s; the untracked 0004
PNGs travel by plain `mv`; `find development/work -type d -empty` returns nothing (old
`{specs,plans,reports,proposals}/` husks removed).

## 4. Path retargeting (commit C2 — path strings only)

Re-measure first: `grep -rInE "work/(specs|plans|reports|proposals)/" . --exclude-dir=.git
--exclude-dir=.venv --exclude-dir=docs/_build` (≈296 lines / ≈60 files at authoring). The
old→new string map, applied as full-path and bare-stem replacements generated from the C1
map:

| Old form | New form |
|---|---|
| `development/work/specs/spec-<NNNN>-<slug>.md` | `development/work/<NNNN>-<slug>/spec.md` |
| `development/work/plans/plan-<NNNN>-<slug>.md` | `development/work/<NNNN>-<slug>/plan.md` |
| `development/work/reports/report-<NNNN>-<slug>.md` | `development/work/<NNNN>-<slug>/report.md` |
| `development/work/proposals/proposal-<NNNN>-<slug>.md` | `development/work/<NNNN>-<slug>/proposal.md` |
| `development/work/reports/report-<NNNN>-<slug>/` (artifacts) | `development/work/<NNNN>-<slug>/artifacts/` |
| bare stem `spec-<NNNN>-<slug>.md` (and plan-/report-/proposal-) | `<NNNN>-<slug>/spec.md` (resp. plan/report/proposal) |

- **Living files → real edits** (14 + the tree-drawing docs): `AGENTS.md`, `CLAUDE.md`, root
  `README.md`, `development/README.md`, `development/work/README.md`,
  `development/policies/{agent-workflow,docs-boundary,review-protocol,naming-conventions,document-kinds,repository-layout}.md`,
  `.github/PULL_REQUEST_TEMPLATE.md`, and the command/plugin files (done in C4, §6). Prose
  like "the spec `spec-0005-vault-plan-t1.md`" — the filename IS a path string; retarget it;
  the surrounding rule wording stays.
- **Frozen files → mechanical path-string retargets only**, verified `git diff --word-diff`.
  Old→new per the table. Every added fragment a new path, every removed fragment an old path.
- **Left byte-identical (self-exempt; §2d bridges them)** — same judgment class as the 0050
  record §2: `development/work/0049-work-structure-iteration/report.md` (its subject is the
  *previous* work/ layout analysis; retargets would falsify it — leave, except any pointer
  already treated as a live path by prior migrations), the REGISTRY §2/§2b/§2c tables
  (historical bridge — §2d is *added*, not applied to them), and the tracked
  `0033-structure-migration/artifacts/layout-doc-revision.diff` (owner-applied artifact,
  TD-33.4). Enumerate every left-alone file in the report with a one-line reason.
- **Never touch:** `icon_sc/**` source import paths; `development/references/lock.toml`
  entries; `docs/architecture/*`; the §3 map inside THIS plan; `constraints/`, `uv.lock`.

**C2 staging:** `git add` exactly the retargeted files (NOT `tools/spec_freeze_guard.py` — it
stays neutered/unstaged until C4). Purity: word-diff over the staged set = path strings only.

## 5. New / restructured content (commit C3)

1. **`development/work/README.md`** rewritten to describe the by-unit tree and absorb the four
   removed per-kind READMEs' durable content: the lifecycle (proposal → spec → plan → report),
   the naming (`<NNNN>-<slug>/<kind>.md`, artifacts subfolder, gitignore convention), the
   plans-README "execution order (pending work units)" table + "background reading" list, and
   the reports-README artifact-reference rule + slice-level notes. **Drop** the reports-README
   report-to-unit table (now redundant with `REGISTRY.md` §1). Keep ≤ its current footprint.
2. **`REGISTRY.md`** (living): flip row 0054 kinds `spec` → `spec + plan + report`, status
   `pending` → `this work unit` (owner sets `executed` at merge). Add a note on §2c that its
   "New" column resolves onward via **§2d**. Add **§2d — remap (work 0054): by-kind →
   by-unit**, house style of §2b/§2c: compress the four uniform series into rule-rows
   (`work/specs/spec-<NNNN>-<slug>.md → work/<NNNN>-<slug>/spec.md`, etc.), enumerate the
   non-uniform (the two artifact folders; the four removed READMEs). Decision register: add
   **TD-54.1** (by-unit tree transposition; source spec-0054) and **TD-54.2** (freeze-guard
   path-shape change + the sanctioned migration-time neuter), both `pending`, Date "(merge)",
   each mirrored by a `TD-PENDING:` line in the report.
3. **Tree-drawing living docs** updated to the by-unit tree: `development/README.md`,
   `development/policies/repository-layout.md`, and any policy diagram
   (`document-kinds.md` kinds-table "Where" cells, `naming-conventions.md` scheme text).

## 6. Living-file & tooling edits (commit C4)

1. **`tools/spec_freeze_guard.py`** — final new-path logic (discard the C2-era neuter):
   - `_SPEC_PATH_RE` → `re.compile(r"/development/work/(\d{4})-[^/]*/spec\.md$")`.
   - `_SPEC_TOKEN_RE` → `re.compile(r"[\w./-]*development/work/(\d{4})-[^/\s]*/spec\.md")`.
   - `_ID_RE` → `re.compile(r"^(\d{4})-")` (now matches the unit **directory** name; the
     `_Frontier` walk keys the id off dir names, not the four filename stems — the simpler,
     more robust frontier the spec promised).
   - **Unchanged:** `is_frozen`/`advice`/`_ROW_RE`/`_NEXTFREE_RE`/REGISTRY parsing, the
     `_MUTATING` set, Bash redirection detection, **fail-open** `main()`, and the
     spec-only scope (do NOT guard `plan.md`/`report.md`). Update the module docstring's one
     path example. This is a path-shape change only — the frozen-id invariant it enforces is
     identical.
   - Verification: the two crafted-payload checks in §2 (deny 0005 / allow 0054), plus a
     below-frontier gap check (e.g. 0015) DENY. Recorded in the report — **not** added as a
     gate-collected pytest (keeps the fast baseline at 696; a `tools/`-level check may be
     added but must stay outside `pytest packages`).
2. **`.opencode/plugins/spec-freeze-guard.js`** — docstring path example
   `development/work/specs/spec-NNNN-*.md` → `development/work/<NNNN>-<slug>/spec.md`
   (delegation to the Python script is unchanged).
3. **Command files** — `.claude/commands/{implement-plan,review-work}.md` + the byte-identical
   `.opencode/command/` twins: the per-kind paths collapse to
   `development/work/$ARGUMENTS/spec.md`, `…/plan.md`, `…/report.md`, artifacts
   `development/work/$ARGUMENTS/artifacts/` (`$ARGUMENTS` = `<NNNN>-<kebab>` = the unit folder).
4. **`.gitignore`** — `development/work/reports/report-0004-coupling-algebra/` →
   `development/work/0004-coupling-algebra/artifacts/`.
5. **Code/doc path strings (exactly these six sites):**
   `packages/icon-sc-core/tests/test_order_ode.py:9,103` and
   `packages/icon-sc-core/tests/test_order_burgers.py:89` →
   `development/work/0004-coupling-algebra/artifacts` (the S04 artifact-write path — this is
   the one exercised by the slow gate); `benchmarks/s05_dispatch.py:4` →
   `development/work/0005-vault-plan-t1/report.md`; `benchmarks/dispatch_overhead/jw_step.py:4`
   → `development/work/0014-plan-through-dycore/report.md`; `docs/conf.py:2` →
   `development/work/0027-docs-plan/report.md`. Nothing else under `packages/`/`benchmarks/`/`docs/`.

## 7. Commit sequence and gates

C1 renames → C2 retargets → C3 content → C4 living/tooling → C5 report. Purity checks per
§3/§4. Guard neuter unstaged across C1–C3, finalized in C4 (§2).

**Gates** — full battery, `uv run python tools/run_gate.py` (or the eight commands in
`verification-gates.md` split by marker if a partition exceeds the shell limit). Baselines
(must match exactly — no behavior change): fast **696 passed, 1 skipped**; slow **31**; data
**43**; data+slow **76 passed, 1 skipped**; `ruff check` clean; `ruff format --check`
**175 files**; `mypy --strict -p icon_sc.core` **50 source files**; `lint-imports`
**2 kept, 0 broken**; `sphinx-build -E -W --keep-going` exit 0. The S04 `slow` order tests
(`test_order_ode.py`/`test_order_burgers.py`) must write
`…/0004-coupling-algebra/artifacts/convergence_{ode,burgers}.png` — check mtimes before/after
the slow partition to prove the retargeted path is live. Long partitions: detached logs with
`EXIT:` sentinels, actively polled — never idle-wait.

**Untouchables:** `git diff main -- docs/architecture constraints/ uv.lock packages/` = only
the three S04 path-string lines. **Residual greps** (each: zero hits outside frozen by-design
+ this plan + REGISTRY remap tables; enumerate every by-design hit in the report):

```bash
grep -rInE "work/(specs|plans|reports|proposals)/" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=docs/_build
grep -rInE "(spec|plan|report|proposal)-[0-9]{4}-" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=docs/_build   # bare stems; hits only in frozen docs + §2/§2b/§2c/§2d + this plan
find development/work -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]-*' | wc -l   # == unit count
```

Plus: `find development/work -type d -empty` empty; the guard proofs (§2); the
`spec_freeze_guard.py` self-test that `_Frontier` still reads the register (advice == next
free). No `-x`/`--ignore`/`-k`/marker games.

## 8. Report — `development/work/0054-work-unit-folders/report.md`

Per the `document-kinds.md` template (header Branch/Date/State; §1 What was built = rename
ledger with observed counts; §2 retarget stats + every left-byte-identical judgment call; §3
deviations; §4 tolerances/sign-off (`TD-PENDING:` for TD-54.1/54.2); §5 dated gate lines; §6
follow-ups; §7 artifacts). Enumerate every by-design residual grep hit one line each. Declare
the freeze-guard neuter/restore maneuver and quote the deny/allow proofs.

## 9. Review checklist (fresh reviewer; protocol `development/policies/review-protocol.md`)

1. **C1 purity:** observed `R100` count reconciles with §3 (the four README `delete`s are the
   only non-renames); `find development/work -type d -empty` empty; every unit folder holds
   only the docs that existed pre-migration (spot-check ≥5 units incl. 0000 report-only, 0020
   plan-only, 0037 proposal-only, 0005 spec+plan+report, 0052 all-four).
2. **C2 purity:** `git diff --word-diff` over ≥5 frozen docs across kinds shows path strings
   only — any wording change in frozen content is a **MAJOR** finding. The left-byte-identical
   set (§4) is genuinely unchanged (`git diff` empty on those blobs).
3. **Artifacts:** `0033-structure-migration/artifacts/layout-doc-revision.diff` tracked;
   `0004-coupling-algebra/artifacts/` gitignored; the slow gate wrote the two PNGs there
   (mtimes).
4. **Guard proven, not just edited:** run the §2 crafted payloads yourself — frozen 0005 (and
   a gap id) DENIED, in-flight 0054 ALLOWED; confirm the guard is enforcing at HEAD (no neuter
   committed: `git log -p -- tools/spec_freeze_guard.py` shows only the final new-path logic);
   `_ID_RE`/`_SPEC_PATH_RE` are the new shapes; scope still spec-only.
5. **Residual greps** (§7) return only by-design hits; **REGISTRY §2d** complete vs the
   filesystem (every unit folder ↔ a §2d rule/row); TD-54.1/54.2 present + `TD-PENDING:`
   mirrored; row 0054 updated.
6. **Full gate battery re-run by you** — counts exactly at baseline (696/1 · 31 · 43 · 76/1 ·
   ruff · mypy 50 · lint-imports 2/0 · sphinx); untouchables diff = only the three S04 lines.
7. **Report honesty** — deviations declared; the guard maneuver declared; every left-alone
   frozen file listed with a reason.

Verdict `approve`/`request-changes`; findings MAJOR→MINOR→INFO with `file:line` evidence.
