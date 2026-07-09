"""Registry-based tendency-stepper family (architecture §4.2, SPEC S04).

Two :class:`~symcon.core.registry.Factory` roots, each with the same four
registered schemes (``forward_euler``, ``rk2`` (Heun), ``rk3ws`` (Wicker-Skamarock),
``ssprk3`` (Shu-Osher)):

- :class:`TendencyStepper` — steps a state from the tendencies of a wrapped
  :class:`~symcon.core.coupling.concurrent.ConcurrentCoupling` (or bare tendency
  component): ``ψⁿ⁺¹ = E(ψⁿ, Δt; P)``. Resolved by name through
  ``TendencyStepper.factory(name, coupling)`` so user-defined steppers are
  first-class citizens of every federation.
- :class:`SequentialTendencyStepper` — the two-input-state signature
  ``E(ψⁿ, Δt; P + (ψ_prov - ψⁿ)/Δt)`` (thesis eq. 2.11b) that makes
  sequential-tendency splitting expressible: the accumulated provisional tendency
  of upstream processes enters every tendency evaluation as a constant forcing.

Scheme provenance (REFERENCES.lock): ``forward_euler``/``rk3ws`` coefficients from
tasmania's tendency steppers (rk3ws provisional fractions 1/3, 1/2, 1 per
Doms & Baldauf's COSMO documentation); ``rk2`` is Heun per SPEC S04 — sympl's
2-stage SSP Runge-Kutta — which deviates from tasmania's midpoint ``rk2``
(recorded in STATUS.md); ``ssprk3`` from sympl's 3-stage SSP Runge-Kutta
(Shu & Osher 1988). The generic-forcing formulation of the sequential steppers is
algebraically identical to tasmania's fused first-stage ops (``sts_rk2_0``:
``½(ψⁿ + ψ_prov + Δt·P)``; ``sts_rk3ws_0``: ``(2ψⁿ + ψ_prov + Δt·P)/3``).

Diagnostics returned by a stepper are those of the **first** tendency evaluation,
i.e. diagnosed at ``ψⁿ`` (tasmania's convention); later stage evaluations feed the
scheme only.
"""

from __future__ import annotations

import abc
import re
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import timedelta
from typing import Any, ClassVar, cast

import xarray as xr

from symcon.core.components.base import DataArrayDict
from symcon.core.contracts.properties import PropertySpec
from symcon.core.coupling.concurrent import (
    is_tendency_kind,
    name_of,
    output_dict_names_of,
    parsed_properties_of,
)
from symcon.core.registry import Factory

__all__ = ["SequentialTendencyStepper", "TendencyStepper"]

#: One tendency evaluation at a stage state: buffers in, (buffers, diagnostics) out.
_Evaluate = Callable[[dict[str, Any]], tuple[dict[str, Any], DataArrayDict]]

_SECONDS_TOKEN = re.compile(r"^s(?P<exponent>-?\d+)?$")


def _integrate_units(units: str) -> str:
    """Units of ``∫ x dt`` for tendency units ``x`` (``"K s-1" -> "K"``).

    Canonical unit strings are space-separated power tokens (S02); integrating
    over seconds raises the ``s`` exponent by one (dropping the token at zero) or
    appends a bare ``s``.
    """
    tokens = units.split()
    for index, token in enumerate(tokens):
        match = _SECONDS_TOKEN.match(token)
        if match is None:
            continue
        exponent = int(match.group("exponent") or 1) + 1
        if exponent == 0:
            del tokens[index]
        elif exponent == 1:
            tokens[index] = "s"
        else:
            tokens[index] = f"s{exponent}"
        return " ".join(tokens) if tokens else "1"
    tokens.append("s")
    return " ".join(t for t in tokens if t != "1") or "s"


def _dt_seconds(timestep: timedelta, *, name: str) -> float:
    if timestep <= timedelta(0):
        raise ValueError(f"{name}: timestep must be positive, got {timestep!r}.")
    return timestep.total_seconds()


class _StepperBase(abc.ABC):
    """Machinery shared by the two registry roots (not itself registered)."""

    #: Stepper-kind fingerprint: steppers compose like §4.1 Steppers.
    output_dict_names: ClassVar[tuple[str, ...]] = (
        "diagnostic_properties",
        "output_properties",
    )
    timestep_required: ClassVar[bool] = True

    def __init__(self, coupling: Any) -> None:
        if not is_tendency_kind(coupling):
            raise TypeError(
                f"{type(self).__name__}: {name_of(coupling)!r} is not a tendency "
                f"provider (output_dict_names={output_dict_names_of(coupling)!r}); "
                f"wrap TendencyComponents or a ConcurrentCoupling."
            )
        self._coupling = coupling
        parsed = parsed_properties_of(coupling)
        tendency_specs = dict(parsed.get("tendency_properties", {}))
        if not tendency_specs:
            raise ValueError(
                f"{self.label}: {name_of(coupling)!r} declares no tendencies; "
                f"there is nothing to step."
            )
        input_specs = dict(parsed.get("input_properties", {}))
        output_specs: dict[str, PropertySpec] = {}
        for field, spec in tendency_specs.items():
            source = input_specs.get(field)
            if source is not None:
                output_specs[field] = source
            else:
                output_specs[field] = replace(spec, units=_integrate_units(spec.units))
        self._parsed: Mapping[str, Mapping[str, PropertySpec]] = {
            "input_properties": input_specs,
            "diagnostic_properties": dict(parsed.get("diagnostic_properties", {})),
            "output_properties": output_specs,
        }
        self._prognostics = tuple(tendency_specs)

    @property
    def label(self) -> str:
        """Display name: the registered scheme key over the wrapped coupling.

        The registered scheme key itself lives in the ``name`` class attribute
        (S02 ``Factory`` registration contract), so it cannot double as a
        per-instance display name.
        """
        scheme = getattr(type(self), "name", type(self).__name__)
        return f"{scheme}({name_of(self._coupling)})"

    @property
    def coupling(self) -> Any:
        """The wrapped tendency provider."""
        return self._coupling

    @property
    def prognostics(self) -> tuple[str, ...]:
        """The fields this stepper advances (the coupling's tendency names)."""
        return self._prognostics

    @property
    def parsed_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        """Parsed property dicts (outputs derived from the coupling's tendencies)."""
        return self._parsed

    def __str__(self) -> str:
        return f"instance of {type(self).__name__} over {name_of(self._coupling)}"

    # -- scheme hook -----------------------------------------------------------------

    @abc.abstractmethod
    def _integrate(
        self, phi: dict[str, Any], evaluate: _Evaluate, dt: float
    ) -> tuple[dict[str, Any], DataArrayDict]:
        """Advance ``phi`` by ``dt`` seconds; return (new buffers, ψⁿ diagnostics)."""

    # -- shared call machinery ---------------------------------------------------------

    def _extract(self, state: Mapping[str, Any], *, role: str) -> dict[str, Any]:
        buffers: dict[str, Any] = {}
        for field in self._prognostics:
            try:
                buffers[field] = state[field].data
            except KeyError:
                raise KeyError(
                    f"{self.label}: prognostic {field!r} missing from the {role} state."
                ) from None
        return buffers

    def _make_evaluate(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        forcing: dict[str, Any] | None = None,
    ) -> _Evaluate:
        coupling = cast("Callable[..., Any]", self._coupling)
        prognostics = self._prognostics

        def evaluate(phi: dict[str, Any]) -> tuple[dict[str, Any], DataArrayDict]:
            stage_state: dict[str, Any] = dict(state)
            for field, buffer in phi.items():
                stage_state[field] = state[field].copy(data=buffer)
            tendencies, diagnostics = coupling(stage_state, timestep)
            if forcing is None:
                arrays = {field: tendencies[field].data for field in prognostics}
            else:
                arrays = {field: tendencies[field].data + forcing[field] for field in prognostics}
            return arrays, diagnostics

        return evaluate

    def _validate_out(self, out: Mapping[str, xr.DataArray] | None) -> None:
        if out is None:
            return
        known = set(self._prognostics) | set(self._parsed["diagnostic_properties"])
        unknown = set(out) - known
        if unknown:
            raise ValueError(
                f"{self.label}: out= names {sorted(unknown)} are not outputs of this "
                f"stepper (outputs: {sorted(known)})."
            )

    def _package(
        self,
        state: Mapping[str, Any],
        phi_new: dict[str, Any],
        diagnostics: DataArrayDict,
        out: Mapping[str, xr.DataArray] | None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        diag_result: DataArrayDict = {}
        for field, array in diagnostics.items():
            if out is not None and field in out:
                out[field].data[...] = array.data
                diag_result[field] = out[field]
            else:
                diag_result[field] = array
        new_state: DataArrayDict = {}
        for field in self._prognostics:
            if out is not None and field in out:
                out[field].data[...] = phi_new[field]
                new_state[field] = out[field]
            else:
                new_state[field] = state[field].copy(data=phi_new[field])
        return diag_result, new_state

    # -- restart / functional carry (delegated to the coupling) -----------------------

    def restart_state(self) -> dict[str, xr.DataArray]:
        """The wrapped coupling's private state (steppers themselves are stateless)."""
        return dict(self._coupling.restart_state())

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        """Restore the wrapped coupling's private state."""
        self._coupling.load_restart_state(restart)

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """The wrapped coupling's carry schema."""
        return cast("Mapping[str, PropertySpec]", self._coupling.functional_state())


class TendencyStepper(_StepperBase, Factory):
    """``ψⁿ⁺¹ = E(ψⁿ, Δt; P)`` — registry root (frozen interface, SPEC S04).

    ``TendencyStepper.factory(name, coupling)`` resolves ``name`` through the S02
    registry; ``coupling`` is a :class:`ConcurrentCoupling` or a bare tendency
    component. Instances are Stepper-shaped components:
    ``(state, timestep, *, out=None) -> (diagnostics, new_state)``.
    """

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Step the coupling's prognostics from ``state`` over ``timestep``."""
        dt = _dt_seconds(timestep, name=self.label)
        self._validate_out(out)
        phi = self._extract(state, role="input")
        evaluate = self._make_evaluate(state, timestep)
        phi_new, diagnostics = self._integrate(phi, evaluate, dt)
        return self._package(state, phi_new, diagnostics, out)


class SequentialTendencyStepper(_StepperBase, Factory):
    """``E(ψⁿ, Δt; P + (ψ_prov - ψⁿ)/Δt)`` — registry root (frozen interface, SPEC S04).

    The two-state signature of thesis eq. (2.11b): the integration starts from the
    **step-initial** state ``ψⁿ`` and the provisional state of the upstream sections
    enters as the constant forcing ``(ψ_prov - ψⁿ)/Δt`` added to every tendency
    evaluation.
    """

    def __call__(
        self,
        state: Mapping[str, Any],
        prv_state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Step from ``state`` (ψⁿ) with the provisional forcing from ``prv_state``."""
        dt = _dt_seconds(timestep, name=self.label)
        self._validate_out(out)
        phi = self._extract(state, role="input")
        provisional = self._extract(prv_state, role="provisional")
        forcing = {field: (provisional[field] - phi[field]) / dt for field in self._prognostics}
        evaluate = self._make_evaluate(state, timestep, forcing)
        phi_new, diagnostics = self._integrate(phi, evaluate, dt)
        return self._package(state, phi_new, diagnostics, out)


# -- registered schemes -----------------------------------------------------------------


class _ForwardEulerScheme(_StepperBase):
    """``ψⁿ⁺¹ = ψⁿ + Δt·F(ψⁿ)`` (tasmania forward_euler)."""

    def _integrate(
        self, phi: dict[str, Any], evaluate: _Evaluate, dt: float
    ) -> tuple[dict[str, Any], DataArrayDict]:
        k1, diagnostics = evaluate(phi)
        return {field: phi[field] + dt * k1[field] for field in phi}, diagnostics


class _HeunScheme(_StepperBase):
    """Heun's method (SSP RK2, sympl's 2-stage SSPRungeKutta; SPEC S04 ``rk2``)."""

    def _integrate(
        self, phi: dict[str, Any], evaluate: _Evaluate, dt: float
    ) -> tuple[dict[str, Any], DataArrayDict]:
        k1, diagnostics = evaluate(phi)
        phi_1 = {field: phi[field] + dt * k1[field] for field in phi}
        k2, _ = evaluate(phi_1)
        return {
            field: phi[field] + 0.5 * dt * (k1[field] + k2[field]) for field in phi
        }, diagnostics


class _RK3WSScheme(_StepperBase):
    """Wicker-Skamarock RK3: provisional fractions 1/3, 1/2, then the full step."""

    def _integrate(
        self, phi: dict[str, Any], evaluate: _Evaluate, dt: float
    ) -> tuple[dict[str, Any], DataArrayDict]:
        k1, diagnostics = evaluate(phi)
        phi_1 = {field: phi[field] + (dt / 3.0) * k1[field] for field in phi}
        k2, _ = evaluate(phi_1)
        phi_2 = {field: phi[field] + (dt / 2.0) * k2[field] for field in phi}
        k3, _ = evaluate(phi_2)
        return {field: phi[field] + dt * k3[field] for field in phi}, diagnostics


class _SSPRK3Scheme(_StepperBase):
    """Shu-Osher SSP RK3 (sympl's 3-stage SSPRungeKutta)."""

    def _integrate(
        self, phi: dict[str, Any], evaluate: _Evaluate, dt: float
    ) -> tuple[dict[str, Any], DataArrayDict]:
        k1, diagnostics = evaluate(phi)
        phi_1 = {field: phi[field] + dt * k1[field] for field in phi}
        k2, _ = evaluate(phi_1)
        phi_2 = {field: 0.75 * phi[field] + 0.25 * (phi_1[field] + dt * k2[field]) for field in phi}
        k3, _ = evaluate(phi_2)
        return {
            field: (phi[field] + 2.0 * (phi_2[field] + dt * k3[field])) / 3.0 for field in phi
        }, diagnostics


class _ForwardEulerTendencyStepper(_ForwardEulerScheme, TendencyStepper):
    name = "forward_euler"


class _HeunTendencyStepper(_HeunScheme, TendencyStepper):
    name = "rk2"


class _RK3WSTendencyStepper(_RK3WSScheme, TendencyStepper):
    name = "rk3ws"


class _SSPRK3TendencyStepper(_SSPRK3Scheme, TendencyStepper):
    name = "ssprk3"


class _ForwardEulerSequentialTendencyStepper(_ForwardEulerScheme, SequentialTendencyStepper):
    name = "forward_euler"


class _HeunSequentialTendencyStepper(_HeunScheme, SequentialTendencyStepper):
    name = "rk2"


class _RK3WSSequentialTendencyStepper(_RK3WSScheme, SequentialTendencyStepper):
    name = "rk3ws"


class _SSPRK3SequentialTendencyStepper(_SSPRK3Scheme, SequentialTendencyStepper):
    name = "ssprk3"
