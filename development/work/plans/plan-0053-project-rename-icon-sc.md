# Work unit 0053 — Project rename `symcon` → `ICON-sc`

**Branch:** `work/0053-project-rename-icon-sc` (from `main`; verify `git branch --show-current`
before every commit). One PR. **Deliverable:** the sense-aware rename across live code, config,
harness, and docs, plus `development/work/reports/report-0053-project-rename-icon-sc.md`.

Authority: `docs/architecture/symcon_architecture.md` > `spec-0053-project-rename-icon-sc.md` >
this plan. **The spec's *Frozen interfaces* map is the single source of truth for every
old→new token** — this plan does not restate it; read it there and apply exactly, with the spec's
precedence rule. This work unit changes names only; it changes no behavior, no dependency, no
test outcome.

## Hard rules (restated; full list in `development/work/plans/README.md`)

- `git branch --show-current` = `work/0053-project-rename-icon-sc` before every commit; never
  commit to `main`; never `git push`; `Co-Authored-By:` trailer on every commit.
- **No dependency-pin changes.** `constraints/*.txt` untouched (they contain no `symcon`);
  `uv.lock` changes are **regeneration only** — it may move only distribution-name and
  editable-path strings, never a version. If `uv lock` moves any pin: **STOP**, mark blocked.
- **No tolerance / reduction-order / `pytest.mark` / test-assertion changes.** No `-x`/`-k`/
  `--ignore`/marker edits to make a gate pass. Bitwise T0≡T1 equivalence stays bitwise.
- **Preserve namespace-package semantics:** never create an `icon_sc/__init__.py`.
- **Frozen-history exemption (spec Out of scope / TD-53.3):** do not rewrite `REGISTRY.md` §2*
  remap columns or past-tense signed-off TD rows; frozen `reports/*`, `proposals/*`; `lock.toml`
  evidence; the `layout-doc-revision.diff` artifact. Renaming those falsifies signed-off history.
- **Sanctioned guard relaxations, bracketed and restored** (globs unchanged, so protection is
  identical afterward): temporarily lift `Edit(docs/architecture/**)` + `Edit(LICENSE)` in
  `.claude/settings.json` **and** `opencode.json` to rebrand the arch doc + LICENSE; temporarily
  disable the `spec_freeze_guard.py` PreToolUse hook to rewrite `spec-0001..0052`; restore both at
  C5. (`Write` on the arch doc's new path is not covered by the `Edit` deny — the alternative.)
- If any item needs more than its scope (e.g. a technical change to the architecture doc): **STOP**,
  mark "blocked — needs trunk decision" in the report, continue the rest.

## Registration (this commit, at assignment)

`REGISTRY.md` §1: add `| 0053 | project-rename-icon-sc | spec + plan + report | pending |`; bump
**Next free number → 0054**. §3 decision rows added at C4 (mirrored by `TD-PENDING:` report lines):
**TD-53.1** architecture-doc rebrand (name token + rev-note only; v1.3 retained; no technical
change), **TD-53.2** import namespace = `icon_sc` (PEP 420 preserved), **TD-53.3** the
current-system-vs-frozen-history scope boundary.

## Sequencing note (no per-commit green)

C1/C2 rename dirs/identifiers while `pyproject.toml` still says `symcon-*`/`packages=["src/symcon"]`,
so the workspace is not installable until C3 regenerates packaging + `uv.lock`. Run the full gate
battery once, at C5, after `uv sync`. `uv lock` (C3) must precede `uv sync` (C5). Each `git mv`
(C1) will prompt (not in the bash allowlist); `git push` is denied — do not attempt.

## C1 — renames only (`git mv`; purity: 100 % renames)

- `packages/symcon-{core,icon,bridges}/` → `packages/icon-sc-{core,icon,bridges}/`, then inside
  each `src/symcon/` → `src/icon_sc/` (the `core|icon|bridges` subtree + `py.typed` ride along).
- `git mv docs/architecture/symcon_architecture.md docs/architecture/icon-sc_architecture.md`
  (the `Edit(docs/architecture/**)` deny does not block `git mv`).
- `git mv docs/tutorials/00_what_is_symcon.md docs/tutorials/00_what_is_icon-sc.md`.

**Verify:** `git show --summary -M100 HEAD` shows only renames; `test -d packages/icon-sc-core/src/icon_sc/core`.

## C2 — import namespace + code identifiers (`.py` + code-level config)

Apply the spec map to code. Bulk-substitute with review; the precedence rule prevents
`icon_sc-core` corruption. Touches: `packages/*/src`, `packages/*/tests`, `examples/`,
`benchmarks/`, `validation/`, `tools/names_audit.py`, root `conftest.py`, `.importlinter`.

- `import symcon` / `from symcon.…` → `icon_sc` (167 files / 606 import lines).
- `conftest.py`: `pytest_plugins = ("icon_sc.core.testing.plugin",)`.
- `.importlinter`: `root_packages` + both `forbidden`/`source_modules` contracts → `icon_sc.*`.
- **`packages/icon-sc-core/tests/test_namespace.py`** (explicit edit, not "verify"): imports +
  `resources.files("icon_sc.core")` → `icon_sc`; **`roots` set → `{"icon-sc-core","icon-sc-icon","icon-sc-bridges"}`
  (hyphen)**.
- Misc identifiers `symcon_backend`/`symcon_name`/`symcon_value`/`symcon_column`/`ps_symcon`/
  `temp_symcon` → `icon_sc_*`; NetCDF `symcon_provenance` → `icon_sc_provenance`; artifacts
  `jw_l4_symcon.npz`/`jw_l4_symcon.partial.npz` → `jw_l4_icon_sc*`; `generate_symcon` →
  `generate_icon_sc`. Confirm `id="symcon_column"` (`_column_grid.py:41`) is internal-only before renaming.

**Verify:** `rg -n 'symcon' packages examples benchmarks validation tools conftest.py .importlinter`
returns nothing; namespace test reads correctly.

## C3 — packaging & tooling config

- Root `pyproject.toml`: `[project] name`/`description`/`dependencies`; `[tool.uv.sources]` keys;
  dev extras (`icon-sc-icon[datatest]`, `[gridgen]`); `[tool.ruff] src`; isort
  `known-first-party = ["icon_sc"]`; `[tool.mypy] mypy_path` + the `-p symcon.core` comment.
  (`members = ["packages/*"]` unchanged.)
- 3 per-package `pyproject.toml`: `name`, `description`, inter-package `dependencies`
  (`icon-sc-core`), `[tool.hatch.build.targets.wheel] packages = ["src/icon_sc"]`.
- `.pre-commit-config.yaml` (`-p icon_sc.core`, `files: ^packages/icon-sc-core/src/`).
- `.github/workflows/{lint,test-cpu}.yml` (`-p icon_sc.core`, `-e packages/icon-sc-*`,
  `import icon_sc.core`). Other three workflows have no literal.
- `docs/conf.py`: `project = "ICON-sc"`.
- `tools/run_gate.py`: mypy tuple `-p icon_sc.core`; `/tmp/icon-sc-gate-<pid>`.
- Cache setters → `~/.cache/icon-sc/…`: `…/core/testing/plugin.py`,
  `benchmarks/dispatch_overhead/jw_step.py`, `examples/02_jw_baroclinic.py`,
  `validation/L4_idealized/make_reference.py`, and
  `packages/icon-sc-icon/src/icon_sc/icon/testing.py` (`~/.cache/icon-sc/{generated-grids,icon4py-testdata}`).
- `uv lock` (regenerate). **STOP if any version moves.**

**Verify:** `git diff main -- constraints/` empty; `uv sync --locked` resolves.

## C4 — docs & living `development/` prose (current-system only; sense-aware)

- Root: `README.md`, `CLAUDE.md`, `AGENTS.md` (authority-order sentence →
  `docs/architecture/icon-sc_architecture.md`; import-boundary rule → `icon_sc.*`), `LICENSE` copyright.
- `docs/`: `index.md` (incl. extensionless toctree `architecture/symcon_architecture` at :74, the
  `:47` link, the `:33` `git clone … symcon && cd symcon` dir name), `glossary.md`,
  `names_registry.md` (regenerated at C5), `api/*.md`; **all `docs/tutorials/*`** — the renamed
  `00_what_is_icon-sc.md`, `01_state_fields_grids.md`, `02_first_run_scm.md`, and `index.md` (bare
  toctree `00_what_is_symcon` at :17); the **architecture doc** — H1 rebrand, 25 prose mentions, the
  **5-line** illustrative import block (`:214-219`), and a v1.3 rev-note "rebrand symcon→ICON-sc, no
  technical change".
- **`packages/*/README.md`** (3; packaged wheel metadata: H1 `# icon-sc-core` etc.).
- **`validation/L4_idealized/README.md`, `validation/L8_gradients/README.md`**.
- `development/policies/*` incl. `repository-layout.md` (package/module/tree/cache/arch-doc-filename) and
  **`review-protocol.md:4`** (hardcoded `…/grAItools/symcon` absolute path → `…/grAItools/ICON-sc`);
  `REGISTRY.md` header/rules prose **only** (not §2* remap columns / signed-off TD wording) + the §1
  row + TD-53.1/2/3 rows; living folder READMEs; `.github/PULL_REQUEST_TEMPLATE.md`;
  `.claude/commands/*` + `.opencode/command/*` prose; `.gitignore` cache-namespace comment (L24-26).
- **specs `spec-0001..0052`** (guard disabled for this step): `symcon.*` → `icon_sc.*`,
  `symcon-*` → `icon-sc-*` in acceptance criteria. Then re-enable the guard.
- Retarget every arch-doc/tutorial reference **with or without `.md`** (incl. `{toctree}` entries).

**Verify:** `git diff main -- development/references/lock.toml` empty; the frozen-history exemptions
untouched; every arch-doc link resolves.

## C5 — external, caches, gates, report

- `.git/config` remote → `git@github.com:grAItools/ICON-sc.git`.
- Restore guards (settings.json/opencode.json deny globs; re-enable freeze hook).
- Clear stale caches: `.import_linter_cache/` (tracked? verify — holds `symcon.*.meta.json`),
  `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, all `__pycache__/`; `uv sync` (regenerates
  editable `.pth` shims). Regenerate `docs/names_registry.md` via `uv run python tools/names_audit.py`.
- Run the full gate battery (below). Write `report-0053-project-rename-icon-sc.md` per
  `document-kinds.md`: rename ledger + per-commit purity, the enumerated ~30 by-design frozen-history
  residuals, dated gate lines, deviations, the two owner-manual follow-ups (GitHub rename, root-dir mv).

## Acceptance criteria

Per `spec-0053` Acceptance criteria 1–8 (namespace preserved + `test_namespace.py`; importability;
gates green with identical counts; no dependency change; residual grep = enumerated history; arch
doc rebranded/renamed retaining v1.3; remote + REGISTRY + TD rows; report committed).

## Verification gates (run at C5, after `uv sync`)

`uv run python tools/run_gate.py` green end-to-end (its mypy target is now `icon_sc.core`), plus:
- `uv run python -c "import icon_sc.core, icon_sc.icon, icon_sc.bridges"`.
- `uv run pytest packages -q` — identical passed/skipped counts to the pre-rename baseline;
  `test_namespace.py` green.
- `uv run mypy --strict -p icon_sc.core` → `Success: no issues found in 50 source files`.
- `uv run lint-imports` → `Contracts: 2 kept, 0 broken`.
- `uv run ruff check` + `uv run ruff format --check` clean.
- `uv run sphinx-build -E -W --keep-going docs docs/_build/html` exit 0 (catches orphaned/
  extensionless toctree refs to the renamed arch-doc/tutorial).
- Residual grep: `grep -rInE 'symcon' . --exclude-dir=.git --exclude-dir=.venv
  --exclude-dir=docs/_build --exclude-dir='*_cache' --exclude-dir=__pycache__
  --exclude-dir=node_modules` = the enumerated frozen-history hits only.
- `git diff main -- constraints/ development/references/lock.toml` empty.

## Review checklist (fresh reviewer; protocol `policies/review-protocol.md`)

- **C1 purity:** `git show -M100 --name-status` for C1 = renames only; namespace dirs are
  `src/icon_sc/`, no `icon_sc/__init__.py` introduced.
- **Namespace correctness:** re-run `test_namespace.py`; confirm the `roots` set uses hyphenated
  distribution names and imports use `icon_sc`.
- **No hidden behavior change:** `git diff main..HEAD` — grep for tolerance strings (`rtol|atol`),
  `pytest.mark` edits, `-x `/`-k `/`--ignore`; all absent. `git diff main -- constraints/ uv.lock`:
  `uv.lock` moves only name/path strings, no version.
- **Frozen-history integrity:** `git diff main -- development/references/lock.toml
  development/work/reports development/work/proposals` shows the exempt set untouched; REGISTRY §2*
  remap columns unchanged; spot-check ≥3 frozen reports byte-identical.
- **Coverage/counts:** gate counts identical to baseline; import-linter 2 kept/0 broken; sphinx `-W` green.
- **Residual grep** reproduced independently = the report's enumerated history list, nothing else.
- **Registration:** row 0053 present, Next free = 0054, TD-53.1/2/3 present and mirrored by report
  `TD-PENDING:` lines; guards restored (settings/opencode deny globs + freeze hook re-enabled).
- Verdict per protocol.
