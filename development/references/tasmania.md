# tasmania

**Source:** https://github.com/stubbiali/tasmania
**Pinned:** `75b46ac0737c88ea201274692ab6883e803efb29` — corpus pin, see
`REFERENCES.lock` (not a package dependency; not in `constraints/`).
**License:** not recorded

## Role in the project

Federation classes, `DynamicalCore`, `SequentialTendencyStepper` reference
implementations: ConcurrentCoupling serial policy, PS/STS/SUS federations, the
tendency-stepper factories, the Timer, and the op-algebra kernel set the S05 plan
ops generalize.

## Gotchas

- tasmania's `rk2` is the **midpoint** scheme; symcon deviates to Heun per SPEC S04
  (cross-checked against sympl SSPRungeKutta 2-stage).
- Substepped PS/STS/SUS sections raise `NotImplementedError` in tasmania too — not
  ported.
- Not ported either: execution policies (`'as_parallel'`),
  `enforce_horizontal_boundary`, promoter components, `DataArrayDictOperator` gt4py
  stencil dispatch (symcon: numpy-level `dict_axpy` at T0).

## Consultation ledger

`grep -n 'id = "tasmania' REFERENCES.lock` — one `[[ref]]` entry per consultation.
