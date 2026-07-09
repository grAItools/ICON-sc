"""ICON thermodynamic relations, exactly as ICON defines them (S06).

Formulas are transcribed from the pinned references (REFERENCES.lock, S06):

- ``diag_temp`` in ICON ``src/atm_dyn_iconam/mo_nh_diagnose_pres_temp.f90`` (equals
  icon4py v0.2.0 ``diagnose_temperature.py``): ``tempv = theta_v * exner``,
  ``temp = tempv / (1 + vtmpc1*qv - qsum)``;
- pressure (cpd) Exner path: ``exner = (p/p0ref)**rd_o_cpd``
  (``mo_nh_vert_extrap_utils.f90``), inverse ``p = p0ref * exner**(cpd/rd)``;
- density (cvd) Exner path: ``exner = EXP(rd_o_cvd*LOG(rd_o_p0ref*rho*theta_v))``
  (``mo_nh_nest_utilities.f90``) — ICON's isochoric coupling uses cvd downstream, so
  both paths exist here from the start and are named unambiguously (PLAN pitfall).

All functions are array-namespace generic (PEP 3118/array-API duck typing via
``array_api_compat``): numpy in → numpy out, cupy in → cupy out, and — unchanged — JAX
in S10 (the start of the functional cores). Nothing here allocates other than the
result; no field/DataArray types appear at this layer.
"""

from __future__ import annotations

from typing import Any

import array_api_compat

from symcon.icon._constants import (
    CPD_O_RD,
    P0REF,
    RD_O_CPD,
    RD_O_CVD,
    RD_O_P0REF,
    VTMPC1,
)

__all__ = [
    "exner_from_pressure",
    "exner_from_rho_thetav",
    "pressure_from_exner",
    "temperature_from_thetav_exner",
    "virtual_potential_temperature",
    "virtual_temperature",
]

#: Array-namespace-generic value (any array-API array: numpy, cupy, later JAX).
Array = Any


def exner_from_pressure(pressure: Array) -> Array:
    """Exner function from pressure — the *pressure (cpd) path*.

    ``exner = (p / p0ref)**(rd/cpd)`` (ICON ``mo_nh_vert_extrap_utils.f90``).
    """
    return (pressure / P0REF) ** RD_O_CPD


def pressure_from_exner(exner: Array) -> Array:
    """Pressure from the Exner function — inverse of the pressure (cpd) path.

    ``p = p0ref * exner**(cpd/rd)`` (plain form: ``mo_nh_vert_extrap_utils.f90:754``;
    the fused ``EXP(cpd_o_rd*LOG(exner)+...)`` surface-pressure variant lives in
    ``mo_nh_diagnose_pres_temp.f90``).
    """
    return P0REF * exner**CPD_O_RD


def exner_from_rho_thetav(rho: Array, theta_v: Array) -> Array:
    """Exner function from density and θv — the *density (cvd) path*.

    ``exner = EXP(rd/cvd * LOG(rd/p0ref * rho * theta_v))`` operation-for-operation as
    ICON writes it (``mo_nh_nest_utilities.f90:1657``); the dycore/physics isochoric
    coupling is cvd-based, distinct from the cpd exponent of the pressure path.
    """
    xp = array_api_compat.array_namespace(rho, theta_v)
    return xp.exp(RD_O_CVD * xp.log(RD_O_P0REF * rho * theta_v))


def virtual_temperature(temperature: Array, qv: Array, q_condensate: Any = 0.0) -> Array:
    """Virtual temperature with moisture and condensate loading.

    ``tempv = temp * (1 + vtmpc1*qv - qsum)`` where ``qsum`` is the total mass
    fraction of prognostic condensate (``qc+qi+qr+qs+qg`` in ICON ``diag_temp``,
    inverted; here a single pre-summed ``q_condensate`` argument).
    """
    return temperature * (1.0 + VTMPC1 * qv - q_condensate)


def virtual_potential_temperature(
    temperature: Array, exner: Array, qv: Array, q_condensate: Any = 0.0
) -> Array:
    """θv from temperature, Exner function and moisture (inverse of ``diag_temp``).

    ``theta_v = temp * (1 + vtmpc1*qv - qsum) / exner``.
    """
    return virtual_temperature(temperature, qv, q_condensate) / exner


def temperature_from_thetav_exner(
    theta_v: Array, exner: Array, qv: Array, q_condensate: Any = 0.0
) -> Array:
    """Temperature from θv, Exner function and moisture — ICON ``diag_temp`` verbatim.

    ``tempv = theta_v * exner``; ``temp = tempv / (1 + vtmpc1*qv - qsum)``.
    """
    return theta_v * exner / (1.0 + VTMPC1 * qv - q_condensate)
