# Agent Working Agreement (canonical)

You are implementing the symcon architecture. Authority order on any conflict:
`docs/architecture/symcon_architecture.md` (v1.3) > `development/specs/NNN_*_spec.md`
> `development/plans/NNN_*_plan.md`. Never silently resolve a contradiction — record it
in the work unit's record and stop if it blocks acceptance criteria.

## Workflow for a work unit

Read the spec fully, then the plan; mine references before writing code; implement with
tests alongside; run the gates; record the outcome in
`development/records/NNN_*_record/`; one PR per work unit. The full sequence, branch
naming (`work/NNN-<slug>`), and the implementer/reviewer loop live in
`development/policies/agent_workflow.md`; the gate battery and baselines in
`development/policies/verification_gates.md`.

## Hard rules

- **No data in git.** Reference datasets via icon4py datatest fixtures or pooch manifests.
- **No dependency bumps.** gt4py/icon4py pins are set in work unit 001's `constraints/`;
  changing them is a trunk decision.
- **No cross-boundary imports.** `symcon.core` must not import `symcon.icon`/`symcon.bridges`
  (import-linter enforces it, in place since work unit 001).
- **No tolerance creep, no reduction-order changes** in equivalence tests (bitwise T0≡T1 is
  required where the spec says bitwise).
- Do not modify `docs/architecture/*` or other work units' specs (`development/specs/`);
  propose changes in your own record.

## Environment

CPU pytest always; MPI up to np=4 (`pytest-mpi`); one CUDA GPU (gpu-marked tests must skip,
not fail, without a device); network access for reference fetching. Long-running reference
generation (e.g., the 013_diffusion_jw_l4 icon4py driver run) is cached via pooch — never
rerun in CI.

## Reference corpus

Pinned per `development/records/000_overview_record.md` §3: icon4py, gt4py, ICON
open-source Fortran, sympl (upstream + stubbiali `oop` fork), tasmania, the ICON 2025
tutorial and the Ubbiali thesis. Per-source cards: `development/references/` (local PDFs
go in its gitignored `local/`); mining and `REFERENCES.lock` rules:
`development/policies/reference_mining.md`. When ICON Fortran and icon4py disagree,
icon4py's serialized data is the verification target and the disagreement goes in your
record.
