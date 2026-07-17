"""Shared toy processes for the S04 acceptance suite.

Two test problems, both fp64/numpy per SPEC S04:

- the **2-process linear ODE system** of acceptance 1 — D = rotation,
  P1 = relaxation, P2 = damping on a 1-point plane-wind state; in complex form
  ``ζ = u + iv`` the full system is ``ζ' = gammaζ + c`` with
  ``gamma = iω - 1/τ₁ - 1/τ₂`` and ``c = ζ_eq/τ₁``, hence the closed form
  ``ζ(t) = (ζ₀ + c/gamma)·e^{gammat} - c/gamma``;
- the **1-D viscous Burgers equation with a relaxation physics term** of
  acceptance 2 (thesis §2.5.2 spirit) — D = advection + diffusion (periodic
  central differences, N = 512), P = Newtonian relaxation toward a static
  profile; no closed form, so orders are measured by self-convergence.

Both LFC variants are expressed through toy :class:`DynamicalCore` subclasses
(2-stage Heun cores with the physics entering through the slow-tendency port),
which is exactly eq. (2.9): ``E₀(ψⁿ, Δt; D + Pⁿ)`` with ``Pⁿ`` held constant.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any, ClassVar, cast

import numpy as np
import numpy.typing as npt

from icon_sc.core.components.base import TendencyComponent
from icon_sc.core.components.dycore import DynamicalCore
from icon_sc.core.coupling import ConcurrentCoupling, TendencyStepper
from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.time import datetime
from icon_sc.core.typing import FieldBuffer

_DIMS = ["cell", "height"]

# -- acceptance 1: the linear ODE system --------------------------------------------

#: Final time and Δt ladder (all integer microseconds, so timedelta is exact).
ODE_T = 1.024
ODE_DTS = [ODE_T / 64, ODE_T / 128, ODE_T / 256, ODE_T / 512, ODE_T / 1024]
OMEGA = 2.0 * np.pi / ODE_T  # one full rotation over [0, T]
TAU_RELAX = 0.7
TAU_DAMP = 0.15  # the stiff-ish process
EQUILIBRIUM = 0.5 - 0.3j  # relaxation target (u_eq, v_eq); the b-term that
# breaks the SUS/STS second-order clause J_D P = J_P D (thesis Table 2.1)
ZETA_0 = 1.0 + 0.5j


#: Hoisted: per-call typing subscription would allocate on the kernel hot path (S05).
_F64Array = npt.NDArray[np.float64]


def _np(buffer: FieldBuffer) -> npt.NDArray[np.float64]:
    return cast(_F64Array, buffer)


def plane_state(u0: float, v0: float) -> dict[str, Any]:
    """A 1-point (cell, height) state carrying the plane wind (u, v)."""

    def field(name: str, value: float) -> Any:
        return make_dataarray(
            np.full((1, 1), value, dtype=np.float64),
            name=name,
            dims=_DIMS,
            units="m s-1",
            location="cell",
        )

    return {
        "time": datetime(2000, 1, 1),
        "eastward_wind": field("eastward_wind", u0),
        "northward_wind": field("northward_wind", v0),
    }


_PLANE_INPUTS: dict[str, Any] = {
    "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    "northward_wind": {"dims": _DIMS, "units": "m s-1"},
}
_PLANE_TENDENCIES: dict[str, Any] = {
    "eastward_wind": {"dims": _DIMS, "units": "m s-2"},
    "northward_wind": {"dims": _DIMS, "units": "m s-2"},
}


class Rotation(TendencyComponent):
    """D: solid rotation, du/dt = -ω v, dv/dt = ω u."""

    input_properties: ClassVar[Mapping[str, Any]] = _PLANE_INPUTS
    tendency_properties: ClassVar[Mapping[str, Any]] = _PLANE_TENDENCIES

    def __init__(self, omega: float = OMEGA, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.omega = float(omega)

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        np.multiply(_np(inputs["northward_wind"]), -self.omega, out=_np(outputs["eastward_wind"]))
        np.multiply(_np(inputs["eastward_wind"]), self.omega, out=_np(outputs["northward_wind"]))


class PlaneRelaxation(TendencyComponent):
    """P1: Newtonian relaxation of (u, v) toward a fixed equilibrium point."""

    input_properties: ClassVar[Mapping[str, Any]] = _PLANE_INPUTS
    tendency_properties: ClassVar[Mapping[str, Any]] = _PLANE_TENDENCIES

    def __init__(
        self,
        tau: float = TAU_RELAX,
        equilibrium: complex = EQUILIBRIUM,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.tau = float(tau)
        self.u_eq = float(equilibrium.real)
        self.v_eq = float(equilibrium.imag)

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        _np(outputs["eastward_wind"])[...] = (self.u_eq - _np(inputs["eastward_wind"])) / self.tau
        _np(outputs["northward_wind"])[...] = (self.v_eq - _np(inputs["northward_wind"])) / self.tau


class PlaneDamping(TendencyComponent):
    """P2: linear damping of (u, v) — the stiff-ish process of acceptance 1."""

    input_properties: ClassVar[Mapping[str, Any]] = _PLANE_INPUTS
    tendency_properties: ClassVar[Mapping[str, Any]] = _PLANE_TENDENCIES

    def __init__(self, tau: float = TAU_DAMP, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tau = float(tau)

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        np.multiply(
            _np(inputs["eastward_wind"]), -1.0 / self.tau, out=_np(outputs["eastward_wind"])
        )
        np.multiply(
            _np(inputs["northward_wind"]), -1.0 / self.tau, out=_np(outputs["northward_wind"])
        )


def ode_exact(t: float) -> npt.NDArray[np.float64]:
    """Closed-form (u, v) of the full D+P1+P2 system at time ``t``."""
    gamma = 1j * OMEGA - 1.0 / TAU_RELAX - 1.0 / TAU_DAMP
    c = EQUILIBRIUM / TAU_RELAX
    zeta = (ZETA_0 + c / gamma) * np.exp(gamma * t) - c / gamma
    return np.array([zeta.real, zeta.imag], dtype=np.float64)


_PLANE_SLOTS: dict[str, str] = {
    "eastward_wind": "tendency_of_eastward_wind",
    "northward_wind": "tendency_of_northward_wind",
}


class _HeunCoreBase(DynamicalCore):
    """Toy 2-stage Heun core: E₀ second order over D + slow-port forcing.

    Stage 0: ψ* = ψⁿ + Δt·(D(ψⁿ) + S); stage 1: ψⁿ⁺¹ = ψⁿ + Δt/2·(k₁ + D(ψ*) + S).
    ``S`` arrives combined (slow port + optional per-stage fast coupling) under
    the slot names. Subclasses provide the dynamics ``_dynamics`` over the
    prognostic buffers.
    """

    n_stages: ClassVar[int] = 2
    substep_fraction: ClassVar[float | tuple[float, ...]] = 1.0

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._psi_n: dict[str, npt.NDArray[np.float64]] = {}
        self._k1: dict[str, npt.NDArray[np.float64]] = {}

    def _dynamics(
        self, fields: dict[str, npt.NDArray[np.float64]]
    ) -> dict[str, npt.NDArray[np.float64]]:
        raise NotImplementedError

    def stage_array_call(
        self,
        stage: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        seconds = dt.total_seconds()
        prognostics = tuple(self.parsed_properties["output_properties"])
        fields = {name: _np(inputs[name]) for name in prognostics}
        rate = self._dynamics(fields)
        forced = {name: rate[name] + _np(inputs[self.tendency_port[name]]) for name in prognostics}
        if stage == 0:
            self._psi_n = {name: fields[name].copy() for name in prognostics}
            self._k1 = forced
            for name in prognostics:
                _np(outputs[name])[...] = fields[name] + seconds * forced[name]
        else:
            for name in prognostics:
                _np(outputs[name])[...] = self._psi_n[name] + 0.5 * seconds * (
                    self._k1[name] + forced[name]
                )

    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        raise AssertionError("the toy Heun cores run with the substep tier disabled.")


class RotationCore(_HeunCoreBase):
    """LFC core for acceptance 1: D = rotation inside, physics via the slow port."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        **_PLANE_INPUTS,
        "tendency_of_eastward_wind": {"dims": _DIMS, "units": "m s-2"},
        "tendency_of_northward_wind": {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = _PLANE_INPUTS
    tendency_port: ClassVar[Mapping[str, str]] = _PLANE_SLOTS

    def __init__(self, omega: float = OMEGA, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.omega = float(omega)

    def _dynamics(
        self, fields: dict[str, npt.NDArray[np.float64]]
    ) -> dict[str, npt.NDArray[np.float64]]:
        return {
            "eastward_wind": -self.omega * fields["northward_wind"],
            "northward_wind": self.omega * fields["eastward_wind"],
        }


# -- acceptance 2: 1-D viscous Burgers + relaxation ---------------------------------

BURGERS_N = 512
BURGERS_DX = 1.0 / BURGERS_N
BURGERS_X = np.arange(BURGERS_N, dtype=np.float64) * BURGERS_DX
BURGERS_NU = 2.0e-4
BURGERS_TAU = 0.5
BURGERS_AMPLITUDE = 0.2
BURGERS_T = 0.128
# Ladder floor at T/512 = 250 us: every rung and both SSUS splits (0.5*dt, 0.3*dt)
# stay integer microseconds, i.e. exactly timedelta-representable. T/1024 = 125 us
# would make lam*dt = 62.5 us round to 62 us and corrupt the Strang symmetry.
BURGERS_DTS = [BURGERS_T / 64, BURGERS_T / 128, BURGERS_T / 256, BURGERS_T / 512]
BURGERS_U0 = BURGERS_AMPLITUDE * np.sin(2.0 * np.pi * BURGERS_X)
BURGERS_UEQ = BURGERS_AMPLITUDE * np.cos(2.0 * np.pi * BURGERS_X)

_BURGERS_INPUTS: dict[str, Any] = {"eastward_wind": {"dims": _DIMS, "units": "m s-1"}}
_BURGERS_TENDENCIES: dict[str, Any] = {"eastward_wind": {"dims": _DIMS, "units": "m s-2"}}


def burgers_state() -> dict[str, Any]:
    """The (1, N) Burgers state at t = 0."""
    return {
        "time": datetime(2000, 1, 1),
        "eastward_wind": make_dataarray(
            BURGERS_U0.reshape(1, -1).copy(),
            name="eastward_wind",
            dims=_DIMS,
            units="m s-1",
            location="cell",
        ),
    }


def _burgers_rhs(u: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """D(u) = -u uₓ + nu*uₓₓ, periodic central differences on axis -1."""
    forward = np.roll(u, -1, axis=-1)
    backward = np.roll(u, 1, axis=-1)
    advection = -u * (forward - backward) / (2.0 * BURGERS_DX)
    diffusion = BURGERS_NU * (forward - 2.0 * u + backward) / (BURGERS_DX * BURGERS_DX)
    return cast(npt.NDArray[np.float64], advection + diffusion)


class BurgersDynamics(TendencyComponent):
    """D: advection + diffusion of the 1-D Burgers velocity (periodic, N=512)."""

    input_properties: ClassVar[Mapping[str, Any]] = _BURGERS_INPUTS
    tendency_properties: ClassVar[Mapping[str, Any]] = _BURGERS_TENDENCIES

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        _np(outputs["eastward_wind"])[...] = _burgers_rhs(_np(inputs["eastward_wind"]))


class BurgersRelaxation(TendencyComponent):
    """P: relaxation toward the static profile u_eq(x) (the physics term)."""

    input_properties: ClassVar[Mapping[str, Any]] = _BURGERS_INPUTS
    tendency_properties: ClassVar[Mapping[str, Any]] = _BURGERS_TENDENCIES

    def __init__(self, tau: float = BURGERS_TAU, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tau = float(tau)

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        u = _np(inputs["eastward_wind"])
        _np(outputs["eastward_wind"])[...] = (BURGERS_UEQ.reshape(1, -1) - u) / self.tau


class BurgersCore(_HeunCoreBase):
    """LFC core for acceptance 2: Burgers dynamics inside, relaxation via the port."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        **_BURGERS_INPUTS,
        "tendency_of_eastward_wind": {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = _BURGERS_INPUTS
    tendency_port: ClassVar[Mapping[str, str]] = {"eastward_wind": "tendency_of_eastward_wind"}

    def _dynamics(
        self, fields: dict[str, npt.NDArray[np.float64]]
    ) -> dict[str, npt.NDArray[np.float64]]:
        return {"eastward_wind": _burgers_rhs(fields["eastward_wind"])}


# -- scheme drivers ------------------------------------------------------------------

StepFn = Callable[[dict[str, Any], timedelta], dict[str, Any]]


def federation_step(federation: Any) -> StepFn:
    """A loop-body step from any Stepper-shaped component/federation."""

    def step(state: dict[str, Any], dt: timedelta) -> dict[str, Any]:
        diagnostics, new_state = federation(state, dt)
        state.update(diagnostics)
        state.update(new_state)
        return state

    return step


def lfc_step(physics: ConcurrentCoupling, core: DynamicalCore, slots: Mapping[str, str]) -> StepFn:
    """LFC (thesis eq. 2.9): evaluate physics at ψⁿ, publish, run the core.

    The physics tendencies are published into the core's slow-port slots once per
    step (the loop-body bus-publication pattern of architecture §5.1) and held
    constant across the core's stages.
    """

    def step(state: dict[str, Any], dt: timedelta) -> dict[str, Any]:
        tendencies, diagnostics = physics(state, dt)
        state.update(diagnostics)
        for field, slot in slots.items():
            source = tendencies[field]
            state[slot] = make_dataarray(
                source.data,
                name=slot,
                dims=source.dims,
                units="m s-2",
                location="cell",
            )
        core_diags, new_state = core(state, dt)
        state.update(core_diags)
        state.update(new_state)
        return state

    return step


def integrate(
    step: StepFn, state: dict[str, Any], dt_seconds: float, t_final: float
) -> dict[str, Any]:
    """Run ``step`` from t=0 to ``t_final`` in exact Δt slabs."""
    n_steps = round(t_final / dt_seconds)
    if abs(n_steps * dt_seconds - t_final) > 1e-12:
        raise ValueError(f"t_final={t_final} is not a multiple of dt={dt_seconds}.")
    dt = timedelta(seconds=dt_seconds)
    if dt.total_seconds() != dt_seconds:
        raise ValueError(f"dt={dt_seconds} s is not exactly representable as a timedelta.")
    current = dict(state)
    for _ in range(n_steps):
        current = step(current, dt)
    return current


def make_scheme_steps(
    dynamics: TendencyComponent,
    physics: list[TendencyComponent],
    lfc_core: DynamicalCore,
    slots: Mapping[str, str],
    stepper: str = "rk2",
) -> dict[str, StepFn]:
    """The seven coupling schemes of acceptance 1/2, as loop-body step functions."""
    from icon_sc.core.coupling import (
        SSUS,
        ParallelSplitting,
        SequentialTendencySplitting,
        SequentialUpdateSplitting,
    )

    sections = [(component, stepper) for component in physics]
    return {
        "fc": federation_step(
            TendencyStepper.factory(stepper, ConcurrentCoupling([dynamics, *physics]))
        ),
        "lfc": lfc_step(ConcurrentCoupling(list(physics)), lfc_core, slots),
        "ps": federation_step(ParallelSplitting([(dynamics, stepper), *sections])),
        "sts": federation_step(SequentialTendencySplitting([(dynamics, stepper), *sections])),
        "sus": federation_step(SequentialUpdateSplitting([(dynamics, stepper), *sections])),
        "ssus_half": federation_step(SSUS(sections, (dynamics, stepper), 0.5)),
        "ssus_03": federation_step(SSUS(sections, (dynamics, stepper), 0.3)),
    }
