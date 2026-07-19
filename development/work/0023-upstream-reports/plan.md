# Task 23 — Draft the upstream icon4py reports (writing task; no product code)

**Branch:** `task/23-upstream-reports` (from `main`; verify `git branch
--show-current` before every commit). **Scope: writing three report drafts into
`development/records/023_upstream_reports_record/` — you change NO product code and NO tests.** The
drafts are for a human to review and submit to github.com/C2SM/icon4py; you do NOT
open issues yourself.

## Hard rules

- Every technical claim in a draft must cite its in-repo evidence (file:line of the
  committed test or STATUS section) AND the upstream source at the pinned tag
  v0.2.0 = `28d32c45afb4dbea1da6b6e5170202f08b4adb88` (file:line). If you cannot
  verify a claim from those sources, leave it out — no memory, no invention.
- Reproduce every number you quote by actually running the cited test or reading
  the cited STATUS. Do not copy numbers you have not seen produced.
- Style: factual, minimal, upstream-maintainer-friendly. Reproduction steps must
  be runnable with icon4py alone (no ICON-sc imports) wherever a wrapper-free
  reproduction exists.

## Draft 1 — `graupel_cold_glaciation_budget_leak.md`

Source material: `development/work/reports/report-0008-graupel-component.md` (the leak dossier and
its Review-fixes round), and the committed wrapper-free reproduction
`test_cold_leak_reproduces_in_bare_granule` in
`packages/icon-sc-icon/tests/test_graupel_component.py` (read `_raw_granule_budget_defect`
— it uses only public icon4py APIs; translate it into a standalone snippet for the
report). Content: symptom (fixed absolute column water-path leak ~1.6e-4 kg/m² per
30 s step at reference conditions, growing to ~1.05e-3 kg/m² at qv_scale=0.1;
relative worst 4.32e-4 at the dry edge), trigger (supercooled qc at T≲233 K, no
coexisting ice-phase hydrometeor above QMIN), suppression conditions, the
measured-not-theorized characterization method, and the runnable reproduction.
RUN the cited test once (`uv run pytest packages/icon-sc-icon/tests/test_graupel_component.py::test_cold_leak_reproduces_in_bare_granule -q`)
and quote its pass line.

## Draft 2 — `wgtfacq_shifted_k_domain_footgun.md`

Source material: `development/work/reports/report-0013-diffusion-jw-l4.md` (the root-cause
narrative), `development/work/reports/report-0012-nonhydro-hosting.md` §5 (the original dossier +
reviewer refinements), development/references/lock.toml entry `icon4py-wgtfacq-domain`, and the fix
commit `2c0b569`. Content: NOT a bug report — a documentation/API-hardening
suggestion. The facts: `wgtfacq_c`/`wgtfacq_e` are 3-level fields registered on
K-domain `[num_levels−3, num_levels)` (metrics factory, cite the registration
lines) while the serialized savepoints shift them likewise (cite serialbox reader
lines); consumers reading them through a rebuilt `[0,3)` field silently go out of
domain, producing heap-dependent, rebuild-nondeterministic corruption that
masquerades as pentagon-point trouble. Suggestion for upstream: an assertion or
documented convention on domain-carrying metric fields (concrete proposal: the
factory could expose the expected K-range in field metadata, or `dallclose`-style
test helpers could verify domain anchors). Include the symptom signature
("bitwise-unequal identical rebuilds; deviations seeded near special points") so
future victims can find the report.

## Draft 3 — `minor_divergences_vs_icon_2026_04.md`

A short omnibus of verified, low-severity divergences between icon4py v0.2.0 and
ICON icon-2026.04-public (`8597da45…`, gitlab.dkrz.de mirror), each with both
citations, from the STATUS files of S06/S07/S08/S12:
`SPECIFIC_HEAT_CAPACITY_ICE=2108.0` vs Fortran `ci=2106.0_wp`
(mo_physical_constants.f90:213; dead code under `use_constant_latent_heat=True`);
satad supersaturation factor `tune_supsat_limfac` + `w` input present in Fortran,
absent in icon4py (identical under default namelist); satad silent
`count < maxiter` cap vs icon4py `ConvergenceError`; the multi-substep dycore test
being MCH-only (the literal `# why is this not run for APE?` comment at
test_solve_nonhydro.py:784) with our measured APE deviations (4.85e-12/7.19e-12 vn)
as a data point upstream may want.

## Acceptance criteria

1. Three drafts committed under `development/records/023_upstream_reports_record/`, every claim
   double-cited (in-repo + upstream file:line at the pinned SHA).
2. Draft 1's reproduction snippet is icon4py-only (no ICON-sc import) and you have
   verified it runs (`uv run python <<the snippet>>` in a scratch file under /tmp)
   producing the reported magnitudes.
3. No product/test/doc file outside `development/records/023_upstream_reports_record/` is touched.
4. Full fast gate untouched-green as a formality:
   `uv run pytest packages -m "not gpu and not slow" -q` matches the current
   baseline (see README; may be 733 if Task 21 merged first — check `git log`).

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Spot-check ≥2 upstream citations per draft by opening the pinned sources
  (clone/fetch at the SHA if needed) and comparing line contents.
- Run Draft 1's snippet yourself; the numbers must reproduce within the stated
  bounds (they are deterministic).
- `git diff main..HEAD --stat`: only files under `development/records/023_upstream_reports_record/`.
  Anything else is a MAJOR finding.
- Check every number in the drafts against its cited source; an uncited or
  unreproducible number is a MAJOR finding (these documents leave the repo — they
  carry our credibility).
