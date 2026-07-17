# 0053 — Project rename `symcon` → `ICON-sc`

**Depends on:** 0052 (merged) · **Source:** owner-accepted plan (this session, 2026-07-17) · **Policies:** `policies/naming-conventions.md`, `policies/verification-gates.md`, `policies/agent-workflow.md`, `policies/document-kinds.md`

## Goal

Rebrand the project from **symcon** to **ICON-sc** cleanly and sense-aware, across all live
code, configuration, harness, and human-facing documentation, **without any behavior change**.
"symcon" means *sympl-Conformant*; "ICON-sc" means *ICON, sympl-conformant* — the architecture
doc's tagline ("A sympl-Conformant Python Architecture for the ICON Model") is preserved
verbatim; only the leading name token changes. No dependency-pin change, no tolerance change, no
reduction-order change, no test-assertion or `pytest.mark` change. The PEP 420 namespace-package
semantics are preserved under the new name. Frozen history is preserved (see Out of scope).

## In scope

The name appears in three independent senses plus runtime/external artifacts; each renames per
the **Frozen interfaces** map below. Only references to the **current system** are renamed:

1. **Import namespace** `symcon` → `icon_sc` (identifier) across all `.py`, `.importlinter`,
   `conftest.py`, mypy targets, isort config: `symcon.core/.icon/.bridges` → `icon_sc.core/.icon/.bridges`.
2. **Distribution names** `symcon-core/-icon/-bridges`, `symcon-workspace` → `icon-sc-*`
   (pyproject `name`/deps/`[tool.uv.sources]`/extras, per-package dirs, `uv.lock` regenerated,
   `.py` string literals that name distribution dirs).
3. **Brand / prose** `symcon` (the word) → `ICON-sc` in README, docs, comments, titles.
4. **Filesystem/runtime**: package dirs `packages/symcon-*/` → `packages/icon-sc-*/`, import dirs
   `src/symcon/` → `src/icon_sc/`; cache/tmp namespaces `~/.cache/symcon`,
   `$XDG_CACHE_HOME/symcon`, `/tmp/symcon-gate` → `icon-sc`; NetCDF output attribute
   `symcon_provenance` → `icon_sc_provenance`; reference artifacts `jw_l4_symcon.npz` /
   `generate_symcon` → `icon_sc`; misc identifiers `symcon_backend`, `symcon_name`,
   `symcon_value`, `symcon_column`, `ps_symcon`, `temp_symcon` → `icon_sc_*`.
5. **Doc filenames** (brand token rendered as `icon-sc`): `symcon_architecture.md` →
   `icon-sc_architecture.md`; `00_what_is_symcon.md` → `00_what_is_icon-sc.md`.
6. **Git remote** `grAItools/symcon` → `grAItools/ICON-sc` (`.git/config`; GitHub repo rename +
   working-copy root-dir rename are owner-manual, out of the branch diff).
7. **Living `development/` prose** naming the current system: `policies/*` (incl. `repo-layout.md`
   and `review-protocol.md`), `REGISTRY.md` header/rules prose, folder READMEs, PR template,
   `.claude`/`.opencode` command prose; and — per the owner's ratified scope — the work-unit
   **specs** (`spec-0001..spec-0052`), whose `symcon.*` refs are current-system acceptance criteria.

## Out of scope

- **Frozen historical records (TD-53.3, exempt):** `REGISTRY.md` §2/§2b/§2c remap "Old"/"New"
  columns and past-tense signed-off `TD-*` rows; frozen `development/work/reports/*` and
  `development/work/proposals/*` wording; `development/references/lock.toml` evidence strings; the
  tracked artifact `development/work/reports/report-0033-structure-migration/layout-doc-revision.diff`.
  Retro-renaming these would falsify signed-off history and destroy the remap bridge (e.g.
  `REGISTRY.md:150` names `symcon_repo_layout.md`, a file that no longer exists). Matches
  `plan-0035` ("frozen records keep historical wording") and AGENTS.md. The ~30 by-design residual
  `symcon` hits are enumerated in the report and the residual-grep allowlist, not rewritten.
- Any functional/behavioral change; dependency-pin bumps; `constraints/*` edits; tolerance,
  reduction-order, test-assertion, or `pytest.mark` changes. `uv.lock` changes are regeneration only.
- The published architecture-doc **technical content** — only its name token + a rev-note change
  (TD-53.1); v1.3 is retained (a pure rebrand implies no technical revision).

## Frozen interfaces

The target naming scheme is the load-bearing interface (implement exactly):

| Sense | Old | New |
|---|---|---|
| Import namespace (PEP 420, **no** top-level `__init__.py`) | `symcon`, `symcon.{core,icon,bridges}` | `icon_sc`, `icon_sc.{core,icon,bridges}` |
| Distributions | `symcon-{core,icon,bridges}`, `symcon-workspace` | `icon-sc-{core,icon,bridges}`, `icon-sc-workspace` |
| Distribution dir names (incl. in `.py` string literals) | `packages/symcon-{core,icon,bridges}` | `packages/icon-sc-{core,icon,bridges}` |
| Import dir | `packages/*/src/symcon/` | `packages/*/src/icon_sc/` |
| pytest plugin path | `symcon.core.testing.plugin` | `icon_sc.core.testing.plugin` |
| import-linter contracts | `symcon.core ↛ symcon.{icon,bridges}`, `symcon.icon ↛ symcon.bridges` | same under `icon_sc.*`; **2 kept, 0 broken** |
| mypy strict target | `-p symcon.core` | `-p icon_sc.core` |
| NetCDF provenance attr | `symcon_provenance` | `icon_sc_provenance` |
| Cache/tmp fs namespace | `~/.cache/symcon`, `/tmp/symcon-gate` | `~/.cache/icon-sc`, `/tmp/icon-sc-gate` |
| Doc filenames | `symcon_architecture.md`, `00_what_is_symcon.md` | `icon-sc_architecture.md`, `00_what_is_icon-sc.md` |

**Precedence when substituting (per file-type, most-specific first):** `symcon-workspace` →
`symcon-<pkg>` → `symcon.<sub>` → bare import `symcon` → `symcon_<identifier>` → fs `symcon`/tmp →
brand word `symcon`. Hyphenated `symcon-*` → `icon-sc-*` **even inside `.py` string literals**
(e.g. `test_namespace.py` `roots` set); in `.md`, the standalone word is the brand → `ICON-sc`
but code spans/imports are identifiers → `icon_sc`.

## Acceptance criteria

1. **No `__init__.py` at the `icon_sc` namespace level** (PEP 420 preserved);
   `packages/icon-sc-core/tests/test_namespace.py` passes (`not hasattr(icon_sc, "__file__")`,
   `roots == {"icon-sc-core","icon-sc-icon","icon-sc-bridges"}`).
2. Importability: `uv run python -c "import icon_sc.core, icon_sc.icon, icon_sc.bridges"` succeeds
   after `uv sync`.
3. Full gate battery green with **identical passed/skipped counts** to the pre-rename baseline
   (`policies/verification-gates.md`): pytest partitions, `ruff check`/`format --check`,
   `mypy --strict -p icon_sc.core` (Success, 50 source files), `lint-imports` **Contracts: 2 kept,
   0 broken**, `sphinx-build -E -W --keep-going` exit 0.
4. **No dependency change:** `git diff main -- constraints/` empty; `uv.lock` differs only by the
   distribution-name/editable-path rename (no version moved); `uv sync --locked` resolves.
5. **Residual `symcon` grep** (excluding `.git`, `.venv`, `docs/_build`, `*_cache`, `__pycache__`,
   `node_modules`) equals the enumerated by-design frozen-history hits (§ Out of scope), each named
   in the report — nothing else.
6. `docs/architecture/icon-sc_architecture.md` exists with H1
   `# ICON-sc: A sympl-Conformant Python Architecture for the ICON Model`, v1.3 retained + a
   rebrand rev-note; no technical-content change (TD-53.1). `docs/architecture/symcon_architecture.md`
   no longer exists.
7. `.git/config` remote is `grAItools/ICON-sc`; `REGISTRY.md` row 0053 present, "Next free number"
   = 0054, and TD-53.1/53.2/53.3 recorded (mirrored by `TD-PENDING:` lines in the report).
8. Report `development/work/reports/report-0053-project-rename-icon-sc.md` per the
   `document-kinds.md` template, with the rename ledger, the enumerated frozen-history residuals,
   dated gate lines, and deviations.
