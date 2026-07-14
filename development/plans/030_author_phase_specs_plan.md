# Task 30 — Author SPEC/PLAN step folders for the next phase (design writing)

**Branch:** `task/30-specs-<phase>` (e.g. `task/30-specs-p2`). **Precondition: a
human names the phase** (one of P2–P7; the natural next choices are P2 distributed
or P5 tiers T2/T3, both unblocked by S14 — P3 physics is unblocked too and
parallelizable per scheme). Do not pick the phase yourself; if none was named in
your instructions, STOP and ask.

**Scope: writing SPEC.md + PLAN.md files only.** No product code, no tests, no
edits to existing steps. The output is a trunk-review artifact: a human approves
the SPECs before any implementation prompt is issued against them.

## Inputs (read fully, in this order)

1. `development/ideas/<phase>.md` — the frozen scope sketch (your contract: cover
   everything it names; add nothing it doesn't, except mechanically implied glue).
2. `docs/architecture/symcon_architecture.md` — ONLY the §§ the outline cites.
3. `development/records/000_overview_record.md` §1 (agent contract) and 2–3 EXISTING step folders as
   templates — the best exemplars are `development/{specs,plans}/S05_vault_plan_t1.md`,
   `development/{specs,plans}/S08_graupel_component.md`, `development/{specs,plans}/S12_nonhydro_hosting.md`
   (read their SPEC.md + PLAN.md; your files must match their structure, register,
   and level of detail).
4. `development/records/036_implementation_report_record.md` §4–§6 — the findings and follow-ups your SPECs
   must not contradict and should, where relevant, absorb (e.g. any P5 SPEC must
   require config digests in compiled-artifact cache keys per the S05/S22 line;
   any P2 SPEC must state the exchange-transpose test obligations of §8.7 if it
   touches them).

## Structure to produce (per step; mirror the existing folders exactly)

`development/specs/SXX_<snake_name>.md`:
- Header: `# SXX — <title>` + `**Lane:** ... · **Depends on:** <steps> ·
  **Unblocks:** <steps>` (derive the DAG from the outline; when in doubt make
  dependencies MORE conservative, never less).
- `## Goal` — 2–4 sentences, outcome-shaped.
- `## In scope` / `## Out of scope` — bullets; the out-of-scope list is a drift
  fence for weak implementers: name the tempting adjacent work explicitly.
- `## Frozen interfaces (later steps import these)` — exact Python signatures.
  Every signature you freeze must name its types precisely and be minimal; a
  frozen interface is a promise other lanes build against concurrently.
- `## Acceptance criteria` — numbered, each one MECHANICALLY CHECKABLE by a
  command or a named test property. Rules learned from S01–S14 (binding):
  - every numeric tolerance must carry its provenance (the upstream test or a
    "characterize-and-flag-for-sign-off" instruction — never a bare invented
    number);
  - anything long-running must state its caching policy (pooch/manifest; "CI
    never reruns");
  - anything gpu/mpi must state the skip-cleanly requirement AND that first real
    execution must be recorded;
  - bitwise claims must say bitwise and name the comparison
    (`assert_array_equal`);
  - include the fast-gate budget criterion if the step adds fast-tier tests.

`development/plans/SXX_<snake_name>.md`:
- Numbered task ordering starting with **reference mining** (name candidate repos/
  paths AS HINTS and say so — the S01–S14 convention that paths are discovered,
  not trusted, and every source lands in REFERENCES.lock at mining time).
- A `**Pitfalls:**` paragraph. Mine `development/records/036_implementation_report_record.md` §4 for
  phase-relevant traps (e.g. for P2: background-child survival, chunk-resume via
  restart protocols, np=4 CI budget; for P5: domain-carrying fields — the wgtfacq
  lesson — and config-digest cache keys; for P3: the S07/S08 hosting pattern,
  scheme-constants modules, upstream tolerance citation discipline).

## Sizing rules

- One step = one PR = roughly the S07/S08/S12 size (a hosted component + its
  verification, or one infrastructure seam + its negative-test suite). If an
  outline item doesn't fit, split it and add the DAG edge.
- Every step must name its verification data source (existing cached archives
  where possible — new archives need a size estimate and the cache-only rule).

## Acceptance criteria (for THIS task)

1. Every item in the phase outline maps to exactly one step folder (build the
   mapping table in your report; unmapped outline text = incomplete task).
2. Each SPEC/PLAN passes the structural checklist above — self-audit each file
   against it and include the checklist per step in your report.
3. The DAG is stated in every SPEC header and is acyclic; a proposed update to
   `development/records/000_overview_record.md` §2's mermaid graph is included in your report AS A DIFF
   SNIPPET ONLY (do not edit 00_OVERVIEW.md — trunk applies it at approval).
4. No file outside `development/{specs,plans}/<new files>` and your report is touched. The
   full fast gate still passes untouched (formality; run once).
5. Report `development/records/30_specs_<phase>_REPORT.md`: mapping table,
   per-step checklists, open design questions EXPLICITLY listed for the human
   trunk review (do not bury uncertainty inside confident-sounding SPEC text —
   an honest "TRUNK DECISION NEEDED:" marker inside a SPEC is the correct way to
   flag an unresolved choice).

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Verify outline coverage independently: read the outline, list its items, check
  each against the step folders WITHOUT looking at the implementer's mapping
  table first; then diff your list against theirs.
- For every frozen interface: is it minimal, typed, and consistent with the
  existing S02–S14 surfaces it extends? Grep the existing code for name
  collisions.
- For every acceptance criterion: is it mechanically checkable as written? Reject
  vague criteria ("works correctly", "reasonable performance") as MAJOR findings.
- For every tolerance: provenance stated? Bare numbers without an upstream
  citation or a characterize-and-sign-off instruction are MAJOR findings.
- Check the DAG for cycles and for optimistic edges (a step depending on less
  than it actually imports is MAJOR; depending on more is INFO).
- Confirm `git diff main..HEAD --stat` touches only new step folders + the report.
