# Agent Working Agreement (canonical)

You are implementing the ICON-sc architecture. Authority order on any conflict:
`docs/architecture/icon-sc_architecture.md` (v1.3) > `development/work/<NNNN>-<slug>/spec.md`
> `development/work/<NNNN>-<slug>/plan.md`. Never silently resolve a contradiction — record it
in the work unit's report and stop if it blocks acceptance criteria.

## The `development/` tree

`development/` is the repo-internal process memory: policies, registers, ADRs, reference
cards, and the per-unit work documents. Before creating, moving, or renaming any file under
it, read `development/README.md` (the map of the tree); the governing authorities are
`development/policies/repository-layout.md` (layout), `development/policies/naming-conventions.md`
(the `<NNNN>-<slug>/` folder scheme and its exemptions), and
`development/policies/document-kinds.md` (file kinds, frozen vs. living, and the templates).

## Workflow for a work unit

Read the spec fully, then the plan; mine references before writing code; implement with
tests alongside; run the gates; record the outcome in the report
`development/work/<NNNN>-<slug>/report.md` (artifacts, if any, in the `<NNNN>-<slug>/artifacts/` subfolder); one PR per work unit. The full sequence, branch
naming (`work/NNNN-<kebab>`), and the implementer/reviewer loop live in
`development/policies/agent-workflow.md`; the gate battery and baselines in
`development/policies/verification-gates.md`.

## Hard rules

- **No data in git.** Reference datasets via icon4py datatest fixtures or pooch manifests.
- **No dependency bumps.** gt4py/icon4py pins are set in work unit 001's `constraints/`;
  changing them is a trunk decision.
- **No cross-boundary imports.** `icon_sc.core` must not import `icon_sc.icon`/`icon_sc.bridges`
  (import-linter enforces it, in place since work unit 001).
- **No tolerance creep, no reduction-order changes** in equivalence tests (bitwise T0≡T1 is
  required where the spec says bitwise).
- **Python code style.** New source stays under a package's `src/icon_sc/…` (src-layout; see
  `development/policies/repository-layout.md`). `ruff check` / `ruff format` (pyproject
  `[tool.ruff]`) enforce PEP 8, import sorting, and docstring *formatting* (`pydocstyle`
  `convention = "google"`) — keep them green. Three conventions the linter does *not* check;
  uphold them by hand:
  - **Import packages/modules only, never individual classes/functions** (Google style §2.2) —
    `import numpy as np` then `np.array(x)`, not `from numpy import array`.
  - **PEP 8 descriptive naming, capitalizing whole acronyms in CapWords identifiers** —
    `HTTPServerError`, not `HttpServerError`.
  - **Google-style docstring sections on non-trivial public APIs** — `Args:` / `Returns:` /
    `Raises:` / `Yields:` / `Attributes:`, per the [Napoleon Google example](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html#example-google).
    `sphinx.ext.napoleon` is enabled (`docs/conf.py`, `napoleon_google_docstring = True`) and
    renders these; ruff checks docstring *format*, not section presence, so the sections are the
    author's job (TD-27.3: Google sections going forward, existing corpus converted on touch).
- Do not modify `docs/architecture/*` or other work units' specs (`development/work/<NNNN>-<slug>/spec.md`);
  propose changes in your own report.

## Environment

CPU pytest always; MPI up to np=4 (`pytest-mpi`); one CUDA GPU (gpu-marked tests must skip,
not fail, without a device); network access for reference fetching. Long-running reference
generation (e.g., the 0013-diffusion-jw-l4 icon4py driver run) is cached via pooch — never
rerun in CI.

## Reference corpus

Pinned per `development/work/0000-overview/report.md` §3: icon4py, gt4py, ICON
open-source Fortran, sympl (upstream + stubbiali `oop` fork), tasmania, the ICON 2025
tutorial and the Ubbiali thesis. Per-source cards: `development/references/` (local PDFs
go in its gitignored `local/`); mining and `development/references/lock.toml` rules:
`development/policies/reference-mining.md`. When ICON Fortran and icon4py disagree,
icon4py's serialized data is the verification target and the disagreement goes in your
report.
