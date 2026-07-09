"""ConcurrentCoupling semantics (SPEC S04): summation, serial chaining, nesting."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar

import numpy as np
import pytest

from symcon.core.components.base import TendencyComponent
from symcon.core.components.wrappers import CallingFrequency
from symcon.core.contracts.properties import PropertyDictError
from symcon.core.coupling import ConcurrentCoupling
from symcon.core.testing import assert_allclose
from symcon.core.testing.toys import Damping, ImplicitDamping, Relaxation, WindSpeed, column_state

DT = timedelta(seconds=30)
_DIMS = ["cell", "height"]


class WindChill(TendencyComponent):
    """Toy consumer of the ``wind_speed`` diagnostic: dT/dt = -k * wind_speed."""

    input_properties: ClassVar[dict[str, Any]] = {
        "wind_speed": {"dims": _DIMS, "units": "m s-1"},
    }
    tendency_properties: ClassVar[dict[str, Any]] = {
        "air_temperature": {"dims": _DIMS, "units": "K s-1"},
    }

    def __init__(self, k: float = 0.01, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.k = k

    def array_call(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        np.multiply(inputs["wind_speed"], -self.k, out=outputs["air_temperature"])


def test_tendency_contributions_are_summed() -> None:
    a = Relaxation(tau=timedelta(seconds=100), equilibrium=250.0)
    b = Relaxation(tau=timedelta(seconds=50), equilibrium=200.0)
    state = column_state()
    tendencies, _ = ConcurrentCoupling([a, b])(state, DT)
    ta, _ = a(state)
    tb, _ = b(state)
    assert_allclose(
        tendencies["air_temperature"].data,
        ta["air_temperature"].data + tb["air_temperature"].data,
        rtol=1e-14,
        names="air_temperature tendency",
    )


def test_serial_policy_chains_diagnostics_into_later_members() -> None:
    """A later member consumes an earlier member's diagnostic (tasmania serial)."""
    coupling = ConcurrentCoupling([WindSpeed(), WindChill(k=0.01)])
    state = column_state()
    assert "wind_speed" not in state  # produced inside the coupling
    # ... and therefore not required from the caller:
    assert "wind_speed" not in coupling.parsed_properties["input_properties"]
    tendencies, diagnostics = coupling(state, DT)
    expected = -0.01 * np.hypot(state["eastward_wind"].data, state["northward_wind"].data)
    assert_allclose(
        tendencies["air_temperature"].data, expected, rtol=1e-14, names="chained tendency"
    )
    assert "wind_speed" in diagnostics


def test_couplings_nest() -> None:
    inner = ConcurrentCoupling([Relaxation(tau=timedelta(seconds=100))])
    outer = ConcurrentCoupling([inner, Relaxation(tau=timedelta(seconds=50))])
    state = column_state()
    tendencies, _ = outer(state, DT)
    assert set(tendencies) == {"air_temperature"}


def test_wrapped_members_are_accepted() -> None:
    wrapped = CallingFrequency(Relaxation(tau=timedelta(seconds=100)), timedelta(seconds=300))
    coupling = ConcurrentCoupling([wrapped])
    tendencies, _ = coupling(column_state(), DT)
    assert set(tendencies) == {"air_temperature"}


def test_implicit_member_requires_timestep() -> None:
    coupling = ConcurrentCoupling([ImplicitDamping(tau=timedelta(seconds=100))])
    assert coupling.timestep_required
    with pytest.raises(TypeError, match="requires a timestep"):
        coupling(column_state())


def test_stepper_members_are_rejected() -> None:
    with pytest.raises(TypeError, match="Steppers belong in federations"):
        ConcurrentCoupling([Damping(tau=timedelta(seconds=100))])


def test_incompatible_tendency_declarations_reject() -> None:
    class BadUnits(TendencyComponent):
        input_properties: ClassVar[dict[str, Any]] = {
            "air_temperature": {"dims": _DIMS, "units": "K"},
        }
        tendency_properties: ClassVar[dict[str, Any]] = {
            "air_temperature": {"dims": _DIMS, "units": "K min-1"},
        }

        def array_call(
            self,
            inputs: dict[str, Any],
            outputs: dict[str, Any],
            timestep: timedelta | None,
        ) -> None:
            del inputs, timestep
            outputs["air_temperature"][...] = 0.0

    with pytest.raises(PropertyDictError, match="tendency 'air_temperature'"):
        ConcurrentCoupling([Relaxation(tau=timedelta(seconds=100)), BadUnits()])


def test_out_buffers_are_honored() -> None:
    coupling = ConcurrentCoupling([Relaxation(tau=timedelta(seconds=100))])
    state = column_state()
    reference, _ = coupling(state, DT)
    out_tend = state["air_temperature"].copy(deep=True)
    tendencies, _ = coupling(state, DT, out={"air_temperature": out_tend})
    assert tendencies["air_temperature"] is out_tend
    assert_allclose(
        out_tend.data, reference["air_temperature"].data, rtol=1e-14, names="out= tendency"
    )
    with pytest.raises(ValueError, match="not outputs of this coupling"):
        coupling(state, DT, out={"nope": out_tend})


def test_restart_round_trip_reaches_members() -> None:
    """CallingFrequency carry survives through the coupling's restart delegation."""
    wrapped = CallingFrequency(Relaxation(tau=timedelta(seconds=100)), timedelta(seconds=60))
    coupling = ConcurrentCoupling([wrapped])
    state = column_state()
    coupling(state, DT)  # prime the cache/phase
    saved = coupling.restart_state()
    assert any(key.startswith("component0/") for key in saved)

    fresh_wrapped = CallingFrequency(Relaxation(tau=timedelta(seconds=100)), timedelta(seconds=60))
    fresh = ConcurrentCoupling([fresh_wrapped])
    fresh.load_restart_state(saved)
    # The restored wrapper replays the cache instead of firing again.
    tendencies, _ = fresh(state, DT)
    reference, _ = coupling(state, DT)
    assert_allclose(
        tendencies["air_temperature"].data,
        reference["air_temperature"].data,
        rtol=1e-14,
        names="restored cache",
    )
    with pytest.raises(ValueError, match="unknown restart key"):
        fresh.load_restart_state({"bogus": state["air_temperature"]})


def test_empty_coupling_rejects() -> None:
    with pytest.raises(ValueError, match="at least one component"):
        ConcurrentCoupling([])
