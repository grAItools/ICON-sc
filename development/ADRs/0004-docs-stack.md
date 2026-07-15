# 047 — Documentation stack: Sphinx + MyST + Napoleon + furo (retroactive)

**Status:** accepted · **Date:** 2026-07-14 (decision 2026-07-13, TD-27.1–3;
recorded retroactively by work unit 035)

## Context

Work unit 027 evaluated documentation stacks for the published site
(`development/work/reports/report-0027-docs-plan.md`; decisions TD-27.1–3,
signed off and executed by work unit 028). The measured constraint: the existing
docstring corpus (78 module docstrings, 346 public-API docstrings) is
Sphinx-flavored narrative — it renders natively under Sphinx (roles → links,
verified) and visibly degrades under griffe-based stacks; bulk-rewriting audited,
provenance-bearing docstrings is exactly the mass-touch event the working agreement
exists to prevent.

## Decision

- **Stack (TD-27.1):** Sphinx + MyST-Parser + Napoleon + furo. MyST gives Markdown
  authoring for hand-written pages; Napoleon parses Google `Args:/Returns:` sections
  while leaving existing narrative prose and its roles untouched. The layout-doc line
  "`docs/api/` # sphinx + autodoc from py.typed sources" is complied with as written.
- **Pins (TD-27.2):** dev-group lower bounds `sphinx>=8.1`, `myst-parser>=4.0`,
  `furo>=2025.12.19`; `constraints/cpu-ci.txt` pins sphinx==8.1.3, myst-parser==4.0.1,
  furo==2025.12.19, docutils==0.21.2 (verified pair, 2026-07-13). Sphinx ≥ 8.2
  requires Python ≥ 3.11; the workspace floor is 3.10, hence 8.1.x — revisit when the
  floor moves.
- **Deploy:** GitHub Pages via the artifact flow ("Pages → Source: GitHub Actions",
  workflow per 027 §5 item E) — plain static HTML, no gh-pages branch.
- **Docstrings (TD-27.3):** Google-style sections going forward, Napoleon-parsed;
  the existing corpus is kept, **convert-on-touch** (add Google sections when a change
  substantively edits a public docstring; never as a drive-by). Enforcement via ruff
  `D` (`convention = "google"`) with an explicit ignore baseline that only ever
  shrinks.

## Consequences

- Every docs contribution follows this stack; hand-written pages are MyST Markdown,
  API pages are autodoc from py.typed sources.
- `uv.lock`/constraints additions for docs are covered by TD-27.2; further docs
  dependencies (sphinx-copybutton, myst-nb, …) are deliberately out of the first
  iteration and need their own decision.
- The docs build is a gate (`sphinx-build -E -W --keep-going` exits 0).

## Alternatives considered (027 §2–3)

- **MkDocs + Material + mkdocstrings:** rejected, not deferred — MkDocs 2.0
  "no migration path" warning (verified), mkdocstrings/griffe major-version churn,
  and measured corpus degradation; overruling requires funding a re-reviewed bulk
  conversion of all 346 docstrings' role syntax.
- **Quarto + quartodoc:** best pure-tutorial engine, but a ~150 MB system binary that
  cannot be pinned via `constraints/*.txt`, plus the same corpus degradation —
  rejected on the same governance grounds.
