# Agent Working Agreement (canonical)

You are implementing the ICON-sc architecture. Authority order on any conflict:
`docs/architecture/icon-sc_architecture.md` (v1.3) > `development/work/specs/spec-NNNN-*.md`
> `development/work/plans/plan-NNNN-*.md`. Never silently resolve a contradiction — record it
in the work unit's report and stop if it blocks acceptance criteria.

## Workflow for a work unit

Read the spec fully, then the plan; mine references before writing code; implement with
tests alongside; run the gates; record the outcome in the report
`development/work/reports/report-NNNN-*.md` (artifacts, if any, in the sibling folder `report-NNNN-*/`); one PR per work unit. The full sequence, branch
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
- Do not modify `docs/architecture/*` or other work units' specs (`development/work/specs/`);
  propose changes in your own report.

## Environment

CPU pytest always; MPI up to np=4 (`pytest-mpi`); one CUDA GPU (gpu-marked tests must skip,
not fail, without a device); network access for reference fetching. Long-running reference
generation (e.g., the 0013-diffusion-jw-l4 icon4py driver run) is cached via pooch — never
rerun in CI.

## Reference corpus

Pinned per `development/work/reports/report-0000-overview.md` §3: icon4py, gt4py, ICON
open-source Fortran, sympl (upstream + stubbiali `oop` fork), tasmania, the ICON 2025
tutorial and the Ubbiali thesis. Per-source cards: `development/references/` (local PDFs
go in its gitignored `local/`); mining and `development/references/lock.toml` rules:
`development/policies/reference-mining.md`. When ICON Fortran and icon4py disagree,
icon4py's serialized data is the verification target and the disagreement goes in your
report.
