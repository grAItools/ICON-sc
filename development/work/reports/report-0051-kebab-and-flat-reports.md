# Work unit 0051 — kebab-case everywhere + flat reports: execution report

**Branch:** `work/0051-kebab-and-flat-reports` · **Date:** 2026-07-15 · **State:**
executed, all gates green (dated outputs in §5)

Plan: `development/work/plans/plan-0051-kebab-and-flat-reports.md` (frozen at
assignment). Commits: C1 `d5936f4` (renames) · C2 `60f52c6` (retargets) · C2-addendum
`f1729f1` (three missed report-0004 artifact pointers, see deviation 4) · C3 `4af956f`
(ADR-0007 + REGISTRY + policy/README content; amended once, deviation 2) · C4
`bbeebb7` (living root files, commands, code strings, gitignore, conf.py; amended once
for docs/index.md, deviation 3) · C5 = this report. This report is a flat file per its
own rule (TD-51.2).

## 1. What was built — rename ledger (plan §2, commit C1)

All §2 map pairs executed as `git mv`; nothing else in C1. Purity:
`git show --summary -M100 d5936f4 | grep -cE "^ rename"` → **34**, non-`R100` → **0**.
**Count delta vs the plan headline "35":** the §2 map enumerates 34 pairs — 8 policies
+ 4 reference cards + 1 archive + 14 STATUS flattenings + 6 named-inner flattenings +
1 sidecar kebab. The headline's "21 main documents" is 20 main documents (14 + 6) plus
the sidecar; 13 + 21 = 34. Executed exactly the enumerated map; no file with an
underscore name remains under `development/` outside the gitignored
`references/local/`. Category counts: policies 8, references 4, archive 1,
STATUS→flat 14, named-inner→flat 6, sidecar kebab 1.

Before C1, the untracked S04 PNGs were relocated with plain `mv`
(`report-0004-coupling-algebra/artifacts/*.png` → `report-0004-coupling-algebra/*.png`,
empty `artifacts/` removed) and never `git add`ed (but see deviation 2). The 18
emptied report folders were removed in C1 (git leaves working-tree husks after
`git mv`; `find development -type d -empty` → empty). Survivors as artifact folders:
`report-0004-coupling-algebra/` (on disk only — holds the 2 untracked PNGs, absent
from git, ignored via the C4 per-folder line) and `report-0033-structure-migration/`
(in git — holds only the tracked sidecar `layout-doc-revision.diff`).

## 2. Retarget statistics and judgment calls (plan §3, commit C2)

C2 `60f52c6`: 29 files, 149 insertions = 149 deletions; whole-set word-diff verified —
every changed fragment is a path string per the §2 map. One over-reach caught and
reverted before commit: the `repo_layout.md` stem substring-matched the historical
`docs/architecture/symcon_repo_layout.md` (not in the map) in 9 lines across
REGISTRY/policies-README/report-0027/report-0029/report-0033 — all reverted to
underscore (that file is a docs-era name, renamed by nobody).

**Folder-reference vs file-reference calls** (plan §3: a folder reference that meant
the document points at the file; one that means artifacts keeps the folder form):

- Pointed at the flat FILE: `report-0032:16` (its own "where this document lives"
  location), `report-0029:356` (untouchables-table row naming the 0027 document),
  `report-0029:9,561` (its own location), all `…/STATUS.md`, `…/REPORT.md`, and
  named-inner-document paths everywhere retargeted (REGISTRY §3 source cells,
  plans 0020/0023/0025/0028 source-material pointers, ADR-0003/0004 pointers,
  reports/README index, plan-0033/0035 deliverable lines + §8 headings).
- Kept the FOLDER form: REGISTRY §2b rows (historical map, untouched);
  `report-0029:256` ("subdir, no suffix" — the folder shape is the analysis
  subject); `plan-0050:169` (era-bound instruction quoting what conf.py should say
  post-0050); `report-0049:82` (exempt analysis); TD-33.4's diff-artifact path keeps
  `report-0033-structure-migration/` as the (real) artifacts folder, inner file
  kebab-cased.
- Artifacts-path class: `report-0050:216` (§7 live artifact pointer) retargeted to
  the new PNG location; `report-0050:146` (dated quoted gate line naming the old
  artifacts path) left verbatim; `report-0029:62,376` (analysis rows describing the
  test-code runtime path, previously retargeted by 0050 → pointer class) follow the
  C4 code change (drop `/artifacts`); `report-0004:115,169,170` — missed in C2,
  fixed in the addendum `f1729f1` (deviation 4).

**Left byte-identical:** `report-0034-naming-iteration.md`,
`report-0049-work-structure-iteration.md` (both analyses — 0050 precedent),
`report-0035-naming-migration.md` (only own-ledger/quote hits remained),
`report-0033-structure-migration/layout-doc-revision.diff` (owner-applied artifact,
TD-33.4 — renamed, content untouched), `plan-0051` (self; its §2 map is exempt and
the rest was born kebab), REGISTRY §2/§2b tables, `lock.toml`, `docs/architecture/`.

**Frozen-plan per-line classes (0050's classification carried forward):** plan-0033 —
retargeted the deliverable line (9), diff-artifact path (306), §7/§8/§9 pointers to
living policies and templates (352, 376, 378, 385, 393, 398, 399); left the §5
policy-creation table (115–121), §5 item instructions (235, 237, 240–241, 254, 259,
284–285), move-map rows (157, 163, 202, 210), quoted commands, and all
`symcon_repo_layout` docs-era mentions. plan-0035 — retargeted 7, 218, 240, 246; left
its §3 map and §5/§6 instruction quotes. plan-0050 — retargeted 204, 208 (template and
protocol pointers); left its own maps, §5/§6 instruction lists, and ledger vocabulary.
report-0033 — all hits were pointer-class (plan_tree_map narrative, artifact paths,
policy pointers) and retargeted; its §-map rows and quoted gate lines contain only
pre-035 paths and stayed untouched by construction. report-0050 — only §7 retargeted
(above); ledger/judgment/quote narrative left. REGISTRY — source cells and
previously-retargeted decision-text paths (TD-29.3's archive map, TD-33.4's artifact,
bare `27_docs_plan.md`/`29_plan_structure.md` source stems) retargeted; TD-35.2's
decision text (`policies/repo_layout.md` as the 035 move target) left verbatim
(TD-33.3 era-bound-outcome class); TD decision texts otherwise untouched.
ADR-0006:40 (its own `records_and_liveness.md → policies/document_kinds.md` decision
text) left — era-defining, by-design residual.

## 3. New content (plan §4–§5, commits C3–C4)

C3 `4af956f` (19 files, +171/−60): `ADRs/0007-kebab-everywhere-flat-reports.md`
(Nygard, 50 lines — everything traces to the plan preamble's owner mandate of
2026-07-15 and ADR-0006); ADR-0006 `Status:` → the plan §4.1 sentence verbatim;
`ADRs/README.md` index 0000–0007, next free 0008, 0006 status mirrored. REGISTRY: row
0051 → "this work unit"; next free 0052 (was already allocated at assignment); new
**§2c** complete 0051 remap table (34 pairs; the 14 STATUS rows compressed to one
rule-row in house style) + the untracked-PNG relocation row; TD-51.1/TD-51.2 rows
(pending, Date "(merge)"). Policies: `naming-conventions.md` (kebab-everywhere rule,
flat-report + artifacts-folder + per-folder-gitignore rules, case-split section
dropped, history clause extended to §2c), `document-kinds.md` (report rows and the §2
template restated for the flat shape; generated-artifact row on per-folder ignores),
`repo-layout.md` (reports tree node redrawn). READMEs: `development/README.md`
(naming-convention section, reports table row), `work/README.md` (shape),
`work/reports/README.md` (shape explanation; index was retargeted in C2),
`archive/README.md` (case note, deviation 6). H1 self-names of the 7 renamed policies
and 4 reference cards updated to kebab (deviation 5); `review-protocol.md` H1 names no
file; archive map H1 untouched (dead).

C4 `bbeebb7` (12 files): AGENTS.md (3 policy paths + report-shape sentence); PR
template (report-shape line); `implement-plan`/`review-work` commands (.claude +
.opencode twins): deliverable `report-$ARGUMENTS.md`, artifacts (if any) in
`report-$ARGUMENTS/`, kebab policy paths; code path strings exactly per §5.3
(`test_order_ode.py:9,103`, `test_order_burgers.py:89`, `s05_dispatch.py:4`,
`jw_step.py:4`); `.gitignore:32` blanket `*/artifacts/` glob → explicit
`development/work/reports/report-0004-coupling-algebra/`; `docs/conf.py:2`;
`docs/index.md:49` (deviation 3). CLAUDE.md and root README needed no edits (no old
names; verified by grep).

## 4. Tolerances & sign-off flags

No tolerances touched; no reduction-order changes; no dependency edits. Owner at
merge: fill TD-51.1/TD-51.2 dates/evidence; flip REGISTRY row 0051 to executed.

## 5. Gates (dated 2026-07-15 CEST; logs `/tmp/gate0051_*.log` with `EXIT:` sentinels)

- fast (`not gpu and not slow`): `739 passed, 1 skipped, 143 deselected, 51 warnings
  in 664.72s (0:11:04)`, EXIT:0 (10:37, /tmp/gate0051_fast.log; skip = mpi opt-in).
- slow-no-data: `31 passed, 852 deselected, 5 warnings in 523.34s (0:08:43)`, EXIT:0
  (10:46, /tmp/gate0051_slow.log). The S04 order tests wrote
  `development/work/reports/report-0004-coupling-algebra/convergence_{burgers,ode}.png`
  at 10:37 — the NEW flat location is exercised (mtimes checked before 07:59 → after
  10:37; no `artifacts/` subdir was recreated).
- data-not-slow: `43 passed, 840 deselected, 11 warnings in 517.37s (0:08:37)`,
  EXIT:0 (10:54, /tmp/gate0051_data.log).
- data-slow: `76 passed, 1 skipped, 806 deselected, 28 warnings in 2134.47s
  (0:35:34)`, EXIT:0 (11:30, /tmp/gate0051_dataslow.log; skip = upstream MCH-only
  diffusion).
- ruff check / format: `All checks passed!` / `173 files already formatted` (10:25).
- mypy: `Success: no issues found in 50 source files`; lint-imports:
  `Contracts: 2 kept, 0 broken.` (10:25).
- sphinx `-E -W --keep-going`: `build succeeded.`, EXIT:0 (10:26,
  /tmp/gate0051_sphinx.log).
- Link check (033 §7.2 script): 0 BROKEN (10:24). Husk check:
  `find development -type d -empty` → empty. lock.toml: **completely untouched**
  (`git diff main -- development/references/lock.toml` empty), parses at 51 `[[ref]]`
  entries. Untouchables: `git diff main -- docs/architecture constraints/ uv.lock`
  empty; `packages/` + `benchmarks/` diff = exactly the §5.3 lines (4 files, 5=5);
  `git status --porcelain` clean after C5.

### §6 residual greps — by-design hits, enumerated (10:23–10:24)

Grep 1 (`development/(policies|references)/<snake>.md`):
- `development/REGISTRY.md:141` — §2 remap-table row (historical bridge).
- `development/REGISTRY.md:265` — TD-35.2 decision text (era-bound outcome, kept verbatim).
- `plan-0035-naming-migration.md:25,105,118,134` — 035's own move map/instructions.
- `plan-0033-structure-migration.md:163,202` — move-map rows; `:284` — §5 instruction.
- `plan-0050-work-tree-migration.md:84` — 0050's own map line.
- `report-0034-naming-iteration.md:16,58` — exempt analysis.
- (docs/index.md:49 was a genuine miss, fixed in C4 — deviation 3.)

Grep 2 (`report-NNNN-…/(STATUS|REPORT|NN_)`):
- `development/REGISTRY.md:205–210` — §2c remap table (this migration's bridge).
- `plan-0051:44–50,125,127` — this plan's §2/§5 map.
- `plan-0050:166–167` — 0050's §6 code-string instructions (era-bound).
- `report-0029-plan-structure.md:256` — folder-shape contrast kept (judgment call §2).
- `report-0050-work-tree-migration.md:35` — 0050's judgment-call narrative.

Grep 3 (`plan_tree_map|layout_doc_revision`):
- `plan-0051:40,53` — this plan's map. `REGISTRY:164` (§2b), `:203,211` (§2c).
- `plan-0033:78,157,210,254` — its own map/instructions.
- `report-0035:20,31,122` and `report-0050:38,73,179` — own ledgers/narratives.

Grep 4 (`artifacts/` over .gitignore + reports + core tests):
- `.gitignore:42,45` — validation artifact globs (out of scope, untouched).
- `report-0033:77–78,113` — §-map rows and dated quoted gate line (pre-035 paths).
- `report-0050:23,105,146` — own ledger, quoted gitignore glob, quoted gate line.
- `report-0029:92–93,189,266,303` — records-era quotes left by 0050, still historical.
- `report-0035:104` — 035-era narrative path.
- `report-0005:230`, `report-0010:72,181`, `report-0013:48`, `report-0014:205`,
  `report-0027:505` — prose/validation paths, not report-artifact paths.
- `report-0049:82,123` — exempt analysis.
- `packages/symcon-core/tests/`: no hits (C4 retargeted both files).

## 6. Deviations

1. **C1 count 34, not 35.** The plan's §2 map enumerates 34 pairs; the headline "35"
   double-counts (its "21 main documents" = 20 documents + 1 sidecar). Executed the
   enumerated map exactly; nothing snake-cased remains (verified by `find`).
2. **C3 briefly staged the untracked S04 PNGs** (`git add -A development/`), violating
   the never-`git add` instruction; caught on the same commit's status output,
   removed with `git rm --cached`, and the commit amended before any further step —
   final C3 `4af956f` contains no PNGs (`git show --stat` verified); the files
   remained on disk untracked throughout; nothing was pushed.
3. **docs/index.md:49** (living published-site file) cited
   `policies/repo_layout.md` — not in plan §5's explicit C4 list but a genuine
   reference caught by §6 grep 1; retargeted and amended into C4 `bbeebb7`.
4. **report-0004's three live artifact pointers** (lines 115/169/170) were missed by
   the C2 sweep (surfaced by §6 grep 4); fixed as the dedicated addendum commit
   `f1729f1` (path strings only, word-diff verified) rather than folded into C3–C5.
5. **H1 self-names** of the renamed living policies and reference cards updated to
   kebab in C3 — beyond §4.3's "path updates only" for other policies, treated as
   filename-string class (a stale `# agent_workflow` H1 contradicts TD-51.1 in a
   living file); frozen/dead files' H1s untouched.
6. **archive/README.md** amended ("dying names, kebab-cased (scheme-exempt, ADR-0006;
   case rule TD-51.1, ADR-0007)") — §4.4 only required an edit "if it names the map
   file" (it does not), but the unqualified "naming-exempt" claim contradicted
   TD-51.1.
7. **REGISTRY row 0051** existed at assignment as "pending (plan …)"; updated to
   "this work unit" (0050-row precedent) instead of allocating a new row.
8. C3 and C4 were each amended once (deviations 2–3) before gating and before C5; no
   history rewrite touched C1/C2.

## 7. Follow-ups

- **F1 (inherits 0050's F1):** unexecuted plans 0020–0025/0030 still carry 035-scheme
  output paths (`development/records/0NN_*_record*`), to be restated at execution
  time; their *source-material* pointers now read the flat 0051 names.
- **F2 (inherits 0050's F2):** the ~86 `REFERENCES.lock` provenance-comment mentions
  under `packages/`/`validation/`/`benchmarks/` remain outside any sanction list;
  bridged by the lock header note and REGISTRY §2b.
- The four gate partitions plus sphinx/ruff/mypy/lint-imports are the standing
  battery; no baseline count changed (this unit adds no tests and no `.py` files).

## 8. Artifacts

None generated by this work unit. The relocated S04 PNGs
(`development/work/reports/report-0004-coupling-algebra/convergence_{ode,burgers}.png`,
untracked, per-folder gitignore) belong to work unit 0004 — regenerate with
`uv run pytest packages/symcon-core/tests/test_order_ode.py packages/symcon-core/tests/test_order_burgers.py -m "slow" -q`.
