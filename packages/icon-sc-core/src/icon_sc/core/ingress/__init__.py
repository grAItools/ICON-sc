"""Framework ingress adapters (architecture §2.3).

Zero-copy views of the boundary buffers for compute frameworks. One module per
framework; S07 ships the first one (:mod:`icon_sc.core.ingress.gt4py`). The
*contract-side* ingress machinery (``IngressPlan``/``EgressPlan``) lives in
:mod:`icon_sc.core.contracts` — this package owns the framework field types only.
"""

from icon_sc.core.ingress.gt4py import Backend, make_backend

__all__ = ["Backend", "make_backend"]
