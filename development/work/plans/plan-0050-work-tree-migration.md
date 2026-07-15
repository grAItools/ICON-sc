# Work unit 0050 — `development/work/` migration (kind-prefixed names, ADRs/, lock.toml)

**Branch:** `work/0050-work-tree-migration` (plan committed on it; execution continues on
the same branch — one PR). First document born under the convention it implements.

**Deliverable:** the migration + the record
`development/work/reports/report-0050-work-tree-migration.md`.

Frozen at assignment. Implements `development/work/reports/report-0049-work-structure-iteration.md`
(owner-confirmed 2026-07-14: value-preserving 4-digit remap; ADRs/ independent from 0000;
proposals/reports renames; `document_kinds.md`; lock.toml move; REGISTRY/READMEs stay in
place with contents updated; **archive/ stays at the development/ root** — it must accept
dead documents of any kind, not only work documents). On conflict with reality: stop,
record, resolve only the mechanical-and-obvious.

## 1. The agreed decisions (binding)

1. Lifecycle folders group under `development/work/{proposals,specs,plans,reports}`
   (ex-`ideas`, unchanged, unchanged, ex-`records`). Files: `<kind>-<NNNN>-<kebab-slug>`
   (`proposal-`, `spec-`, `plan-`, `report-`), four digits, **numeric values preserved**
   from the current ids; slugs converted snake→kebab. Multi-file reports keep folder form
   `report-NNNN-<kebab>/` (inner files unchanged). Related items share NNNN across
   subfolders. Work-id sequence is independent of everything outside `work/`.
2. `adr/` → `ADRs/` (the repo's single deliberate non-lowercase folder), Nygard
   `<NNNN>-<kebab-title>.md`, own sequence from `0000`: existing six remap in order
   (043→0000, 044→0001, 045→0002, 046→0003, 047→0004, 048→0005); the new ADR of this
   migration is `0006`; citation form `ADR-NNNN`.
3. `REFERENCES.lock` → `development/references/lock.toml` (verified valid TOML; header
   title line updated; `[[ref]]` entries and their historical `step` ids untouched).
4. `policies/records_and_liveness.md` → `policies/document_kinds.md` (rename + vocabulary
   sweep). Policies stay snake_case unnumbered; kebab is for `work/` + `ADRs/` only.
5. Terminology (living files only): lifecycle vocabulary becomes
   proposal → spec → plan → report; "record"/"idea" as kind names disappear from living
   surfaces. Frozen documents keep wording; only path strings change (ADR-0001 rule,
   post-remap `ADRs/0001-content-frozen-records.md`).
6. `REGISTRY.md`, `development/README.md`, folder READMEs, reference cards, `archive/`
   stay in place; contents updated to the new state.

## 2. Hard rules (restated)

- `git branch --show-current` = `work/0050-work-tree-migration` before every commit;
  never commit to main; never push; `Co-Authored-By:` trailer.
- No data, no pins, no tolerances. `lock.toml` entries are append-only — this migration
  edits ONLY the header comment's title line (`REFERENCES.lock` → `lock.toml`), nothing
  below line ~14. `docs/architecture/symcon_architecture.md` untouched.
- Frozen documents: path-string retargets only. Sanctioned non-path edits, exhaustively:
  the lock header title; ADR `0003-document-naming-scheme.md`'s `Status:` line (the
  Status field is mutable by the kinds policy) →
  `accepted; sequence/suffix clauses superseded-by-0006 (number-sharing and exemption clauses stand)`.
- `packages/`/`benchmarks/` edits: exactly the path strings in §6.4. Full gate battery;
  no `-x`/`--ignore`/`-k`/marker games.

## 3. Rename map (commit C1 — `git mv` only, ~84 renames)

Slug rule: take the current name's slug, convert `_`→`-`. Verify every target.

- **specs/** (15): `development/specs/NNN_<snake>_spec.md` →
  `development/work/specs/spec-0NNN-<kebab>.md` for NNN = 001…014
  (e.g. `001_repo_scaffold_spec.md → spec-0001-repo-scaffold.md`,
  `005_vault_plan_t1_spec.md → spec-0005-vault-plan-t1.md`); plus
  `specs/README.md → work/specs/README.md`.
- **plans/** (25): `NNN_<snake>_plan.md → work/plans/plan-0NNN-<kebab>.md` for
  001…014, 020…025, 028, 030, 033, 035 (24 files; e.g.
  `035_naming_migration_plan.md → plan-0035-naming-migration.md`); plus
  `plans/README.md → work/plans/README.md`.
- **records/ → work/reports/** (28): `000_overview_record.md → report-0000-overview.md`;
  the 14 record folders `NNN_<snake>_record/ → report-0NNN-<kebab>/` (inner `STATUS.md`
  unchanged); flat records 026/028/031/049
  `NNN_<snake>_record.md → report-0NNN-<kebab>.md`
  (049 = `049_work_structure_iteration_record.md → report-0049-work-structure-iteration.md`);
  folder records 027/029/032/033/034/035 `NNN_<snake>_record/ → report-0NNN-<kebab>/`
  (inner files unchanged, incl. 033's diff artifact);
  `036_implementation_report_record.md → report-0036-implementation-report.md`;
  `records/README.md → work/reports/README.md`.
- **ideas/ → work/proposals/** (7): `0NN_<snake>_idea.md → proposal-00NN-<kebab>.md` for
  037…042 (e.g. `037_p2_distributed_idea.md → proposal-0037-p2-distributed.md`);
  `ideas/README.md → work/proposals/README.md`.
- **adr/ → ADRs/** (7): `043_development_tree_reorganization_adr.md →
  ADRs/0000-development-tree-reorganization.md`; `044_… → 0001-content-frozen-records.md`;
  `045_… → 0002-decision-register-and-adrs.md`; `046_… → 0003-document-naming-scheme.md`;
  `047_… → 0004-docs-stack.md`; `048_… → 0005-gridgen-adoption.md`;
  `adr/README.md → ADRs/README.md`.
- **root** (2): `REFERENCES.lock → development/references/lock.toml`;
  `development/policies/records_and_liveness.md → development/policies/document_kinds.md`.

After C1: purity — count `^ rename` lines in `git show --summary -M100 HEAD` (expect 84;
if the true tracked-file count differs, verify every §3 bullet executed and record the
count with its explanation); zero non-`R100` lines; no empty directory husks
(`find development -type d -empty`).

## 4. Path retargeting (commit C2 — path strings only)

Old→new per §3, applied to every `.md`/`.diff` under `development/` and the living root
files. Additional mappings and cautions:

- `REFERENCES.lock` → `development/references/lock.toml` (~110 mentions; inside
  `development/` most are frozen — path-string class). In prose like "append to
  REFERENCES.lock", the filename IS a path string — retarget it; the *rule* wording stays.
- `adr 043`…`adr 048` citations → `ADR-0000`…`ADR-0005` (living files); in frozen files
  they are wording — leave, the REGISTRY remap translates.
- `records_and_liveness.md` → `document_kinds.md`.
- Never touch: `symcon/core/plan/` and other source paths; `lock.toml` entries;
  `docs/architecture/symcon_architecture.md`; the §3 map inside THIS plan; the
  self-exempt frozen documents already established (the 033/035 plans' and records' own
  mapping tables and quoted outputs, the 034/049 evaluations' analyses, the layout diff
  artifact) — same judgment as 035's C2, every left-alone case listed in the record.

Purity: word-diff = path strings only. Commit C2.

## 5. New and restructured content (commit C3)

1. **`ADRs/0006-work-tree-and-kind-prefixed-names.md`** — Nygard, ≤60 lines, from the 049
   evaluation §§1–4: work/ grouping; kind-NNNN-kebab with value-preserving 4-digit remap
   (alternatives: compact renumber — rejected, third re-keying breaks the bridge);
   proposals/reports renames; ADRs/ uppercase exception + independent sequence
   (supersedes 0003's sequence/suffix clauses; number-sharing across a work unit's files
   and the policies/README/REGISTRY/archive exemptions restated as surviving); lock.toml
   move; archive at root (must accept any kind). Update `0003`'s Status line per §2 and
   `ADRs/README.md` (index 0000–0006, citation form ADR-NNNN, the remap note).
2. **REGISTRY.md** (living, stays at `development/`): §1 re-keyed to 4-digit work ids
   with kinds column vocabulary `proposal/spec/plan/report` (statuses unchanged; ADR rows
   000N leave §1 — ADRs are indexed by `ADRs/README.md`; §1 keeps a one-line pointer);
   allocate row `0050 | work-tree-migration | plan + report | this work unit`; next free
   **0051**. §2 gains a note that its "New" column resolves further via the new **§2b —
   remap (work 0050)**: complete §3 old→new table (the second hop of the historical
   bridge: `S08 → 008_graupel_component_spec.md → spec-0008-graupel-component.md`).
   Decision register: TD-50.1 (work/ tree + kind-prefixed names + value-preserving remap,
   source ADR-0006), TD-50.2 (ADRs/ independence + uppercase exception), TD-50.3
   (lock.toml move + header-title edit sanction) — pending/(merge).
3. **READMEs updated in place**: `development/README.md` (new tree §4 of the 049 record;
   lifecycle proposal → spec → plan → report; archive = any-kind basin); new
   `development/work/README.md` (the lifecycle + naming in ≤15 lines); folder READMEs
   (proposals/specs/plans/reports) — naming examples in the new scheme;
   `references/README.md` gains the `lock.toml` row (machine ledger, append-only,
   ex-`REFERENCES.lock`); `archive/README.md` gains the any-kind sentence.
4. **Policies**: `document_kinds.md` — vocabulary sweep (record→report, idea→proposal),
   kinds table updated (folder column `work/…`), the ADR row's naming updated;
   `naming_conventions.md` — the full new scheme (kind-NNNN-kebab, 4-digit,
   value-preserved history, ADRs/ exception + own sequence, kebab/snake split, branch
   `work/NNNN-<kebab>`); `agent_workflow.md`, `review_protocol.md`,
   `verification_gates.md`, `reference_mining.md` (lock.toml path + "append to
   lock.toml"), `repo_layout.md` (its `development/` tree node redrawn to §4 of the 049
   record) — path/vocabulary updates only where stale.

## 6. Living-file edits and tooling (commit C4)

1. **AGENTS.md**: authority order →
   `docs/architecture/symcon_architecture.md (v1.3) > development/work/specs/spec-NNNN-*.md
   > development/work/plans/plan-NNNN-*.md`; lock path; kind vocabulary.
   **CLAUDE.md**: paths + `/implement-plan <NNNN-kebab>` wording. **Root README**:
   repo-map rows (work/, ADRs/, references incl. lock.toml). **PR template**: spec path.
2. **Terminology sweep** (living files only): "record"/"idea" as kind names →
   "report"/"proposal" across policies, READMEs, REGISTRY headers/columns, commands.
   Generic English uses of "record" (verb; "the historical record") stay — judgment, list
   ambiguous cases in the record.
3. **Tooling**: `.claude/commands/implement-plan.md` + `.opencode` twin — argument is now
   `NNNN-<kebab>`; spec `development/work/specs/spec-$ARGUMENTS.md`, plan
   `development/work/plans/plan-$ARGUMENTS.md`, report
   `development/work/reports/report-$ARGUMENTS(.md|/)`; same for `review-work.md`.
   `.claude/settings.json` deny glob → `"Edit(development/work/specs/spec-*.md)"`.
   `.gitignore`: `development/records/*/artifacts/` →
   `development/work/reports/*/artifacts/`.
4. **Code path strings** (only these): `packages/symcon-core/tests/test_order_ode.py`
   (docstring + path line) and `test_order_burgers.py` →
   `development/work/reports/report-0004-coupling-algebra/artifacts`;
   `benchmarks/s05_dispatch.py:4` → `…/report-0005-vault-plan-t1/STATUS.md`;
   `benchmarks/dispatch_overhead/jw_step.py:4` → `…/report-0014-plan-through-dycore/STATUS.md`.
5. **docs/**: `docs/conf.py:2` comment path (the 027 record) →
   `development/work/reports/report-0027-docs-plan/…`. Nothing else under `docs/`.
6. **lock.toml header**: title line `# lock.toml — provenance ledger …` (formerly
   REFERENCES.lock note appended to the header comment); entries untouched.

## 7. Commit sequence and gates

C1 renames → C2 retargets → C3 content → C4 living/tooling → C5 record. Purity checks as
in §3/§4; same discipline as 033/035.

Gates (baselines unchanged: fast 739/1 · slow 31 · data 43 · data-slow 76/1 · ruff
clean/173 · mypy 50 · lint-imports 2 · sphinx `-E -W` exit 0). Long partitions: detached
sentinel logs under `/tmp/gate0050_*.log`, actively polled — never idle-wait for a
notification. The S04 order tests are **slow**-marked: the slow partition exercises the
retargeted artifact path (must write `…/report-0004-coupling-algebra/artifacts/*.png`).

Residual checks (each: zero hits outside frozen by-design + this plan + REGISTRY remap;
enumerate every by-design hit in the record):

```bash
grep -rn "REFERENCES.lock" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rnE "development/(specs|plans|records|ideas|adr)/" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rnE "records_and_liveness|_record(\.md|/)|_idea\.md|_spec\.md|_plan\.md" . --exclude-dir=.git --exclude-dir=docs/_build
grep -rnE "adr 04[3-8]" AGENTS.md CLAUDE.md README.md development/policies/ development/README.md development/REGISTRY.md
```

(the third pattern will hit the §2 remap tables and frozen docs — those are the by-design
set; anything in a living file is a miss). Plus: the 033-plan link checker (0 BROKEN);
`find development -type d -empty` empty; TOML validity of the moved lock
(`uv run python -c "import tomli; tomli.load(open('development/references/lock.toml','rb'))"`
— tomli is importable in the project venv); untouchables diff
(`git diff main -- docs/architecture constraints/ uv.lock packages/` = only §6.4 lines);
living-file terminology grep for `_record`/`_idea`/kind-suffix leftovers.

## 8. Record — `development/work/reports/report-0050-work-tree-migration.md`

Per the STATUS template (`policies/document-kinds.md` post-rename): rename ledger with
the observed count and any explanation, retarget stats + judgment calls, content summary,
verbatim dated gate lines, deviations, by-design residual hits one line each, follow-ups.

## 9. Review checklist (fresh reviewer; protocol `development/policies/review-protocol.md`)

1. C1 purity (expected 84 R100 — verify the observed count against the §3 bullets
   yourself; any non-rename line is a finding) and C2 purity (word-diff ≥5 frozen files
   across kinds; wording change in frozen content = MAJOR; `adr 04N`→`ADR-000N` citation
   changes only in living files).
2. Spot frozen integrity: ≥3 specs + 2 reports byte-identical modulo path strings; the
   lock byte-identical below its header comment (`git diff` on blobs, skip first ~14
   lines); ADR 0003's Status line is the ONLY non-path change among the six moved ADRs.
3. ADR-0006 faithful to the 049 evaluation (owner amendments included: archive at root);
   REGISTRY §1 re-keyed correctly vs the filesystem (scripted check: every work id ↔
   files), §2b complete vs §3, TD-50.1–3 pending, no other row-cell changes.
4. READMEs/policies: no stale tree drawings or kind vocabulary
   (`grep -rn "ideas/\|records/" development/README.md development/work/ development/policies/`
   — hits only where historical); `document_kinds.md` rename complete.
5. Re-run §7 residual checks, link checker, TOML validity, husk check, terminology grep,
   and the full gate battery (log-verify long partitions against dated sentinels if
   inputs unchanged — state which).
6. Record honesty; deviations verified individually.

Verdict `approve`/`request-changes`, findings MAJOR→MINOR→INFO with file:line evidence.
