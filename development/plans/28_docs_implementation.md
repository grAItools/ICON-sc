<!-- Lifted from development/records/27_docs_plan/27_docs_plan.md §5 (task 27).
     Trunk sign-off on TD-1/TD-2/TD-3: granted by the project owner on 2026-07-13
     ("proceed with the docs implementation plan"). -->

# Task 28 — Documentation build: Sphinx + MyST site, API reference, first tutorials, Pages deploy

**Branch:** `task/28-docs-implementation` (from `main`; verify
`git branch --show-current` before every commit). One commit per item A–F below
(6 commits + report). **Prerequisite:** trunk sign-off on TD-1/TD-2/TD-3 of
`development/records/27_docs_plan/27_docs_plan.md` (this task implements that
plan; do not re-litigate the stack choice).

## Hard rules (restated; full list in development/plans/README.md)

- No tolerance changes. No data in git. Do not edit `docs/architecture/*` (the
  tutorials and toctrees may *include* those files read-only, never modify them),
  any SPEC/PLAN, or completed steps' STATUS files.
- Dependency additions are exactly the TD-2 list (three dev-group lower bounds +
  four constraints pins) — this task is the explicit grant the prompts-README
  requires. NOTHING else may change in `constraints/*.txt`; gt4py/icon4py/jax pins
  are untouchable. If `uv lock` reports a conflict between the docs pins and the
  existing locked set, STOP and report — resolving it is a trunk decision.
- **Never edit a docstring to silence a Sphinx warning or a ruff `D` finding** in
  this task. Warnings are triaged by config (`suppress_warnings`, per-rule ruff
  ignores), and counts are recorded in the report. Docstring content changes are
  out of scope here (convert-on-touch policy, §4 of the plan).
- Each item has an exact scope. If an item needs more than described, STOP on it,
  mark it "blocked — needs trunk decision" in your report, continue with the others.

## Item A — tooling config + dependencies

**Change:** add the TD-2 dev-group entries to the root `pyproject.toml` and the four
pins to `constraints/cpu-ci.txt` (comment: "task 28: docs build — plan
27_docs_plan §3.3"); run `uv lock` (lockfile grows, existing pins unchanged —
verify with `git diff uv.lock | grep -E '^[-]' | grep -v "^---"` showing no removed
version lines for gt4py/icon4py/jax). Create `docs/conf.py`:

```python
project = "symcon"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "myst_parser",
]
napoleon_google_docstring = True
napoleon_numpy_docstring = False
myst_enable_extensions = ["dollarmath", "colon_fence"]
autodoc_typehints = "description"
autodoc_member_order = "bysource"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
html_theme = "furo"
```

No `sys.path` manipulation — autodoc imports the *installed* workspace packages
(verified: `uv run python -c "import symcon.core, symcon.icon"` succeeds).

**Verify:**
```
uv run python -c "import sphinx, myst_parser, furo; print(sphinx.__version__)"   # 8.1.3
uv run sphinx-build -b html docs docs/_build/html                                 # succeeds (item B provides index)
```
**Stop rule:** items B–F depend on A; if A blocks, the task blocks.

## Item B — site skeleton + nav

**Change:** create `docs/index.md` (landing: what symcon is, install, links),
`docs/tutorials/index.md` (curriculum T0–T8 as titles; T0–T2 linked, T3–T8 marked
"planned" with their §1.2 abstracts), `docs/glossary.md` (seed with the terms
introduced by T0–T2), and a toctree that includes `docs/architecture/*.md`
**read-only** (if MyST chokes on a construct in those files, do NOT edit them —
exclude the file from the toctree, link it on GitHub instead, and record which
construct failed). Add `docs/_build/` to `.gitignore`.

**Verify:** `uv run sphinx-build -b html docs docs/_build/html` — zero *errors*
(warnings recorded); `docs/_build/html/index.html` exists; architecture pages
render or are recorded as excluded.

## Item C — API reference wiring

**Change:** `docs/api/index.md` plus one page per curated module group, each a MyST
file wrapping `{eval-rst}` `automodule` blocks with `:members:`. Curated set for
this task (not full coverage): `symcon.core` top-level (`context`, `registry`,
`time`, `config`), `symcon.core.state`, `symcon.core.contracts`,
`symcon.core.components`, `symcon.core.coupling`, `symcon.core.plan`,
`symcon.core.functional`, `symcon.core.io`; `symcon.icon.presets`,
`symcon.icon.names`, `symcon.icon.thermo`, `symcon.icon.grid`,
`symcon.icon.components` (public modules only). `symcon.bridges` is out (optional
toolchain).

**Verify:**
```
uv run sphinx-build -b html docs docs/_build/html 2>&1 | tee /tmp/t28-build.log
grep -c "WARNING" /tmp/t28-build.log     # record the count in the report; do not chase to zero
python -c "import pathlib; t=pathlib.Path('docs/_build/html/api/core.html').read_text(); assert 'ExecutionPlan' in t or 'registry' in t"
```
Spot-check in the built HTML (record in report): one page where a `` :class:` ` ``
role from the existing corpus renders as a hyperlink, and (after item D exists or
via `symcon.core.testing` if it has one) any Google-section docstring rendering as
Parameters/Returns. **Stop rule:** if a module *import* fails under autodoc (e.g.,
an optional dep missing in your env), add it to `autodoc_mock_imports` and record —
never restructure the module.

## Item D — tutorials T0–T2

**Change:** `docs/tutorials/00_what_is_symcon.md`, `01_state_fields_grids.md`,
`02_first_run_scm.md` per the abstracts and audience contract of plan §1. All code
shown for T2 comes from `examples/01_scm_column.py` via `{literalinclude}` with
`:lines:`/`:pyobject:` selectors — no hand-copied code blocks. Each page: the 2–3
new-term budget, glossary links, an "everything here runs" note with the exact
`uv run` command. Math via dollarmath where equations help (T1: unit/staggering
examples).

**Verify:** build clean as in B; every `literalinclude` resolves (a broken include
is a Sphinx error, not a warning); the T2 command `uv run python
examples/01_scm_column.py --hours 1 --output /tmp/t28-scm.nc` still runs (<60 s —
it is CI-smoked, this is a sanity re-run, not a new gate).

## Item E — GitHub Pages workflow

**Change:** `.github/workflows/docs.yml`, artifact flow (NOT a gh-pages branch —
built HTML in a git branch collides with the repo's no-generated-artifacts/no-data
discipline, and the artifact flow needs no branch protection carve-outs):

```yaml
name: docs
on:
  push: { branches: [main] }
  pull_request:
  workflow_dispatch:
concurrency: { group: pages-${{ github.ref }}, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run sphinx-build -b html docs docs/_build/html
      - uses: actions/upload-pages-artifact@v3
        with: { path: docs/_build/html }
  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: build
    permissions: { pages: write, id-token: write }
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Repo setting "Pages → Source: GitHub Actions" is a human/one-time action — note it
in the report and the PR body; you cannot verify deployment locally.

**Verify:** `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/docs.yml'))"`;
`grep -n "uv sync --frozen" .github/workflows/docs.yml`. Confirm the build job's
sphinx invocation is *identical* to the local one from item B.

## Item F — ruff docstring convention (TD-3) + docs-build CI gate

**Change (two parts, one commit):**
1. `pyproject.toml`: add `"D"` to `[tool.ruff.lint] select`, add
   `[tool.ruff.lint.pydocstyle] convention = "google"`, and an `ignore` list built
   empirically: run `uv run ruff check . --select D --statistics`, put `D1xx`
   and every rule with >20 findings into `ignore` with a one-line comment each
   ("corpus baseline, plan 27 §4; shrink-only"). The final `uv run ruff check .`
   must be green **without any docstring edits**.
2. CI: extend `.github/workflows/lint.yml` with a docs-build step (same
   `sphinx-build` line, no artifact upload) so a PR that breaks the docs build
   fails lint, not just the decorative docs workflow.

**Verify:**
```
uv run ruff check .                       # All checks passed!
uv run ruff format --check .              # unchanged count
uv run ruff check . --select D --statistics   # paste into report (the baseline)
```

## Acceptance criteria

1. Items A–F done exactly as scoped (or explicitly reported blocked), one commit
   each, per-item verifications recorded.
2. `uv run sphinx-build -b html docs docs/_build/html` exits 0 from a clean
   checkout of the branch; warning count recorded and justified.
3. Full README gate green with **unchanged** test baselines (this task adds no
   tests and must not change any counts); ruff gates green with the new `D` config.
4. `git diff main..HEAD --stat` touches ONLY: `pyproject.toml`, `uv.lock`,
   `constraints/cpu-ci.txt`, `.gitignore`, `docs/**` (new files; `docs/architecture/`
   byte-identical), `.github/workflows/docs.yml`, `.github/workflows/lint.yml`, and
   the report `development/records/28_docs_implementation_REPORT.md`.
5. Report includes: built-site page inventory, warning triage table, ruff `D`
   baseline statistics, the "Pages → GitHub Actions" human action item.

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Re-run the docs build yourself from a clean venv (`uv sync --frozen` first);
  confirm exit 0 and that the warning count matches the report.
- Open the built HTML: verify (i) a corpus `` :class:` ` `` role rendering as a
  link, (ii) a Google-section docstring rendering structured, (iii) T2's included
  code matching `examples/01_scm_column.py` byte-for-byte at the cited lines,
  (iv) math rendering on T1.
- `git diff main..HEAD -- docs/architecture/` MUST be empty. Any docstring diff in
  `packages/` is a MAJOR finding (this task edits no docstrings).
- `git diff main..HEAD -- constraints/` shows exactly the four TD-2 additions;
  `uv.lock` diff removes no existing pin (check gt4py/icon4py/jax lines survive).
- Confirm no test-baseline drift: run the fast gate; counts must equal the
  prompts-README baselines current at branch time.
- Workflow hygiene: deploy job gated on `main` push; `permissions` scoped to the
  deploy job only; build job runs on PRs.

---
*(end of liftable task text)*
