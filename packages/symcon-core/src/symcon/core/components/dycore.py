"""``DynamicalCore`` — the three-cadence-tier core base class (SPEC S04).

Tasmania's base class for two-time-level, multi-stage cores (thesis §3.5,
Fig. 3.8-3.10), whose tier terminology Tasmania itself borrowed from ICON:

- **slow tier** — tendencies computed *outside* the core and consumed inside at
  the point the numerics dictate: the slow-tendency input port. Port slots are
  ordinary ``input_properties`` entries (state fields, ``icon:ddt_*`` convention;
  the :class:`~symcon.core.coupling.bus.SlowTendencyBus` is their checker); the
  ``tendency_port`` class attribute maps each prognostic to its slot. Slow
  tendencies are **held constant across the step** — the port buffers are never
  written.
- **fast tier** — an optional per-stage ``fast_tendency_component``
  (:class:`~symcon.core.coupling.concurrent.ConcurrentCoupling`) evaluated once
  per stage on the latest provisional state (FC *within* the core); its
  tendencies are summed onto the slow port values into per-stage scratch
  buffers. Empty in the ICON preset; the natural experiment port.
- **super-fast tier** — substepping with its own hook: stage ``s`` performs
  ``max(1, round(substep_fraction[s] · N))`` substeps of ``Δt/N`` each, where
  ``N`` comes from ``substeps`` (static) or ``ratio_provider`` (adaptive,
  CFL-style; called once per step with the state — the semantics shared with
  :class:`~symcon.core.components.wrappers.Subcycle`). Fig. 3.10's example is a
  3-stage Wicker-Skamarock core with ``N = 6`` and fractions (⅓, ½, 1) → 2, 3, 6
  substeps.

Subclass contract (frozen, SPEC S04): implement
``stage_array_call(stage, inputs, outputs, dt)`` and
``substep_array_call(stage, substep, inputs, outputs, dt)``; declare ``n_stages``
and ``substep_fraction``. Hooks receive raw buffers (the S03 ABI): ``inputs``
holds the latest provisional state plus the *combined* (slow + fast) tendency
values under the port slot names, and — inside substeps — the enclosing stage's
outputs under ``"stage/<name>"`` keys.

The orchestration is numpy-level T0 reference semantics (scratch buffers via
``numpy.empty_like``); the S05 plan compiler unrolls the tiers into the op list.
"""

from __future__ import annotations

import abc
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Any, ClassVar, cast

import numpy as np

from symcon.core.components.base import Component, DataArrayDict
from symcon.core.context import ComputeContext
from symcon.core.coupling.concurrent import ConcurrentCoupling
from symcon.core.state.dataarray import make_dataarray
from symcon.core.typing import FieldBuffer

if TYPE_CHECKING:
    from symcon.core.plan.bind import PlanBuilder

__all__ = ["DynamicalCore"]

#: Prefix under which substep hooks see the enclosing stage's outputs.
_STAGE_PREFIX = "stage/"


class DynamicalCore(Component):
    """Multi-stage, three-tier dynamical core base (frozen interface, SPEC S04).

    Stepper-shaped: ``(state, timestep, *, out=None) -> (diagnostics, new_state)``.
    Subclasses declare ``input_properties`` (prognostics + slow-port slots + any
    static fields), ``output_properties`` (the prognostics) and optionally
    ``diagnostic_properties``; every prognostic must also be an input, and
    ``tendency_port`` maps prognostics to their slow-tendency slot names.
    """

    output_dict_names: ClassVar[tuple[str, ...]] = (
        "diagnostic_properties",
        "output_properties",
    )
    timestep_required: ClassVar[bool] = True

    #: How the stage and super-fast tiers nest (S14, additive ClassVar):
    #: ``"stage_outer"`` — the Fig. 3.10 default this base class orchestrates
    #: (each stage runs its own substep block); ``"substep_outer"`` — ICON's
    #: nesting (every substep runs the full stage sequence,
    #: ``mo_nh_stepping.f90::perform_dyn_substepping``). A substep-outer core
    #: overrides ``array_call`` with its own orchestration **and** implements the
    #: plan-hook quartet the S05/S14 compiler unrolls the step into (all follow
    #: the materialized ``(*prefix, inputs, outputs, timestep)`` BoundCall pack):
    #:
    #: - ``plan_ingress(n_substeps, inputs, outputs, dt)`` — step entry: boundary
    #:   buffers → component-private state (§4.5); ``dt`` is the full Δt;
    #: - ``plan_substep_begin(substep, inputs, outputs, sub_dt)`` — the
    #:   component-private carry swaps that precede the substep's stages;
    #: - ``substep_array_call(stage, substep, inputs, outputs, sub_dt)`` — the
    #:   frozen S04 hook, one stage of one substep;
    #: - ``plan_substep_end(substep, inputs, outputs, sub_dt)`` — the private
    #:   time-level swap between substeps (not emitted after the last);
    #: - ``plan_egress(inputs, outputs, dt)`` — step exit: private state →
    #:   boundary output buffers, plus step bookkeeping.
    #:
    #: Private swaps stay inside these BoundCalls — the vault only ever holds
    #: boundary fields and their step-level ping-pong (§8.2/§4.5).
    substep_nesting: ClassVar[str] = "stage_outer"

    #: Number of stages of the time-marching scheme (subclass contract).
    n_stages: ClassVar[int] = 1
    #: Per-stage fraction of the total substep count ``N`` (scalar broadcasts).
    substep_fraction: ClassVar[float | tuple[float, ...]] = 1.0
    #: Prognostic field name -> input slot carrying its slow tendency (may be partial).
    tendency_port: ClassVar[Mapping[str, str]] = {}

    def __init__(
        self,
        *,
        fast_tendency_component: ConcurrentCoupling | None = None,
        substeps: int = 0,
        ratio_provider: Callable[[Mapping[str, Any]], int] | None = None,
        ctx: ComputeContext | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(ctx=ctx, name=name)
        if self.n_stages < 1:
            raise ValueError(f"{self.name}: n_stages must be >= 1, got {self.n_stages}.")
        fractions = (
            (float(self.substep_fraction),) * self.n_stages
            if isinstance(self.substep_fraction, int | float)
            else tuple(float(f) for f in self.substep_fraction)
        )
        if len(fractions) != self.n_stages:
            raise ValueError(
                f"{self.name}: substep_fraction has {len(fractions)} entries for "
                f"{self.n_stages} stages."
            )
        if any(not 0.0 < f <= 1.0 for f in fractions):
            raise ValueError(
                f"{self.name}: substep fractions must be in (0, 1], got {fractions!r}."
            )
        self._fractions = fractions

        if substeps < 0:
            raise ValueError(f"{self.name}: substeps must be >= 0, got {substeps}.")
        if substeps > 0 and ratio_provider is not None:
            raise ValueError(f"{self.name}: give at most one of substeps and ratio_provider.")
        self._substeps = substeps
        self._ratio_provider = ratio_provider
        self._resolved_substeps = substeps

        inputs = self._parsed_properties.get("input_properties", {})
        outputs = self._parsed_properties.get("output_properties", {})
        missing = [field for field in outputs if field not in inputs]
        if missing:
            raise ValueError(
                f"{self.name}: prognostics {missing!r} are not declared in "
                f"input_properties; a two-time-level core reads what it steps."
            )
        for field, slot in self.tendency_port.items():
            if field not in outputs:
                raise ValueError(
                    f"{self.name}: tendency_port maps {field!r}, which is not a "
                    f"prognostic (output_properties: {sorted(outputs)})."
                )
            if slot not in inputs:
                raise ValueError(
                    f"{self.name}: tendency_port slot {slot!r} (for {field!r}) is not "
                    f"declared in input_properties — the slow port is an input port."
                )
        if fast_tendency_component is not None:
            for field in parsed_tendencies(fast_tendency_component):
                if field not in self.tendency_port:
                    raise ValueError(
                        f"{self.name}: fast_tendency_component computes a tendency for "
                        f"{field!r}, but tendency_port declares no slot for it."
                    )
        self._fast = fast_tendency_component

    # -- introspection ---------------------------------------------------------------

    @property
    def fast_tendency_component(self) -> ConcurrentCoupling | None:
        """The per-stage fast coupling (empty in the ICON preset)."""
        return self._fast

    @property
    def substeps(self) -> int:
        """The static super-fast substep count (0 = tier disabled)."""
        return self._substeps

    @property
    def ratio_provider(self) -> Callable[[Mapping[str, Any]], int] | None:
        """The adaptive substep-count provider (shared semantics with Subcycle)."""
        return self._ratio_provider

    @property
    def substep_fractions(self) -> tuple[float, ...]:
        """``substep_fraction`` normalized to one entry per stage."""
        return self._fractions

    def visit(self, plan_builder: PlanBuilder) -> None:
        """S05 plan-compiler hook: unroll the stage/substep tiers (§8.2)."""
        plan_builder.visit_dynamical_core(self)

    # -- subclass hooks (frozen contract, SPEC S04) ------------------------------------

    @abc.abstractmethod
    def stage_array_call(
        self,
        stage: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        """Integrate one stage on raw buffers, writing every output in place.

        ``inputs``: the latest provisional state (field names) plus the combined
        slow+fast tendencies under the ``tendency_port`` slot names. ``outputs``:
        the stage's prognostic buffers plus the core's diagnostic buffers.
        ``dt`` is the full timestep; the stage's own coefficients decide spans.
        """

    @abc.abstractmethod
    def substep_array_call(
        self,
        stage: int,
        substep: int,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        dt: timedelta,
    ) -> None:
        """Integrate one super-fast substep on raw buffers.

        ``inputs``: the current substepped state (field names), the combined
        tendencies (slot names) and the enclosing stage's outputs under
        ``"stage/<name>"`` keys. ``dt`` is the substep size ``Δt/N``.
        """

    # -- the call path -----------------------------------------------------------------

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, Any] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Advance ``state`` one timestep; return ``(diagnostics, new_state)``."""
        if self._ratio_provider is not None:
            ratio = int(self._ratio_provider(state))
            if ratio < 1:
                raise ValueError(f"{self.name}: ratio_provider returned {ratio}; need >= 1.")
            self._resolved_substeps = ratio
        else:
            self._resolved_substeps = self._substeps
        wrapped = self._run(state, timestep, out)
        return wrapped["diagnostic_properties"], wrapped["output_properties"]

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        """Tier orchestration (Fig. 3.10); subclasses implement the hooks instead."""
        assert timestep is not None  # timestep_required: enforced by the base
        n_substeps = self._resolved_substeps
        prognostics = tuple(self._parsed_properties.get("output_properties", {}))
        diagnostics = {
            field: outputs[field]
            for field in self._parsed_properties.get("diagnostic_properties", {})
        }
        # Latest provisional state; ψⁿ views to start (never written in place).
        current: dict[str, FieldBuffer] = dict(inputs)

        for stage in range(self.n_stages):
            effective = self._effective_tendencies(current, timestep)
            stage_inputs = {**current, **effective}
            last_stage = stage == self.n_stages - 1
            n_sub = max(1, round(self._fractions[stage] * n_substeps)) if n_substeps else 0
            if last_stage and n_sub == 0:
                stage_out = {field: outputs[field] for field in prognostics}
            else:
                stage_out = {
                    field: cast(FieldBuffer, np.empty_like(current[field])) for field in prognostics
                }
            self.stage_array_call(stage, stage_inputs, {**stage_out, **diagnostics}, timestep)

            result: dict[str, FieldBuffer] = stage_out
            if n_sub:
                sub_dt = timestep / n_substeps
                stage_view = {f"{_STAGE_PREFIX}{f}": stage_out[f] for f in prognostics}
                sub_state = {field: current[field] for field in prognostics}
                for substep in range(n_sub):
                    if last_stage and substep == n_sub - 1:
                        sub_out = {field: outputs[field] for field in prognostics}
                    else:
                        sub_out = {
                            field: cast(FieldBuffer, np.empty_like(current[field]))
                            for field in prognostics
                        }
                    sub_inputs = {**current, **sub_state, **effective, **stage_view}
                    self.substep_array_call(
                        stage, substep, sub_inputs, {**sub_out, **diagnostics}, sub_dt
                    )
                    sub_state = sub_out
                result = sub_state
            current = dict(current)
            current.update(result)

    def _effective_tendencies(
        self, current: Mapping[str, FieldBuffer], timestep: timedelta
    ) -> dict[str, FieldBuffer]:
        """Slow port values + one fast-coupling evaluation, per stage (Fig. 3.9).

        Slot buffers without a fast contribution pass through untouched (constant
        by construction); slots with one get a fresh scratch sum, so the slow port
        is never written.
        """
        effective: dict[str, FieldBuffer] = {
            slot: current[slot] for slot in self.tendency_port.values()
        }
        if self._fast is None:
            return effective
        stage_state = self._wrap_state(current)
        tendencies, diagnostics = self._fast(stage_state, timestep)
        input_specs = self._parsed_properties.get("input_properties", {})
        for field, array in tendencies.items():
            slot = self.tendency_port[field]  # membership validated at construction
            effective[slot] = current[slot] + array.data
        for field, array in diagnostics.items():
            if field in input_specs:
                # Fast diagnostics feed the stage input (tasmania: update_swap).
                effective[field] = array.data
        return effective

    def _wrap_state(self, current: Mapping[str, FieldBuffer]) -> dict[str, Any]:
        """Wrap the provisional buffers for the fast coupling (T0; no ``time`` key)."""
        specs = self._parsed_properties.get("input_properties", {})
        state: dict[str, Any] = {}
        for field, buffer in current.items():
            spec = specs.get(field)
            if spec is None:
                continue
            state[field] = make_dataarray(
                buffer,
                name=field,
                dims=spec.dims,
                units=spec.units,
                location=spec.location,
            )
        return state


def parsed_tendencies(coupling: ConcurrentCoupling) -> tuple[str, ...]:
    """The tendency field names a coupling computes (helper for port validation)."""
    return tuple(coupling.parsed_properties.get("tendency_properties", {}))
