# Task 28 report — documentation build (Sphinx + MyST site, API reference, tutorials T0–T2, Pages deploy)

**Branch:** `task/28-docs-implementation` (from `main` = `a38ca01`).
**Commits:** one per item A–F, plus this report.
**Environment:** python 3.10.18 workspace venv, warm gt4py/testdata caches.

## Per-item summary and verifications

### Item A — tooling config + dependencies

- `pyproject.toml` dev group: `sphinx>=8.1`, `myst-parser>=4.0`, `furo>=2025.12.19`
  (exactly TD-2; comment points at plan 27 §3.3).
- `constraints/cpu-ci.txt`: the four TD-2 pins (`sphinx==8.1.3`, `myst-parser==4.0.1`,
  `furo==2025.12.19`, `docutils==0.21.2`) under the required comment. Nothing else
  in `constraints/` changed.
- `uv lock`: lockfile grows only. `git diff uv.lock` contains **zero** changed
  lines matching `gt4py|icon4py|jax`. The only removed lines are four
  `markdown-it-py` dependency-list entries replaced by python-version-marked
  variants (see "Findings" 1). `uv lock --check` passes.
- `docs/conf.py`: the prompt's block verbatim, plus three config-only additions
  (see "Deviations" 1): `exclude_patterns = ["_build", "api/README.md"]` and
  `myst_heading_anchors = 2`.
- Verified: `uv run python -c "import sphinx, myst_parser, furo; print(sphinx.__version__)"`
  → `8.1.3`. Initial `sphinx-build` reached source reading and failed only on the
  missing master document (provided by item B, as the prompt anticipates).

### Item B — site skeleton + nav

- Created `docs/index.md` (landing: what symcon is, install, links),
  `docs/tutorials/index.md` (T0–T8; T0–T2 in a toctree, T3–T8 titled + §1.2
  abstracts marked planned), `docs/glossary.md` (8 terms for T0–T2, science-in,
  one paragraph each). `docs/_build/` added to `.gitignore`.
- `docs/architecture/symcon_architecture.md` and `symcon_repo_layout.md` included
  read-only via toctree. **Both parse under MyST with zero warnings — no
  exclusions were needed**, no construct failed.
- The pre-existing generated `docs/names_registry.md` is included in a
  "Reference" toctree (nav only — the file is untouched); the pre-existing
  `docs/api/README.md` placeholder is excluded via `exclude_patterns` (it is
  superseded as a rendered page by `api/index.md`, and remains in git).
- Build at this commit: exit 0, 4 warnings — all forward references to item C/D
  documents (`api/index` + three tutorial pages), resolved by those items.

### Item C — API reference wiring

- `docs/api/index.md` + 13 group pages, each MyST wrapping `{eval-rst}`
  `automodule` blocks: `core` (context, registry, time, config), `core_state`,
  `core_contracts`, `core_components`, `core_coupling`, `core_plan`,
  `core_functional`, `core_io`, `icon_names`, `icon_thermo`, `icon_grid`,
  `icon_components` (public modules only; `fast/_column_grid` and the constants
  tables excluded by curation), `icon_presets`. `symcon.bridges` excluded per
  prompt. Members are documented at their defining modules; package pages render
  the package docstring without `:members:`, avoiding duplicate-object warnings.
- All curated modules import cleanly under autodoc — **`autodoc_mock_imports` is
  empty/unneeded**.
- Verified: content assert on `api/core.html` (`ExecutionPlan' in t or 'registry' in t`)
  passes. Corpus `` :class:` ` `` role spot-check: `docs/_build/html/api/core.html`
  contains `href="#symcon.core.registry.Factory"` — the role renders as a
  hyperlink.
- Google-section rendering spot-check: **no target exists in the corpus** — the
  packages contain zero `Args:/Returns:/Raises:` sections (grep over
  `packages/*/src`; consistent with plan 27 §2.1's measurement of 0). Napoleon is
  configured and was verified on a synthetic Google docstring in the plan's §2.3
  smoke test; the first in-repo target arrives with the first convert-on-touch
  docstring edit in a future task. Recorded here instead of faked.

### Item D — tutorials T0–T2

- `docs/tutorials/00_what_is_symcon.md`, `01_state_fields_grids.md`,
  `02_first_run_scm.md` per the plan §1 audience contract: science question
  first; 2–3 new terms per page, each linked to the glossary
  (T0: state dictionary, component, run script; T1: property contract, canonical
  units, staggering as API; T2: preset, slow-tendency bus); "everything here
  runs" note with the exact `uv run` command on every page.
- T0 and T2 code is `{literalinclude}` from `examples/01_scm_column.py`
  (`:pyobject: main`, `:pyobject: build_model`, `:lines: 1-14`, `:lines: 29-44`)
  and `packages/symcon-icon/src/symcon/icon/presets/scm.py`
  (`:pyobject: SCMConfig`) — no hand-copied code blocks. T1 uses a 9-line
  interactive transcript whose every output line was produced by actually
  running it in the workspace venv (there is no `examples/` script for state
  inspection; recorded as a deviation-adjacent note, "Deviations" 4).
- T1 math via dollarmath ($v_n = \mathbf v \cdot \mathbf n_e$, $\partial_t T$);
  MathJax markup verified present in the built T1 HTML.
- Factual claims verified by execution: the T2 quoted run summary is the actual
  output of `uv run python examples/01_scm_column.py --hours 1 --output /tmp/t28-scm.nc`
  (38 s wall, < 60 s contract); the "try a wrong order" claim raises
  `CouplingConstraintError` as stated; the xarray plot snippet runs.
- Build: exit 0, **0 warnings** (all literalincludes resolve — a broken include
  would be a build error).

### Item E — GitHub Pages workflow

- `.github/workflows/docs.yml`, artifact flow, structure per the prompt's YAML:
  build job on push-to-main/PR/dispatch runs `uv sync --frozen` + the
  **identical** `sphinx-build -b html docs docs/_build/html` line as local/item B;
  deploy job gated `github.ref == 'refs/heads/main' && github.event_name == 'push'`,
  `permissions: { pages: write, id-token: write }` scoped to the deploy job only.
- One syntactic deviation from the prompt's verbatim block ("Deviations" 2): the
  concurrency group expression is quoted.
- Verified: `yaml.safe_load` passes; `grep "uv sync --frozen"` hits.
- **HUMAN ACTION REQUIRED (one-time, cannot be done or verified locally):** repo
  Settings → Pages → Source: **GitHub Actions**. Also noted in the workflow file
  header; must be restated in the PR body.

### Item F — ruff docstring convention (TD-3) + docs-build CI gate

- `pyproject.toml`: `"D"` added to `[tool.ruff.lint] select`;
  `[tool.ruff.lint.pydocstyle] convention = "google"`; empirical ignore list
  (every entry commented "corpus baseline, plan 27 §4; shrink-only"):
  `D1` (family, 577 findings), `D205` (79), `D209` (66), `D403` (15), `D415` (1).
  See "Deviations" 3 for why two below-threshold rules are present and D401 is not.
- **No docstring was edited anywhere in this task** (`git diff main..HEAD -- packages/`
  is empty).
- `.github/workflows/lint.yml`: added a final "docs build" step running the same
  `sphinx-build` line, no artifact upload.
- Verified: `uv run ruff check .` → `All checks passed!`;
  `uv run ruff format --check .` → `173 files already formatted` (172 baseline +
  the new `docs/conf.py`; no existing file reformatted).

## ruff `D` baseline statistics (the shrink-only ledger)

`uv run ruff check . --select D --statistics` under the final config
(`convention = "google"`, which auto-disables D203/D213 and the
google-excluded rules incl. D400/D401):

```
370  D103  undocumented-public-function
118  D102  undocumented-public-method
 79  D205  missing-blank-line-after-summary
 66  D209  new-line-after-last-paragraph
 42  D107  undocumented-public-init
 30  D105  undocumented-magic-method
 15  D101  undocumented-public-class
 15  D403  first-word-uncapitalized
  2  D100  undocumented-public-module
  1  D415  missing-terminal-punctuation
Found 738 errors.
```

(For the record, the same command *before* the convention was set additionally
reported `83 D401` and `1 D400`; both are disabled by `convention = "google"`
and therefore belong in neither the ignore list nor the baseline.)

## Docs build: final result and warning triage

`uv run sphinx-build -E -b html docs docs/_build/html` on the completed branch:
**exit 0, `build succeeded.`, 0 warnings.** There is consequently no warning
residue to triage; `suppress_warnings` is unset. Interim warning counts during
construction (each explained and resolved): item B — 4 (forward refs to item C/D
docs); item C — 3 (forward refs to item D docs); first item D build — 17
(glossary `(term-x)=` explicit targets do not resolve as `file.md#fragment` ids;
fixed by `myst_heading_anchors = 2` + linking heading slugs, "Deviations" 1).

### Built-site page inventory (22 content pages + generated indices)

| Section | Pages |
|---|---|
| Landing | `index.html` |
| Tutorials | `tutorials/index.html`, `tutorials/00_what_is_symcon.html`, `tutorials/01_state_fields_grids.html`, `tutorials/02_first_run_scm.html` |
| API reference | `api/index.html`, `api/core.html`, `api/core_state.html`, `api/core_contracts.html`, `api/core_components.html`, `api/core_coupling.html`, `api/core_plan.html`, `api/core_functional.html`, `api/core_io.html`, `api/icon_names.html`, `api/icon_thermo.html`, `api/icon_grid.html`, `api/icon_components.html`, `api/icon_presets.html` |
| Architecture (read-only includes) | `architecture/symcon_architecture.html`, `architecture/symcon_repo_layout.html` |
| Reference | `glossary.html`, `names_registry.html` |
| Generated | `genindex.html`, `py-modindex.html`, `search.html` |

## Verification gate (README commands, warm caches)

Partitions split by package/file purely to fit the shell's 10-minute cap; no
test skipped, no marker/`-k`/`--ignore` used beyond the gate's own `-m`
expressions applied per partition.

| Command | Result | Baseline |
|---|---|---|
| fast `-m "not gpu and not slow"` (4 partitions: core; icon ×3) | 409+123+33+174 = **739 passed, 1 skipped** (mpi opt-in) | 739 passed, 1 skipped ✓ |
| `-m "slow and not gpu and not data"` | **31 passed** | 31 ✓ |
| `-m "data and not slow and not gpu"` | **43 passed** | 43 ✓ |
| `-m "data and slow and not gpu"` (5 partitions by file) | **76 passed, 1 skipped** (upstream MCH-only diffusion skip) | 76 passed, 1 skipped ✓ |
| `ruff check .` | `All checks passed!` (with the new `D` config) | ✓ |
| `ruff format --check .` | `173 files already formatted` | 172 + new `docs/conf.py` ✓ |
| `mypy --strict -p symcon.core` | `Success: no issues found in 50 source files` | 50 ✓ |
| `lint-imports` | `Contracts: 2 kept, 0 broken` | ✓ |
| `sphinx-build -E -b html docs docs/_build/html` | exit 0, 0 warnings | — |

data+slow partition detail: `test_static_fields_datatest.py` 55;
`test_diffusion_datatest.py`+`test_nonhydro_datatest.py` 14 + 1 skipped (the
known upstream MCH-only skip); `test_jw_datatest.py`+`test_jw_plan.py` 4;
`test_jw_example.py` 1; `test_jw_plan_equivalence.py` 2.

## Deviations from the prompt (all minimal, all recorded)

1. **`docs/conf.py` has three lines beyond the prompt's block** (config-level
   only, the channel the prompt reserves for triage): `exclude_patterns`
   (`_build` self-ingestion; the pre-existing `api/README.md` placeholder) and
   `myst_heading_anchors = 2` (glossary deep-links; MyST explicit `(target)=`
   ids are not resolvable via `file.md#fragment`, only heading anchors are —
   without this, 17 warnings). No docstring, no architecture file, no content
   was touched to silence anything.
2. **Workflow YAML quoting:** the prompt's verbatim
   `concurrency: { group: pages-${{ github.ref }}, ... }` is invalid YAML
   (`{` inside a plain flow scalar) and fails the prompt's own `yaml.safe_load`
   verify. The expression is quoted (`"pages-${{ github.ref }}"`); semantics
   identical. Prompt-internal contradiction resolved in favor of its
   verification command.
3. **ruff ignore list vs the ">20 findings" recipe:** two rules below the
   threshold, `D403` (15) and `D415` (1), are in the ignore list because the
   prompt's binding outcome — "`ruff check .` green **without any docstring
   edits**" — is unreachable otherwise (and D403's autofix would corrupt
   content: it wants `numpy` → `Numpy`). Conversely `D401` (83 pre-convention)
   is *not* listed: `convention = "google"` disables it, so listing it would be
   dead config. Both directions are empirical, per the plan §4 instruction to
   "measure, list counts, decide per rule".
4. **T1 transcript:** no `examples/` script exists for state inspection, so T1
   carries a 9-line `pycon` transcript instead of a `literalinclude`; every
   line was executed and its output pasted verbatim. The prompt mandates
   literalinclude for **T2's** code (done); the plan's "wherever possible"
   clause covers this.

## Findings (not deviations)

1. **uv universal resolution forks the docs stack by python version.** The lock
   contains `sphinx 8.1.3 / myst-parser 4.0.1 / docutils 0.21.2` for
   `python_full_version < '3.11'` (the workspace floor, the CI python, and this
   machine — i.e. exactly the TD-2 pins) and `sphinx 9.x / myst-parser 5.1.0 /
   docutils 0.22.4` markers for py≥3.11, since the TD-2 lower bounds are floors
   and `constraints/cpu-ci.txt` is consumed by the pip-based `test-cpu.yml` leg,
   not by `uv lock`. Existing pins are untouched. If the trunk wants the lock
   *itself* clamped to 8.1.x for all pythons, that is an upper-bound decision
   (`sphinx>=8.1,<8.2`) it should make explicitly — not taken here.
2. The 4 removed lines in the `uv.lock` diff are this fork's mechanical
   consequence (unversioned `markdown-it-py` dependency entries → two
   version-marked entries); `markdown-it-py` was previously locked at 4.2.0,
   which myst-parser 4.0.1 (py3.10) cannot use — 3.0.0 is selected there.
3. The repo README's "Status: pre-implementation" paragraph is stale (the slice
   exists); out of scope here, noted for a future trunk-owned README refresh.

## For the reviewer

Checklist per the prompt, plus: confirm `git diff main..HEAD -- docs/architecture/`
empty and `git diff main..HEAD -- packages/` empty (no docstring edits);
`constraints/` diff is exactly the four TD-2 pins + one comment line; the T2
literalinclude line ranges (`1-14`, `29-44`) against `examples/01_scm_column.py`.
The one-time Pages→GitHub Actions repo setting remains for a human.
