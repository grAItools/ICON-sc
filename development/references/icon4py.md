# icon4py

**Source:** https://github.com/C2SM/icon4py
**Pinned:** v0.2.0 (tag `28d32c45afb4dbea1da6b6e5170202f08b4adb88`); pin decided in
`constraints/cpu-ci.txt` (all `icon4py-*` distributions == 0.2.0; S01 pin decision).
**License:** not recorded

## Role in the project

Primary implementation donor: dycore/diffusion/microphysics granules,
grid/metrics/interpolation factories, serialbox datatest fixtures, JW driver
experiment. Its serialized reference data is the verification target when ICON
Fortran and icon4py disagree (working agreement, `AGENTS.md`).

## Gotchas

- v0.2.0 is the latest tagged release and every subpackage distribution is on PyPI at
  0.2.0; its published metadata pins `gt4py==1.1.10` exactly — that is the tested
  pair. Repo HEAD at mining time pinned gt4py==1.1.11: pin the released pair, not HEAD.
- Import root is `icon4py.model.common`; GPU extra spelling:
  `icon4py-common[cuda12]` → `cupy-cuda12x>=13.0` + `gt4py[cuda12]`.
- Datatest machinery: `TESTDATA_ROOT_URL=https://rgw.cscs.ch/c2sm:testdata`,
  `ICON4PY_TEST_DATA_PATH` env var; archive sizes range from GAUSS3D 57 MB to
  JW/MCH multi-GB (see `development/policies/verification_gates.md` caches).
- `icon4py-testing` 0.2.0 requires `serialbox4py>=2.6.2` and imports the
  diffusion/dycore/microphysics/standalone-driver packages at import time.

## Consultation ledger

`grep -n 'id = "icon4py' REFERENCES.lock` — one `[[ref]]` entry per consultation.
