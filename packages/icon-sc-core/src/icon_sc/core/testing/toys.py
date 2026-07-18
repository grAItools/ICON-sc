"""Toy components for the T0 acceptance suite (SPEC S03; reused by S04/S05).

Two toy processes with closed-form solutions on a 1-column state — the sympl
paper's Fig. 1/Fig. 2 pattern (standalone diagnostic call; legible run-script
loop) is reproduced with them:

- :class:`Relaxation` (`TendencyComponent`): Newtonian relaxation
  ``dT/dt = (T_eq - T)/tau``. Under forward Euler with constant ``dt``:
  ``T_n = T_eq + (1 - dt/tau)^n (T_0 - T_eq)``.
- :class:`Damping` (`Stepper`): exact exponential damping
  ``w(t + dt) = w(t) exp(-dt/tau)``, hence ``w_n = w_0 exp(-n dt/tau)``.
- :class:`ImplicitDamping` (`ImplicitTendencyComponent`): the same damping as a
  timestep-dependent tendency ``(exp(-dt/tau) - 1)/dt * w`` (exact when
  Euler-applied over ``dt``).
- :class:`WindSpeed` (`DiagnosticComponent`): ``hypot(u, v)``.

All toys are numpy-only (`embedded` backend) and fp64; the math is elementary by
construction (no scientific constants — nothing to mine).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, cast

import numpy as np
import numpy.typing as npt

from icon_sc.core.components.base import (
    DiagnosticComponent,
    ImplicitTendencyComponent,
    Stepper,
    TendencyComponent,
)
from icon_sc.core.context import ComputeContext
from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.time import datetime
from icon_sc.core.typing import FieldBuffer

__all__ = ["Damping", "ImplicitDamping", "Relaxation", "WindSpeed", "column_state"]

_COLUMN_DIMS = ["cell", "height"]


#: Hoisted: subscripting npt.NDArray per call would allocate through typing's
#: parametrized-generic cache on the kernel hot path (S05 zero-alloc contract).
_F64Array = npt.NDArray[np.float64]


def _np(buffer: FieldBuffer) -> npt.NDArray[np.float64]:
    """The toys are numpy-only by design; narrow the boundary type."""
    return cast(_F64Array, buffer)


def _seconds(period: timedelta, *, name: str, label: str) -> float:
    if period <= timedelta(0):
        raise ValueError(f"{name}: {label} must be positive, got {period!r}.")
    return period.total_seconds()


def column_state(
    *,
    n_cell: int = 1,
    n_height: int = 10,
    time: Any | None = None,
) -> dict[str, Any]:
    """A deterministic 1-column fp64 state on (cell, height) for the toy suite."""
    shape = (n_cell, n_height)

    def field(name: str, units: str, values: npt.NDArray[np.float64]) -> Any:
        return make_dataarray(values, name=name, dims=_COLUMN_DIMS, units=units, location="cell")

    heights = np.linspace(0.0, 1.0, n_height, dtype=np.float64)
    return {
        "time": time if time is not None else datetime(2000, 1, 1),
        "air_temperature": field(
            "air_temperature", "K", np.broadcast_to(250.0 + 40.0 * heights, shape).copy()
        ),
        "upward_air_velocity": field(
            "upward_air_velocity", "m s-1", np.full(shape, 1.5, dtype=np.float64)
        ),
        "eastward_wind": field(
            "eastward_wind", "m s-1", np.broadcast_to(3.0 + heights, shape).copy()
        ),
        "northward_wind": field(
            "northward_wind", "m s-1", np.broadcast_to(4.0 - heights, shape).copy()
        ),
    }


class WindSpeed(DiagnosticComponent):
    """Diagnostic toy: wind_speed = hypot(u, v) (standalone-callable, Fig. 1)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _COLUMN_DIMS, "units": "m s-1"},
        "northward_wind": {"dims": _COLUMN_DIMS, "units": "m s-1"},
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {
        "wind_speed": {"dims": _COLUMN_DIMS, "units": "m s-1"},
    }

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        np.hypot(
            _np(inputs["eastward_wind"]),
            _np(inputs["northward_wind"]),
            out=_np(outputs["wind_speed"]),
        )


class Relaxation(TendencyComponent):
    """Tendency toy: Newtonian relaxation of temperature towards ``equilibrium``."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K s-1"},
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {
        "departure_from_equilibrium": {"dims": _COLUMN_DIMS, "units": "K"},
    }

    def __init__(
        self,
        *,
        tau: timedelta,
        equilibrium: float = 250.0,
        ctx: ComputeContext | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        self.tau_seconds = _seconds(tau, name=self.name, label="tau")
        self.equilibrium = float(equilibrium)

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        temperature = _np(inputs["air_temperature"])
        departure = _np(outputs["departure_from_equilibrium"])
        tendency = _np(outputs["air_temperature"])
        np.subtract(temperature, self.equilibrium, out=departure)
        np.multiply(departure, -1.0 / self.tau_seconds, out=tendency)


class Damping(Stepper):
    """Stepper toy: exact exponential damping of the vertical velocity."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "upward_air_velocity": {"dims": _COLUMN_DIMS, "units": "m s-1"},
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {
        "damping_rate": {"dims": _COLUMN_DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "upward_air_velocity": {"dims": _COLUMN_DIMS, "units": "m s-1"},
    }

    def __init__(
        self,
        *,
        tau: timedelta,
        ctx: ComputeContext | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        self.tau_seconds = _seconds(tau, name=self.name, label="tau")

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None  # Stepper kind: enforced by the base
        velocity = _np(inputs["upward_air_velocity"])
        # Diagnostic first: input and output buffers may legally alias under out=.
        np.multiply(velocity, -1.0 / self.tau_seconds, out=_np(outputs["damping_rate"]))
        factor = math.exp(-timestep.total_seconds() / self.tau_seconds)
        np.multiply(velocity, factor, out=_np(outputs["upward_air_velocity"]))


class ImplicitDamping(ImplicitTendencyComponent):
    """Implicit-tendency toy: damping expressed as a timestep-dependent tendency."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "upward_air_velocity": {"dims": _COLUMN_DIMS, "units": "m s-1"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        "upward_air_velocity": {"dims": _COLUMN_DIMS, "units": "m s-2"},
    }

    def __init__(
        self,
        *,
        tau: timedelta,
        ctx: ComputeContext | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        self.tau_seconds = _seconds(tau, name=self.name, label="tau")

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None  # ImplicitTendencyComponent kind: enforced
        dt = timestep.total_seconds()
        rate = (math.exp(-dt / self.tau_seconds) - 1.0) / dt
        np.multiply(
            _np(inputs["upward_air_velocity"]),
            rate,
            out=_np(outputs["upward_air_velocity"]),
        )
