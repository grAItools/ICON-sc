# Agent Working Agreement (canonical)

You are implementing the symcon architecture. Authority order on any conflict:
`docs/architecture/symcon_architecture.md` (v1.3) > step `SPEC.md` > step `PLAN.md`.
Never silently resolve a contradiction — record it in the step's `STATUS.md` and stop if it
blocks acceptance criteria.

## Workflow for a step

1. Pick a step whose dependencies are merged (DAG: `plan/00_OVERVIEW.md` §2). Branch: `step/SXX-short-name`.
2. Read `SPEC.md` fully, then `PLAN.md`. SPEC's *Frozen interfaces* are load-bearing for
   concurrent lanes: implement them exactly; if a signature must change, that is a trunk
   decision, not a local fix.
3. **Mine references before writing code.** Candidate module paths in PLANs are hints —
   icon4py/gt4py reorganize; discover the real paths, then append an entry to
   `REFERENCES.lock` for every source consulted (schema in that file). Scientific constants
   and algorithm structure come from references, never from memory or improvisation.
4. Implement. Tests alongside. Tolerances stated in SPECs are contracts: loosening one
   requires a written justification in `STATUS.md` and human sign-off in the PR.
5. Gate before PR: step acceptance tests green; `pytest -m "not gpu"` green (add `gpu`/`mpi`
   markers per SPEC); `ruff check` + `ruff format --check`; `mypy` strict on `symcon-core`;
   `lint-imports`. (Until S01 lands, only the subset that exists applies.)
6. Write `plan/steps/SXX_*/STATUS.md`: what was built, deviations + why, follow-ups,
   benchmark/plot artifacts if the SPEC asks. One PR per step; fill the PR template.

## Hard rules

- **No data in git.** Reference datasets via icon4py datatest fixtures or pooch manifests.
- **No dependency bumps.** gt4py/icon4py pins are set in S01's `constraints/`; changing them
  is a trunk decision.
- **No cross-boundary imports.** `symcon.core` must not import `symcon.icon`/`symcon.bridges`
  (import-linter enforces from S01 onward).
- **No tolerance creep, no reduction-order changes** in equivalence tests (bitwise T0≡T1 is
  required where the SPEC says bitwise).
- Do not modify `docs/architecture/*` or other steps' SPECs; propose changes in `STATUS.md`.

## Environment

CPU pytest always; MPI up to np=4 (`pytest-mpi`); one CUDA GPU (gpu-marked tests must skip,
not fail, without a device); network access for reference fetching. Long-running reference
generation (e.g., the S13 icon4py driver run) is cached via pooch — never rerun in CI.

## Reference corpus

Pinned per `plan/00_OVERVIEW.md` §3: icon4py, gt4py, ICON open-source Fortran, sympl
(upstream + stubbiali `oop` fork), tasmania, the ICON 2025 tutorial and the Ubbiali thesis
(drop local PDFs into `references/`, see its README). When ICON Fortran and icon4py disagree,
icon4py's serialized data is the verification target and the disagreement goes in `STATUS.md`.
