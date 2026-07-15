# Work unit 0050 — `development/work/` migration: execution report

**Branch:** `work/0050-work-tree-migration` · **Date:** 2026-07-15 · **State:** executed,
all gates green (dated outputs in §5)

Plan: `development/work/plans/plan-0050-work-tree-migration.md` (frozen at assignment;
first document born under the convention it implements). Commits: C1 `ffd129c` (renames)
· C2 `fd1f38d` (retargets) · C3 `3f377d2` (new/restructured content) · C4 `9084882`
(living root files, tooling, code strings, lock header) · C5 = this report. Execution
was interrupted once mid-C2 (credit limit) and resumed on the same working tree; the
uncommitted C2 state was verified by full word-diff before the C2 commit.

## 1. What was built — rename ledger (plan §3, commit C1)

All §3 bullets executed as `git mv`; nothing else in C1. Purity:
`git show --summary -M100 ffd129c | grep -cE "^ rename"` → **84** (plan expected 84;
pre-flight `git ls-files` count of the §3 set was also 84 — no counting artifact this
time); non-`R100` lines → **0**; `find development -type d -empty` → empty (source-dir
husks removed in the same commit). Category counts: specs 15, plans 25,
records→work/reports 28 (27 items; the 033 folder holds two tracked files), ideas→
work/proposals 7, adr→ADRs 7 (Nygard remap 043→0000 … 048→0005), root 2
(`REFERENCES.lock` → `references/lock.toml`, `records_and_liveness.md` →
`document_kinds.md`). The untracked S04 `artifacts/` PNGs traveled with the folder mv.
Post-move TOML validation: `tomli` parse of `development/references/lock.toml` → 51
`[[ref]]` entries.

## 2. Acceptance criteria → retarget statistics and judgment calls (plan §4, commit C2)

64 files, 269 insertions = 269 deletions; word-diff verified over the full set — every
added fragment is a new-scheme path string, every removed fragment an old path/citation.
Rules: per-file full-path + bare-stem replacements generated from the C1 map, applied to
every `.md`/`.diff` under `development/` plus AGENTS.md/CLAUDE.md/README.md, with the
exempt set excluded and over-reaches reverted by hand. Judgment calls:

- **Left byte-identical:** `report-0034-naming-iteration/34_naming_iteration.md` (the
  naming analysis — 035 precedent), `report-0049-work-structure-iteration.md` (the
  document IS this migration's old→new analysis; retargets would falsify it),
  `report-0033-structure-migration/layout_doc_revision.diff` (owner-applied artifact,
  TD-33.4), the REGISTRY §2 remap table (historical bridge — §2b added in C3 instead).
- **plan-0050 (this plan):** 1 pointer retargeted (line 10, "Implements …
  report-0049-work-structure-iteration.md"); its §1 decisions, §3 map, §4–§7
  instructions and grep patterns left (self-exempt per §4).
- **plan-0035:** 2 pointers retargeted (deliverable line 7, §8 heading); its §3 map,
  §5–§6 instruction quotes, and `REFERENCES.lock` hard-rule/untouchables lines left as
  035-era meaning. **report-0035/REPORT.md:** 1 pointer retargeted (line 6 plan
  pointer); quoted gate lines (old S04 artifacts path), quoted globs, and the §2
  judgment-call narrative filenames left — verbatim quotes stay verbatim.
- **plan-0033:** kept retargeted — deliverable line, diff-artifact path, §8 heading (the
  three 035-identified pointers), the `document_kinds.md` template pointers in §8/§9,
  and `REFERENCES.lock` rule-prose (lines 69, 247–248, 401; plan-0050 §4's "append to
  …" class). Reverted to historical — §5.1 move-map rows (165/171/204), the §5
  policy-creation table rows (116, 119), the §3.3 register-survives instruction (39),
  the target-tree row "`REFERENCES.lock` root, UNCHANGED" (46), the §7 quoted
  untouchables command (394), the living-docs parenthetical (221), and the §5 items-5/6
  rewrite headings (256/264) — all era-bound map/instruction meaning (ADR-0001 class).
- **report-0033/REPORT.md:** kept — plan pointer, `lock:471` file:line cite, artifact
  path, `document_kinds.md` phrase pointer (219); reverted — quoted untouchables
  command (133), "Task-register (`development/plans/README.md`)" era claim (144).
- **report-0032 evaluation:** all 8 `REFERENCES.lock` analysis mentions reverted (§2.7's
  subject is precisely the lock's root-vs-`references/` location; retargeting destroys
  the contrast) and all 3 `records_and_liveness.md` creation-proposal mentions reverted;
  other path pointers kept retargeted (rows the 033/035 migrations already treated as
  pointers). **report-0029:** kinds-table "Where" cells kept retargeted (prior
  migrations retargeted the same cells); the §1 inventory row `REFERENCES.lock | 472`
  reverted (bare-filename inventory class, 035 record §2).
- **ADRs (frozen):** pointers to the 034/027/026 sources kept retargeted; ADR-0000's
  "task-number register survives as `development/plans/README.md`" reverted (era-bound
  outcome claim, same class as its "renamed `development/DECISIONS.md`" kept historical
  by 035).
- **REGISTRY (living):** Source-cell paths and `adr 04N`→`ADR-000N` citations
  retargeted (§1 header line, TD-33.x/35.1 Source cells); TD decision texts left
  verbatim (TD-35.1's "`adr NNN`", TD-35.4/35.5 glob quotes, TD-33.3's `DECISIONS.md`);
  §2 table untouched. **archive/plan_tree_map.md:** path retargets applied (archive
  paths were retargeted by 035 too), analysis wording untouched.
- **Fix within C2:** `development/README.md:50` bare-rule artifact
  `records/report-0000-overview.md` corrected to `work/reports/report-0000-overview.md`.

## 3. New/restructured content (plan §5–§6, commits C3–C4)

C3 (19 files, +374/−224): `ADRs/0006-work-tree-and-kind-prefixed-names.md` (Nygard, 60
lines — **no unsourced facts**: everything traces to the 049 evaluation §§1–4, the
owner confirmation of 2026-07-14 quoted by the plan preamble, and plan §1); ADR-0003
`Status:` line set to the plan §2 sentence (the only non-path edit among the six moved
ADRs); `ADRs/README.md` index 0000–0006 with citation form `ADR-NNNN` and the remap
note. REGISTRY: §1 re-keyed to 4-digit ids with proposal/spec/plan/report kinds and
kebab slugs, ADR rows removed with a pointer + consumed-ids note, next free **0051**;
§2 second-hop note; new **§2b** complete 0050 remap table; TD-50.1–3 (pending, Date
"(merge)"). `development/README.md` rewritten to the 049 §4 tree; new
`development/work/README.md` (14 lines); folder READMEs for
proposals/specs/plans/reports; `references/README.md` lock.toml row;
`archive/README.md` any-kind sentence. Policies: `document_kinds.md` (kinds table on
`work/…` paths, ADR row `ADRs/NNNN-<kebab-title>.md`, templates on `report-NNNN`),
`naming_conventions.md` (full new scheme incl. the case split and 0043–0048
consumed-ids rule), `agent_workflow.md`, `review_protocol.md` (scope-check globs),
`verification_gates.md` (one vocabulary word), `policies/README.md`, `repo_layout.md`
(development/ tree node redrawn).

C4 (23 files, 82=82): AGENTS.md (authority order `spec-NNNN`/`plan-NNNN` globs, report
vocabulary, branch `work/NNNN-<kebab>`); CLAUDE.md (`/implement-plan <NNNN-kebab>`,
`work/` paths); root README repo-map rows (work/, ADRs/, references incl. lock.toml —
the standalone lock row folded into the references row); PR template;
`implement-plan`/`review-work` command files (.claude + byte-identical .opencode twins
modulo frontmatter) re-argumented to `NNNN-<kebab>`; `.claude/settings.json` deny glob
→ `Edit(development/work/specs/spec-*.md)`; `.gitignore` artifacts glob →
`development/work/reports/*/artifacts/`; code path strings exactly per §6.4
(test_order_ode.py:9,103; test_order_burgers.py:89; s05_dispatch.py:4; jw_step.py:4);
docs/conf.py:2; lock.toml header title line (sole content edit —
`# lock.toml — provenance ledger (…; formerly REFERENCES.lock at the repo root, moved
by work unit 0050)`; entries untouched, re-validated at 51).

## 4. Deviations

1. The `adr 04N`→`ADR-000N` citation sweep for living files landed partly in C3 (the
   policy/README rewrites) rather than C2; only REGISTRY's citations were swapped in
   C2. Net result identical; commit-class boundary shifted, purity of both commits
   verified.
2. REGISTRY §1 statuses "unchanged" with three mechanical exceptions: row 0035
   "this work unit" → "executed" (leftover from 035's authoring; two "this work unit"
   rows would contradict), row 0031 "(plan: 029 record §8)" → "(plan: 0029 report §8)"
   and row 0036 "process record" → "process report" (the §5.2 kinds-vocabulary
   mandate); row 0050 status now "this work unit".
3. Six proposal `Status:` headers ("graduates to development/specs/ via plan 030") →
   `development/work/specs/` via plan 0030 — living files caught by the §7 grep, not
   named in plan §6 (resolves 035's deviation-10 residue).
4. `report-0000-overview.md` lines 4/67: folder-level pointers `development/ideas/` →
   `development/work/proposals/` retargeted in C4 (frozen path-string class; folder
   mentions were invisible to the per-file C2 rules) — declared here since frozen.
5. Headings inside the six moved ADRs keep their historical numbers (`# 046 — …`,
   `# 0001 — …`): retitling is not in plan §2's exhaustive sanction list (035
   precedent); `ADRs/README.md` states this and is the living map.
6. `development/README.md` keeps `008_graupel_component_spec.md` as the historical-name
   example next to the remap-table pointer — a deliberate living-file hit of §7 grep 3
   (mirrors the plan's own §5.2 bridge example).
7. §2b compresses the four uniform series (specs, plans, the 14 STATUS folders,
   proposals) into rule-rows in §2's house style (035 review INFO precedent); all
   non-uniform rows, both READMEs classes, and the six ADRs are explicit.
8. C2 was interrupted by a credit limit and resumed; no state was lost (verified by
   re-running the purity word-diff over the entire uncommitted set before commit).

## 5. Gates (dated 2026-07-15 CEST; logs `/tmp/gate0050_*.log` with `EXIT:` sentinels)

- fast (`not gpu and not slow`): `739 passed, 1 skipped, 143 deselected, 51 warnings in
  954.60s (0:15:54)`, EXIT:0 (07:57, /tmp/gate0050_fast.log; skip = mpi opt-in).
- slow-no-data: `31 passed, 852 deselected, 5 warnings in 867.09s (0:14:27)`, EXIT:0
  (08:13, /tmp/gate0050_slow.log). The S04 order tests wrote
  `development/work/reports/report-0004-coupling-algebra/artifacts/convergence_{burgers,ode}.png`
  at 07:59 — the retargeted artifact path is exercised (mtimes checked before/after).
- data-not-slow: `43 passed, 840 deselected, 11 warnings in 812.82s (0:13:32)`, EXIT:0
  (08:27, /tmp/gate0050_data.log).
- data-slow: `76 passed, 1 skipped, 806 deselected, 28 warnings in 3819.87s (1:03:39)`, EXIT:0
  (09:32, /tmp/gate0050_dataslow.log; skip = upstream MCH-only diffusion).
- ruff check / format: `All checks passed!` / `173 files already formatted` (07:40).
- mypy: `Success: no issues found in 50 source files`; lint-imports:
  `Contracts: 2 kept, 0 broken.` (07:40).
- sphinx `-E -W --keep-going`: `build succeeded.`, EXIT:0 (07:40,
  /tmp/gate0050_sphinx.log).
- Link check (033 §7.2 script): 0 BROKEN (07:41). Husk check: `find development -type d
  -empty` empty. TOML: 51 entries post-move and post-header-edit. Untouchables:
  `git diff main -- docs/architecture constraints/ uv.lock packages/` = exactly the
  §6.4 test_order lines; `git status --porcelain` clean after C5.

### §7 residual greps — by-design hits, enumerated (07:45–08:30)

`REFERENCES.lock`:
- `packages/**` source/test provenance comments (~50 files, e.g.
  `symcon/core/components/base.py:5`) + `validation/L4_idealized/{README.md,make_reference.py}`
  + `benchmarks/dispatch_overhead/jw_step.py:24` — outside plan §6.4's exhaustive code
  list ("exactly the path strings in §6.4"); see follow-up F2.
- `constraints/cpu-ci.txt:1` — untouchable pin file (035 deviation-9 class).
- `development/references/lock.toml:1` (sanctioned formerly-note) and `:407` (inside a
  `[[ref]]` `taken` field — entries untouchable).
- REGISTRY §2b old column + TD-50.3 text; `references/README.md`, `ADR-0006` — defining
  content naming the old file.
- Frozen analysis/quote classes: plan-0050 (8, self-exempt), report-0049 (5),
  report-0034 (3), report-0032 (8), plan-0035 (4), plan-0033 (3),
  report-0035/REPORT.md (1), report-0033/REPORT.md (1), report-0029 (1).

`development/(specs|plans|records|ideas|adr)/`:
- Frozen maps/quotes/analyses: plan-0033 (46), report-0029 (36), archive/plan_tree_map
  (14), report-0033/REPORT.md (12), report-0032 (10), plan-0035 (6),
  report-0035/REPORT.md (4), report-0034 (2), report-0027 (2), plan-0050 (2, self),
  report-0036 (1), report-0031 (1), report-0049 (1), ADR-0000 (1, the reverted
  era-claim), REGISTRY (1, TD-35.4's verbatim glob quote).
- Unexecuted plans 0020–0025/0030: future-deliverable output paths in the 035 scheme
  (18 hits) — F2-class residuals restated at execution time (follow-up F1).

`records_and_liveness|_record(\.md|/)|_idea\.md|_spec\.md|_plan\.md`:
- REGISTRY §2/§2b (63) — THE by-design set; frozen docs as above; inner-file pattern
  collisions on the unchanged `27_docs_plan.md` (docs/conf.py:2, ADR-0004:9,
  work/reports/README.md:42); ADR-0006's own decision text (2);
  `development/README.md:17` historical example (deviation 6);
  `validation/L4_idealized` = "_idea" inside "idealized" (false positive).

`adr 04[3-8]` (living top files): hits only in REGISTRY §2 (rows 136–138) and §2b
(rows 171–176) — the remap tables themselves. Living-file terminology grep
(`_record|_idea|records/|ideas/|NNN_` over AGENTS/CLAUDE/README/commands/PR
template/policies/READMEs): only the naming policy's history clause, the ADRs README
remap note, ADR-0003's actual title in the index, and the `L4_idealized` false
positive.

## 6. Follow-ups

- **F1** (renews 035's F2): when plans 0020–0025/0030 are executed, restate their
  output paths in the `work/` scheme at execution time; their current
  `development/records/0NN_*_record*` strings are by-design residuals.
- **F2**: ~60 `REFERENCES.lock` mentions in `packages/**`/`validation/**` provenance
  comments and `jw_step.py:24` are outside §6.4's sanction and still cite the old
  name; the lock header's formerly-note and REGISTRY §2b bridge them. A trunk-called
  mechanical sweep (comment-only, no code) could retire them.
- Owner at merge: fill TD-50.1–3 dates/evidence; flip REGISTRY row 0050 to executed.

## 7. Artifacts

`development/work/reports/report-0004-coupling-algebra/artifacts/convergence_{ode,burgers}.png`
(untracked, gitignored) — regenerate with
`uv run pytest packages/symcon-core/tests/test_order_ode.py packages/symcon-core/tests/test_order_burgers.py -m "slow" -q`.
