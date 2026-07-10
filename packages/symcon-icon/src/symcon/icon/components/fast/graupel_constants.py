"""Graupel scheme constants consumed on the symcon side (S08; architecture §8.6).

One scheme-constants module per scheme (single source of numerical truth for the
imperative kernel *and* the S10 functional core). The imperative kernel is
icon4py's granule, whose full constant set lives in its own
``microphysics_constants.MicrophysicsConstants``; this module transcribes only
the values the symcon side itself consumes (tests, contracts, and — from S10 —
the JAX functional core), each with provenance:

- ``GRAUPEL_QMIN`` — icon4py v0.2.0 ``MicrophysicsConstants.QMIN`` ("threshold
  for lowest detectable mixing ratios"; ICON ``zqmin`` in ``gscp_data.f90``).
  Equality with icon4py is asserted in ``tests/test_graupel_component.py``.
- ``CLOUD_NUM`` — ICON ``gscp_data.f90:92`` ``cloud_num = 200.00e+06_wp``
  (cloud droplet number concentration [1/m3]); the value
  ``mo_nwp_gscp_interface.f90`` feeds the graupel granule as ``qnc`` when
  ``icpl_aero_gscp = 0`` (REFERENCES.lock ``icon-fortran-graupel``). icon4py
  has no counterpart constant — its tests read ``qnc`` from serialized data —
  so the symcon column builders use this Fortran default.
"""

from __future__ import annotations

from typing import Final

__all__ = ["CLOUD_NUM", "GRAUPEL_QMIN"]

#: Threshold for lowest detectable mixing ratios [kg/kg] (icon4py QMIN; ICON zqmin).
GRAUPEL_QMIN: Final[float] = 1.0e-15

#: Default cloud droplet number concentration [1/m3] (ICON gscp_data.f90 cloud_num).
CLOUD_NUM: Final[float] = 200.00e6
