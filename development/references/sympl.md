# sympl

**Source:** https://github.com/mcgibbon/sympl (upstream) + fork
https://github.com/stubbiali/sympl, branch `oop`
**Pinned:** upstream `512809ef35d2daf898b8747a717271ed4d2b684d`; `oop` fork
`5491978331ef7d6b7dc7995b9a5726713b5de7a7` — corpus pins, see `development/references/lock.toml`
(not a package dependency; not in `constraints/`).
**License:** not recorded

## Role in the project

Component/property semantics donor; the `out=`/Checker/Operator/Factory mechanisms
(architecture §4.2). Upstream supplied property/units semantics (pint registry,
cftime-aware datetime factory); the fork supplied the Checker/Operator/Factory and
component-ABI shapes (`array_call`, allocate hooks, UpdateFrequencyWrapper,
ScalingWrapper).

## Gotchas

- Two repos: the OOP mechanisms live in the **stubbiali `oop` fork**, not upstream —
  consult the right one per topic.
- symcon deviations recorded at mining time: implicit any-unit conversion dropped in
  favor of canonical units + strict mode (S02); single flat `out=` mapping instead of
  `out_tendencies`/`out_diagnostics`/`out_state` (frozen S03 interface);
  `tendencies_in_diagnostics`/TracerPacker not ported.

## Consultation ledger

`grep -n 'id = "sympl' development/references/lock.toml` — covers both `sympl` and `sympl-oop` ids.
