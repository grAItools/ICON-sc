# coding-conventions — Python style for source code

Scope: the conventions Python source under `packages/*/src` (and the test suites) follows,
beyond what tooling auto-enforces. Tool config lives in `pyproject.toml` (`[tool.ruff]`,
`[tool.mypy]`); the src-layout and packaging boundaries in `repository-layout.md`; the gate
that runs the checks in `verification-gates.md`. This file is the home for the *human-upheld*
rules an agent applies when writing or reviewing code — the ones the linter cannot enforce.

## Enforced by tooling — obey, don't restate

`ruff check` / `ruff format` (run in the gate and in pre-commit) already enforce:

- **PEP 8** style and formatting: pycodestyle `E`, pyflakes `F`, pyupgrade `UP`, bugbear `B`,
  simplify `SIM`, Ruff `RUF`; line length 100.
- **Import sorting**: isort `I` (first-party `icon_sc`).
- **Google docstring *formatting***: pydocstyle `D` with `convention = "google"` (a shrink-only
  ignore baseline covers the legacy narrative-prose corpus — see `pyproject.toml`).
- **src-layout**: importable code lives under `packages/<dist>/src/icon_sc/…`
  (`repository-layout.md`).

`mypy --strict -p icon_sc.core` type-checks the core (icon / bridges tighten later).

## Upheld by hand — the linter does NOT check these

1. **Import packages and modules, not individual names** (Google Python style guide §2.2):
   `import numpy as np` then `np.array(x)`, not `from numpy import array`. Standard exceptions:
   `from __future__ import …`; typing constructs (`from typing import …`,
   `from collections.abc import …`); and a package's own curated public re-exports in its
   `__init__.py`. Importing types/classes purely for annotations is the pragmatic exception the
   corpus already takes; prefer a module import wherever a runtime callable is invoked.

2. **Capitalize whole acronyms in CapWords identifiers** (PEP 8 descriptive naming) — classes,
   type aliases, exceptions: `HTTPServerError`, not `HttpServerError`. The corpus already does
   this (`JWConfig`, `SCMConfig`, `NetCDFMonitor`, `SSUS`). In snake_case names acronyms are
   lower-cased (`read_grib_file`, `grid_uuid`), so the rule is CapWords-only. `Icon…` is a
   deliberate project-wide exception (package `icon_sc`, subpackage `icon_sc.icon`, project
   "ICON-sc").

3. **Google-style docstring sections on non-trivial public APIs** — `Args:` / `Returns:` /
   `Raises:` / `Yields:` / `Attributes:`, per the [Napoleon Google example][napoleon].
   `sphinx.ext.napoleon` is enabled (`docs/conf.py`, `napoleon_google_docstring = True`) and
   renders them; ruff checks docstring *format*, not section presence, so the sections are the
   author's responsibility. Existing narrative-prose docstrings are converted on touch
   (TD-27.3). Once an `Args:` section exists, ruff `D417` requires *every* parameter to be
   documented — so write the sections completely, not partially.

[napoleon]: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html#example-google
