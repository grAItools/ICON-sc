# gt4py

**Source:** https://github.com/GridTools/gt4py
**Pinned:** 1.1.10 (`gt4py==1.1.10` in `constraints/cpu-ci.txt`; chosen because
icon4py-common 0.2.0 pins it exactly — PyPI release consumed as sdist/wheel, not
from git).
**License:** not recorded

## Role in the project

DSL substrate for the hosted granules; the version is whatever the pinned icon4py
requires. Backend objects `gtx.gtfn_cpu`/`gtx.gtfn_gpu` are
`gt4py.next.backend.Backend` instances; embedded execution = backend `None`
(icon4py convention throughout).

## Gotchas

- Public `gtx.as_field` ALWAYS allocates ("we do not support a copy argument …") —
  the zero-copy wrap required by the ingress contract goes through the private
  singledispatch `common._field(ndarray, domain=domain)`, which aliases the buffer.
  Private-API risk recorded in the S07 STATUS follow-ups.
- requires-python `>=3.10,<3.15` (excl. 3.13.10, 3.14.1); cuda12 extra →
  `cupy-cuda12x>=12.0`.

## Consultation ledger

`grep -n 'id = "gt4py' development/references/lock.toml` — one `[[ref]]` entry per consultation.
