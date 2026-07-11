"""Idealized forcing components for column presets (S09).

The S09 SCM composition exercises the slow-tendency bus end-to-end before a real
dynamical core exists to consume it (architecture §4.2 "the bus, reframed"; SPEC
S09 in-scope): a :class:`PrescribedCooling` slow process publishes a
piecewise-constant temperature tendency into the ``icon:ddt_temperature_slow``
slot (seeded for exactly this purpose in :mod:`symcon.icon.names`, S06), and a
trivial :class:`ApplySlowTendencies` stepper stands in for the consumer the
tutorial describes (§3.7.2, REFERENCES.lock ``icon-tutorial-2025``: slow-physics
tendencies are "kept constant between two successive calls" and act as forcing
terms integrated inside the dynamical core / tracer transport — here, at column
scale, a forward-Euler application is that integration).

``PrescribedCooling`` is analytic (PLAN S09 item 1): Newtonian relaxation of the
temperature toward an offset ICON reference-atmosphere profile,

    dT/dt = (T_eq(z) - T) / tau,   T_eq(z) = T_ref(z) - offset,

with ``T_ref`` the decaying-isothermal reference temperature mined in S06
(``mo_vertical_grid.f90``; :func:`symcon.icon.grid.vertical.reference_temperature`).
The *shape* is the standard idealized radiative-cooling stand-in (relaxation-type
forcing); the default timescale/offset are test-fixture magnitudes chosen at
typical tropospheric cooling rates (~1-5 K/day), not mined scientific constants
(S06 ``moist_test_column`` precedent).

Neither component is an ICON scheme; real slow physics (radiation, convection,
...) arrives in P3, the real consumer (the dycore's slow port) in S12.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, Final, cast

from symcon.core.components.base import Stepper, TendencyComponent
from symcon.core.context import ComputeContext
from symcon.core.typing import FieldBuffer
from symcon.icon import names as _names  # noqa: F401  (registry seed side effect)
from symcon.icon.grid.vertical import reference_temperature

__all__ = ["ApplySlowTendencies", "PrescribedCooling", "PrescribedCoolingConfig"]

_COLUMN_DIMS: Final[tuple[str, str]] = ("cell", "height")

#: The S06-seeded bus slot this pair publishes/consumes (symcon-only slot).
SLOW_TEMPERATURE_SLOT: Final[str] = "icon:ddt_temperature_slow"


@dataclasses.dataclass(frozen=True)
class PrescribedCoolingConfig:
    """Newtonian-relaxation parameters (test-fixture magnitudes, see module note)."""

    #: Relaxation (e-folding) timescale of the Newtonian cooling.
    relaxation_timescale: timedelta = timedelta(hours=24)
    #: Equilibrium profile offset below the ICON reference atmosphere [K].
    equilibrium_offset: float = 5.0

    def __post_init__(self) -> None:
        if self.relaxation_timescale <= timedelta(0):
            raise ValueError(
                f"relaxation_timescale must be positive, got {self.relaxation_timescale!r}."
            )


class PrescribedCooling(TendencyComponent):
    """Analytic radiative-cooling stand-in publishing to the tendency bus (SPEC S09).

    ``dT/dt = (T_eq(z) - T)/tau`` with ``T_eq(z) = T_ref(z) - offset`` (module
    docstring). The tendency is published under the bus-slot name
    ``icon:ddt_temperature_slow`` (canonical units ``K s-1``), *not* as a plain
    ``air_temperature`` tendency: slow-process output rides the §4.2 bus and is
    consumed by exactly one consumer, checked at composition time by
    :class:`~symcon.core.coupling.bus.SlowTendencyBus`.
    """

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K"},
        "altitude": {"dims": _COLUMN_DIMS, "units": "m"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        SLOW_TEMPERATURE_SLOT: {"dims": _COLUMN_DIMS, "units": "K s-1", "differentiable": "native"},
    }

    def __init__(
        self,
        cfg: PrescribedCoolingConfig | None = None,
        ctx: ComputeContext | None = None,
        *,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        self.config = cfg if cfg is not None else PrescribedCoolingConfig()

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep  # instantaneous tendency (TendencyComponent kind)
        temperature = cast(Any, inputs["air_temperature"])
        altitude = cast(Any, inputs["altitude"])
        tau = self.config.relaxation_timescale.total_seconds()
        t_eq = reference_temperature(altitude) - self.config.equilibrium_offset
        cast(Any, outputs[SLOW_TEMPERATURE_SLOT])[...] = (t_eq - temperature) / tau

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        """Pure evaluation of the relaxation tendency (§8.6 ``native``; S10).

        ``reference_temperature`` is array-namespace generic (S06), so the same
        formula traces under jax unchanged — one shared source for both tiers.
        """
        del params, dt
        tau = self.config.relaxation_timescale.total_seconds()
        t_eq = reference_temperature(inputs["altitude"]) - self.config.equilibrium_offset
        return {SLOW_TEMPERATURE_SLOT: (t_eq - inputs["air_temperature"]) / tau}


class ApplySlowTendencies(Stepper):
    """Trivial bus consumer: forward-Euler application of the slow T tendency.

    Stands in for the dynamical core's slow-tendency input port (architecture
    §4.2/§4.3) until S12: ``T_new = T + Δt · ddt_temperature_slow``, with the
    slot value held piecewise-constant by the publisher's ``CallingFrequency``
    wrapper. Declared as an input (not recomputed), so the S04 bus checker can
    verify the publish/consume wiring of the preset.
    """

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K"},
        SLOW_TEMPERATURE_SLOT: {"dims": _COLUMN_DIMS, "units": "K s-1"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K", "differentiable": "native"},
    }

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None  # Stepper: enforced by the base class
        temperature = cast(Any, inputs["air_temperature"])
        tendency = cast(Any, inputs[SLOW_TEMPERATURE_SLOT])
        cast(Any, outputs["air_temperature"])[...] = (
            temperature + tendency * timestep.total_seconds()
        )

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        """Pure forward-Euler application of the bus slot (§8.6 ``native``; S10)."""
        del params
        return {"air_temperature": inputs["air_temperature"] + inputs[SLOW_TEMPERATURE_SLOT] * dt}
