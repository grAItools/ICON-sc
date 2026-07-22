"""Bind-time plan compiler: the §8.2 negotiation/execution split (SPEC S05).

``ExecutionPlan.bind(composition, schema, ctx)`` walks the composition tree via
the ``visit(plan_builder)`` double-dispatch protocol implemented by every
S03/S04 container, runs the full sympl negotiation exactly once (S02/S03
``DynamicChecker``/``IngressPlan`` machinery, one negotiation per component
occurrence) and emits **symbolic op drafts** over a stable slot table. Federations
and pure-control-flow wrappers dissolve (§8.2):

- ``SequentialUpdateSplitting`` flattens into the op list;
- ``ParallelSplitting``'s recombination ψⁿ⁺¹ = Σψₗ - L·ψⁿ becomes one k-ary
  :class:`~icon_sc.core.plan.ops.Axpy` per field, term order replayed from the
  T0 implementation (seed ψ_l1, then per further section +ψ_l, -ψⁿ) so T0≡T1
  stays bitwise;
- ``SequentialTendencySplitting`` gets provisional slots plus one
  :class:`~icon_sc.core.plan.ops.DiffScale` per stepped field per section;
- ``SSUS`` doubles into the reversed λ·Δt pre-list, the core, and the forward
  (1-λ)·Δt post-list;
- ``CallingFrequency`` becomes per-signature cadence masks with its cached
  output living in persistent vault/tendency slots;
- ``Subcycle`` and ``DynamicalCore`` stage/substep tiers unroll with bound dt;
- ``ScalingWrapper`` folds into constant-coefficient ``Axpy`` ops.

State evolution is in-place where elementwise-safe (tendency integration) and
**ping-pong** for kernel-written outputs: every swapped field owns exactly one
``(vault cell, alternate cell)`` pair, and the compiler emits one op-list
variant per plan phase (even/odd x cadence signature) with buffer references
pre-bound — no runtime indirection (§8.2). ``run_step`` interprets the phase's
variant; ``plan_hash`` is a stable content hash of the symbolic plan.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import timedelta
from typing import Any, Protocol

import numpy as np

from icon_sc.core.components.base import Component, OutputSchema
from icon_sc.core.components.base import Monitor as BaseMonitor
from icon_sc.core.context import ComputeContext
from icon_sc.core.contracts.checkers import FieldSchema, StateSchema
from icon_sc.core.contracts.operators import IngressPlan
from icon_sc.core.contracts.properties import PropertySpec
from icon_sc.core.coupling.concurrent import (
    is_diagnostic_kind,
    is_tendency_kind,
    name_of,
    parsed_properties_of,
)
from icon_sc.core.coupling.steppers import (
    _ForwardEulerScheme,
    _HeunScheme,
    _RK3WSScheme,
    _SSPRK3Scheme,
    _StepperBase,
)
from icon_sc.core.plan.guards import PlanCompileError, StalePlanError, schema_fingerprint
from icon_sc.core.plan.interpreter import run_ops
from icon_sc.core.plan.ops import (
    Axpy,
    BoundCall,
    CadenceMask,
    DiffScale,
    SegmentMarker,
    Swap,
)
from icon_sc.core.state.vault import SlotMeta, StateVault
from icon_sc.core.typing import FieldBuffer, Location

__all__ = ["ExecutionPlan", "PlanBuilder"]

_MICROSECOND = timedelta(microseconds=1)
_STEPPER_DICTS = ("diagnostic_properties", "output_properties")
_MAX_PHASES = 256

#: The four registered scheme families the S05 compiler can emit (S04 built-ins).
_SCHEME_CLASSES: tuple[tuple[type, str], ...] = (
    (_ForwardEulerScheme, "forward_euler"),
    (_HeunScheme, "rk2"),
    (_RK3WSScheme, "rk3ws"),
    (_SSPRK3Scheme, "ssprk3"),
)


class PlanBuilder(Protocol):
    """Double-dispatch surface of the plan compiler (PLAN S05 item 3).

    Every S03/S04 container implements ``visit(plan_builder)`` forwarding to
    exactly one of these hooks; the same walk is reused by the post-slice halo
    validator.
    """

    def visit_component(self, component: Any) -> None: ...

    def visit_dynamical_core(self, core: Any) -> None: ...

    def visit_concurrent_coupling(self, coupling: Any) -> None: ...

    def visit_tendency_stepper(self, stepper: Any) -> None: ...

    def visit_sequential_tendency_stepper(self, stepper: Any) -> None: ...

    def visit_parallel_splitting(self, federation: Any) -> None: ...

    def visit_sequential_update_splitting(self, federation: Any) -> None: ...

    def visit_sequential_tendency_splitting(self, federation: Any) -> None: ...

    def visit_ssus(self, federation: Any) -> None: ...

    def visit_calling_frequency(self, wrapper: Any) -> None: ...

    def visit_subcycle(self, wrapper: Any) -> None: ...

    def visit_scaling_wrapper(self, wrapper: Any) -> None: ...


# -- symbolic layer -----------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _SlotDef:
    """One storage cell of the plan: a stable label over a buffer allocated once."""

    sid: int
    label: str
    field_name: str | None  # published field name (None for plan-private scratch)
    published: bool
    dims: tuple[str, ...]
    units: str
    dtype: np.dtype[Any]
    location: Location | None
    creator: Any = dataclasses.field(default=None, compare=False)
    spec: PropertySpec | None = dataclasses.field(default=None, compare=False)

    def describe(self) -> str:
        return (
            f"slot {self.sid} label={self.label} published={int(self.published)} "
            f"dims={','.join(self.dims)} units={self.units} dtype={self.dtype.str} "
            f"loc={self.location.value if self.location else '-'}"
        )


@dataclasses.dataclass(frozen=True)
class _DraftCall:
    component: Any = dataclasses.field(compare=False)
    method: str
    prefix: tuple[int, ...]
    inputs: tuple[tuple[str, int], ...]
    outputs: tuple[tuple[str, int], ...]
    timestep_us: int
    tag: str

    def describe(self) -> str:
        ins = ",".join(f"{f}:{s}" for f, s in self.inputs)
        outs = ",".join(f"{f}:{s}" for f, s in self.outputs)
        prefix = ",".join(str(p) for p in self.prefix)
        return (
            f"call tag={self.tag} method={self.method} prefix=({prefix}) "
            f"in=[{ins}] out=[{outs}] dt_us={self.timestep_us}"
        )


@dataclasses.dataclass(frozen=True)
class _DraftAxpy:
    y: int
    init: tuple[float, int] | None
    terms: tuple[tuple[float, int], ...]
    divisor: float
    tag: str

    def describe(self) -> str:
        init = f"{self.init[0].hex()}*{self.init[1]}" if self.init is not None else "-"
        terms = ",".join(f"{a.hex()}*{x}" for a, x in self.terms)
        return (
            f"axpy tag={self.tag} y={self.y} init={init} terms=[{terms}] div={self.divisor.hex()}"
        )


@dataclasses.dataclass(frozen=True)
class _DraftDiffScale:
    y: int
    minuend: int
    subtrahend: int
    divisor: float
    tag: str

    def describe(self) -> str:
        return (
            f"diffscale tag={self.tag} y={self.y} minuend={self.minuend} "
            f"subtrahend={self.subtrahend} div={self.divisor.hex()}"
        )


@dataclasses.dataclass(frozen=True)
class _DraftSwap:
    field: str
    vault_sid: int
    alt_sid: int
    tag: str

    def describe(self) -> str:
        return f"swap tag={self.tag} field={self.field} v={self.vault_sid} alt={self.alt_sid}"


@dataclasses.dataclass(frozen=True)
class _DraftMask:
    period: int
    phase: int
    ops: tuple[Any, ...]
    tag: str

    def describe(self) -> str:
        inner = "; ".join(op.describe() for op in self.ops)
        return f"mask tag={self.tag} period={self.period} phase={self.phase} ops=[{inner}]"


@dataclasses.dataclass(frozen=True)
class _DraftMarker:
    kind: str
    tag: str

    def describe(self) -> str:
        return f"marker kind={self.kind} tag={self.tag}"


_Draft = _DraftCall | _DraftAxpy | _DraftDiffScale | _DraftSwap | _DraftMask | _DraftMarker


@dataclasses.dataclass
class _EvalCtx:
    """One tendency-provider evaluation (a stepper stage or a raw coupling call)."""

    stage: int
    stage_env: dict[str, int]
    tendencies: dict[str, list[int]]
    diag_published: dict[str, int]
    in_cadence: bool = False


@dataclasses.dataclass
class _Bound:
    """A plan materialized against one vault: pre-bound runtime op variants."""

    vault: StateVault
    variants: tuple[tuple[Any, ...], ...]
    epoch: int
    schema_hash: str


def _classify_scheme(stepper: Any) -> str:
    for cls, name in _SCHEME_CLASSES:
        if isinstance(stepper, cls):
            return name
    raise PlanCompileError(
        f"plan compiler: stepper {name_of(stepper)!r} ({type(stepper).__name__}) is not "
        f"one of the four S04 built-in schemes (forward_euler, rk2, rk3ws, ssprk3); "
        f"user-registered schemes need a scheme emitter (post-S05)."
    )


def _dt_us(dt: timedelta) -> int:
    return dt // _MICROSECOND


class _Compiler:
    """One bind: composition x schema x ctx → slot table + per-phase draft lists."""

    def __init__(self, composition: Any, schema: StateSchema, ctx: ComputeContext) -> None:
        if ctx.timestep is None or ctx.timestep <= timedelta(0):
            raise PlanCompileError(
                "ExecutionPlan.bind: ctx.timestep must be a positive timedelta "
                "(the loop Δt is a bind-time constant, architecture §8.2)."
            )
        self._composition = composition
        self._schema0 = schema
        self._ctx = ctx
        self._timestep: timedelta = ctx.timestep

        self.slots: list[_SlotDef] = []
        self._slot_by_key: dict[Any, int] = {}
        self._pairs: dict[str, tuple[int, int]] = {}
        self.cadence_periods: set[int] = set()
        #: keyed by (walk path, component identity): a composite may dispatch
        #: several children at one path (S14 loop-body composites), and one
        #: component may occur at several paths (S05: one negotiation each).
        self._ingress_cache: dict[tuple[str, int], IngressPlan] = {}
        #: published diag name -> (writer path, inside cadence mask)
        self._diag_writers: dict[str, tuple[str, bool]] = {}

        # phase-local state
        self.phase = 0
        self.env: dict[str, int] = {}
        self._ops: list[_Draft] = []
        self._dt: timedelta = self._timestep
        self._path: list[str] = []
        self._output_binding: dict[str, int] | None = None
        self._eval: _EvalCtx | None = None
        self._in_cadence = False
        self._input_override: dict[str, int] | None = None
        self._post_scale: Mapping[str, Mapping[str, float]] | None = None
        self._seen_cf: set[int] = set()

        # canonical published cells for the bind schema
        self._env0: dict[str, int] = {}
        for name, field in schema.fields.items():
            sid = self._new_slot(
                key=("state", name),
                label=f"state/{name}",
                field_name=name,
                published=True,
                dims=field.dims,
                units=field.units,
                dtype=field.dtype,
                location=field.location,
            )
            self._env0[name] = sid

        self.phases: list[tuple[_Draft, ...]] = []
        self.period = 1

    # -- slot table -------------------------------------------------------------------

    def _new_slot(
        self,
        *,
        key: Any,
        label: str,
        field_name: str | None,
        published: bool,
        dims: tuple[str, ...],
        units: str,
        dtype: np.dtype[Any],
        location: Location | None,
        creator: Any = None,
        spec: PropertySpec | None = None,
    ) -> int:
        existing = self._slot_by_key.get(key)
        if existing is not None:
            return existing
        sid = len(self.slots)
        self.slots.append(
            _SlotDef(
                sid=sid,
                label=label,
                field_name=field_name,
                published=published,
                dims=dims,
                units=units,
                dtype=dtype,
                location=location,
                creator=creator,
                spec=spec,
            )
        )
        self._slot_by_key[key] = sid
        return sid

    def _published_cell(self, name: str, spec: PropertySpec, creator: Any) -> int:
        """The canonical vault cell of a published field (create on first write)."""
        existing = self._slot_by_key.get(("state", name))
        if existing is not None:
            return existing
        dtype = spec.dtype if spec.dtype is not None else np.dtype(np.float64)
        return self._new_slot(
            key=("state", name),
            label=f"state/{name}",
            field_name=name,
            published=True,
            dims=spec.dims,
            units=spec.units,
            dtype=dtype,
            location=spec.location,
            creator=creator,
            spec=spec,
        )

    def _scratch_like(self, key: Any, like_sid: int, label: str) -> int:
        like = self.slots[like_sid]
        return self._new_slot(
            key=("scratch", key),
            label=label,
            field_name=None,
            published=False,
            dims=like.dims,
            units=like.units,
            dtype=like.dtype,
            location=like.location,
        )

    def _pair_partner(self, field: str, ref_env: Mapping[str, int]) -> int:
        """The other cell of ``field``'s ping-pong pair (create the alt on demand)."""
        canonical = self._slot_by_key.get(("state", field))
        if canonical is None:
            raise PlanCompileError(f"plan compiler: no canonical cell for swapped field {field!r}.")
        pair = self._pairs.get(field)
        if pair is None:
            alt = self._scratch_like(("alt", field), canonical, f"alt/{field}")
            pair = (canonical, alt)
            self._pairs[field] = pair
        current = ref_env[field]
        if current == pair[0]:
            return pair[1]
        if current == pair[1]:
            return pair[0]
        raise PlanCompileError(
            f"plan compiler: field {field!r} is bound to cell {current}, outside its "
            f"ping-pong pair {pair} — unsupported slot topology."
        )

    # -- negotiation reuse (S02/S03 machinery) ------------------------------------------

    def _field_schema(self, sid: int) -> FieldSchema:
        slot = self.slots[sid]
        return FieldSchema(
            dims=slot.dims,
            units=slot.units,
            dtype=slot.dtype,
            device=self._ctx.device,
            location=slot.location,
        )

    def _schema_of_env(self, env: Mapping[str, int]) -> StateSchema:
        return StateSchema(fields={name: self._field_schema(sid) for name, sid in env.items()})

    def _ingress_bindings(
        self, component: Any, env: Mapping[str, int]
    ) -> tuple[tuple[str, int], ...]:
        """Pre-resolved input pack: contract field -> cell (alias-resolved, checked)."""
        spec = dict(parsed_properties_of(component).get("input_properties", {}))
        cache_key = (self._tag(), id(component))
        plan = self._ingress_cache.get(cache_key)
        if plan is None:
            try:
                plan = IngressPlan.build(
                    spec,
                    self._schema_of_env(env),
                    component=name_of(component),
                    device=self._ctx.device,
                )
            except KeyError as exc:
                raise PlanCompileError(f"bind ingress failed: {exc.args[0]}") from exc
            self._ingress_cache[cache_key] = plan
        override = self._input_override
        bindings: list[tuple[str, int]] = []
        for field, state_name in zip(plan.fields, plan.names, strict=True):
            if override is not None and field in override:
                bindings.append((field, override[field]))
            else:
                bindings.append((field, env[state_name]))
        return tuple(bindings)

    # -- draft emission helpers ----------------------------------------------------------

    def _tag(self) -> str:
        return "/".join(self._path)

    def _emit(self, draft: _Draft) -> None:
        self._ops.append(draft)

    def _emit_axpy(
        self,
        y: int,
        init: tuple[float, int] | None,
        terms: Sequence[tuple[float, int]],
        divisor: float = 1.0,
        note: str = "",
    ) -> None:
        if init is not None and init[1] == y and init[0] == 1.0:
            # y is its own seed: accumulate form (skip the identity multiply).
            init = None
        tag = self._tag() + (f"#{note}" if note else "")
        self._emit(_DraftAxpy(y=y, init=init, terms=tuple(terms), divisor=divisor, tag=tag))

    def _record_diag_write(self, name: str, path: str) -> None:
        held = self._diag_writers.get(name)
        if held is None:
            self._diag_writers[name] = (path, self._in_cadence)
            return
        held_path, held_cadence = held
        if held_path != path and (held_cadence or self._in_cadence):
            raise PlanCompileError(
                f"plan compiler: diagnostic {name!r} is written both by {held_path!r} "
                f"and {path!r} while one write sits under a CallingFrequency cadence "
                f"mask; the persistent-cache slot would be corrupted (S05 restriction)."
            )

    # -- the phase loop -------------------------------------------------------------------

    def compile(self) -> None:
        snapshots: list[dict[str, int]] = [dict(self._env0)]
        env = dict(self._env0)
        phase = 0
        while True:
            drafts, env = self._compile_phase(phase, env)
            self.phases.append(drafts)
            snapshots.append(dict(env))
            phase += 1
            lcm = math.lcm(1, *self.cadence_periods)
            if phase % (2 * lcm) == 0:
                candidate = phase // 2
                if (
                    candidate % lcm == 0
                    and snapshots[phase] == snapshots[candidate]
                    and self.phases[:candidate] == self.phases[candidate:phase]
                ):
                    self.phases = self.phases[:candidate]
                    self.period = candidate
                    return
            if phase > _MAX_PHASES:
                raise PlanCompileError(
                    f"plan compiler: no periodic steady state within {_MAX_PHASES} phases "
                    f"(cadence periods: {sorted(self.cadence_periods)})."
                )

    def _compile_phase(
        self, phase: int, env: dict[str, int]
    ) -> tuple[tuple[_Draft, ...], dict[str, int]]:
        self.phase = phase
        self.env = dict(env)
        self._ops = []
        self._dt = self._timestep
        self._path = ["root"]
        self._output_binding = None
        self._eval = None
        self._in_cadence = False
        self._input_override = None
        self._post_scale = None
        self._seen_cf = set()

        self._dispatch(self._composition)

        # end-of-step reconciliation: one Swap per field whose data moved cells.
        for field, start_sid in env.items():
            if self.env.get(field, start_sid) != start_sid:
                pair = self._pairs.get(field)
                if pair is None or self.env[field] not in pair or start_sid not in pair:
                    raise PlanCompileError(
                        f"plan compiler: field {field!r} ended the step outside its "
                        f"ping-pong pair — unsupported slot topology."
                    )
                self._emit(
                    _DraftSwap(field=field, vault_sid=pair[0], alt_sid=pair[1], tag=f"swap/{field}")
                )
        self._emit(_DraftMarker(kind="step_end", tag="root"))
        return tuple(self._ops), dict(self.env)

    # -- dispatch --------------------------------------------------------------------------

    def _dispatch(self, node: Any) -> None:
        if isinstance(node, BaseMonitor):
            raise PlanCompileError(
                f"plan compiler: {name_of(node)!r} is a Monitor — monitors are "
                f"excluded from the plan (S14). Pass them to "
                f"ctx.timeloop(monitors=...); they run in the SegmentMarker-"
                f"delimited host step between plan segments (§8.3)."
            )
        visit = getattr(node, "visit", None)
        if visit is None or not callable(visit):
            raise PlanCompileError(
                f"plan compiler: {name_of(node)!r} ({type(node).__name__}) implements no "
                f"visit(plan_builder) protocol; it cannot be compiled."
            )
        visit(self)

    def _emit_section(self, section: Any, binding: dict[str, int] | None) -> None:
        saved = self._output_binding
        self._output_binding = binding
        try:
            self._dispatch(section)
        finally:
            self._output_binding = saved

    # -- visit hooks (PlanBuilder) -----------------------------------------------------------

    def visit_component(self, component: Any) -> None:
        if self._eval is not None:
            self._emit_member(component)
            return
        names = tuple(getattr(component, "output_dict_names", ()))
        if names != _STEPPER_DICTS:
            raise PlanCompileError(
                f"plan compiler: {name_of(component)!r} (output_dict_names={names!r}) is "
                f"not Stepper-shaped and appears outside a tendency evaluation."
            )
        self._emit_bare_stepper(component)

    def visit_dynamical_core(self, core: Any) -> None:
        if self._eval is not None:
            raise PlanCompileError(
                f"plan compiler: DynamicalCore {name_of(core)!r} cannot sit inside a "
                f"tendency evaluation."
            )
        self._emit_dycore(core)

    def visit_concurrent_coupling(self, coupling: Any) -> None:
        if self._eval is None:
            self._emit_publishing_coupling(coupling)
            return
        for index, member in enumerate(coupling.components):
            self._path.append(f"m{index}")
            try:
                self._dispatch(member)
            finally:
                self._path.pop()

    def _emit_publishing_coupling(self, coupling: Any) -> None:
        """A top-level ConcurrentCoupling publishes its tendencies to state (S14).

        The §5.1/§4.2 LFC bus-publication pattern (SPEC S09's slow suite): at T0
        the run script evaluates the coupling once per step and merges the
        returned tendency dict into the state (``working.update(tendencies)``),
        so the tendency fields *are* state fields downstream. At T1 the members
        evaluate exactly as a stage-0 coupling walk (cadence masks included) and
        one Axpy per tendency field copies/sums the member contributions into
        the field's published cell — T0's ``acc = c1; acc += c2`` member order,
        replayed exactly (bitwise contract). On non-fire cadence phases the
        member ops are absent but the persistent member cells hold the cached
        output, so the per-step publication Axpy reproduces the
        ``CallingFrequency`` replay verbatim.
        """
        if self._output_binding is not None:
            raise PlanCompileError(
                "plan compiler: a publishing ConcurrentCoupling nested as a redirected "
                "section (inside PS/STS) is not supported."
            )
        ev = _EvalCtx(
            stage=0,
            stage_env=dict(self.env),
            tendencies={},
            diag_published={},
        )
        saved_eval = self._eval
        self._eval = ev
        self._path.append("pub")
        try:
            for index, member in enumerate(coupling.components):
                self._path.append(f"m{index}")
                try:
                    self._dispatch(member)
                finally:
                    self._path.pop()
        finally:
            self._path.pop()
            self._eval = saved_eval

        tendency_specs = parsed_properties_of(coupling).get("tendency_properties", {})
        self._path.append("pub.publish")
        try:
            for name, cells in ev.tendencies.items():
                spec = tendency_specs.get(name)
                if spec is None:
                    raise PlanCompileError(
                        f"plan compiler: publishing coupling {name_of(coupling)!r} "
                        f"produced a tendency {name!r} it does not declare."
                    )
                target = self._published_cell(name, spec, None)
                self._emit_axpy(target, (1.0, cells[0]), [(1.0, c) for c in cells[1:]], note=name)
                self.env[name] = target
        finally:
            self._path.pop()
        self.env.update(ev.diag_published)

    def visit_tendency_stepper(self, stepper: Any) -> None:
        binding = self._output_binding
        self._output_binding = None
        self._emit_scheme(stepper, forcing=None, binding=binding)

    def visit_sequential_tendency_stepper(self, stepper: Any) -> None:
        raise PlanCompileError(
            f"plan compiler: SequentialTendencyStepper {name_of(stepper)!r} needs a "
            f"provisional state; it is only compilable as a SequentialTendencySplitting "
            f"section."
        )

    def visit_sequential_update_splitting(self, federation: Any) -> None:
        if self._output_binding is not None:
            raise PlanCompileError(
                "plan compiler: a federation nested as a redirected section "
                "(inside PS/STS) is not supported in S05."
            )
        for index, stepper in enumerate(federation.sections):
            self._path.append(f"sus.s{index}")
            try:
                self._emit_section(stepper, None)
            finally:
                self._path.pop()

    def visit_parallel_splitting(self, federation: Any) -> None:
        if self._output_binding is not None:
            raise PlanCompileError(
                "plan compiler: a federation nested as a redirected section "
                "(inside PS/STS) is not supported in S05."
            )
        sections = tuple(federation.sections)
        # T0 PS sections all read ψⁿ: a section input produced as a sibling's
        # diagnostic would read the *new* value at T1 (canonical cells are shared).
        diag_names = [
            set(parsed_properties_of(s).get("diagnostic_properties", {})) for s in sections
        ]
        for index, section in enumerate(sections):
            inputs = set(parsed_properties_of(section).get("input_properties", {}))
            sibling_diags: set[str] = set()
            for other, names in enumerate(diag_names):
                if other != index:
                    sibling_diags |= names
            clash = inputs & sibling_diags
            if clash:
                raise PlanCompileError(
                    f"plan compiler: ParallelSplitting section {index} reads "
                    f"{sorted(clash)} which sibling sections write as diagnostics; "
                    f"T1 cannot reproduce T0's ψⁿ-snapshot reads here (S05 restriction)."
                )

        entry_env = dict(self.env)
        contributions: dict[str, list[int]] = {}
        diag_merge: dict[str, int] = {}
        for index, section in enumerate(sections):
            self.env = dict(entry_env)
            fields = tuple(parsed_properties_of(section).get("output_properties", {}))
            self._path.append(f"ps.s{index}")
            try:
                binding = {
                    f: self._scratch_like(
                        (self._tag(), "prov", f), entry_env[f], f"{self._tag()}/prov/{f}"
                    )
                    for f in fields
                }
                self._emit_section(section, binding)
            finally:
                self._path.pop()
            for name in diag_names[index]:
                if name in self.env:
                    diag_merge[name] = self.env[name]
            for f in fields:
                contributions.setdefault(f, []).append(binding[f])

        self.env = dict(entry_env)
        # Recombination ψⁿ⁺¹ = Σψₗ - L·ψⁿ (2.10d): T0 term order per field is
        # (ψ_l1, +ψ_l2, -ψⁿ, +ψ_l3, -ψⁿ, ...) — replayed exactly (bitwise contract).
        self._path.append("ps.recombine")
        try:
            for f, cells in contributions.items():
                target = self._pair_partner(f, entry_env)
                terms: list[tuple[float, int]] = []
                for cell in cells[1:]:
                    terms.append((1.0, cell))
                    terms.append((-1.0, entry_env[f]))
                self._emit_axpy(target, (1.0, cells[0]), terms, note=f)
                self.env[f] = target
        finally:
            self._path.pop()
        self.env.update(diag_merge)

    def visit_sequential_tendency_splitting(self, federation: Any) -> None:
        if self._output_binding is not None:
            raise PlanCompileError(
                "plan compiler: a federation nested as a redirected section "
                "(inside PS/STS) is not supported in S05."
            )
        sections = tuple(federation.sections)
        entry_env = dict(self.env)
        dt = self._dt.total_seconds()
        prov: dict[str, int] = {}

        first = sections[0]
        fields0 = tuple(parsed_properties_of(first).get("output_properties", {}))
        self._path.append("sts.s0")
        try:
            binding0 = {f: self._pair_partner(f, entry_env) for f in fields0}
            self._emit_section(first, binding0)
        finally:
            self._path.pop()
        prov.update(binding0)

        for index, stepper in enumerate(sections[1:], start=1):
            if not isinstance(stepper, _StepperBase):
                raise PlanCompileError(
                    f"plan compiler: STS section {index} ({name_of(stepper)!r}) is not a "
                    f"tendency-stepper instance."
                )
            self._path.append(f"sts.s{index}")
            try:
                forcing: dict[str, int] = {}
                for f in stepper.prognostics:
                    minuend = prov.get(f, entry_env[f])
                    cell = self._scratch_like(
                        (self._tag(), "forcing", f), entry_env[f], f"{self._tag()}/forcing/{f}"
                    )
                    self._emit(
                        _DraftDiffScale(
                            y=cell,
                            minuend=minuend,
                            subtrahend=self.env[f],
                            divisor=dt,
                            tag=f"{self._tag()}#forcing/{f}",
                        )
                    )
                    forcing[f] = cell
                binding = {f: self._pair_partner(f, entry_env) for f in stepper.prognostics}
                self._emit_scheme(stepper, forcing=forcing, binding=binding)
            finally:
                self._path.pop()
            prov.update(binding)

        for f, cell in prov.items():
            self.env[f] = cell

    def visit_ssus(self, federation: Any) -> None:
        if self._output_binding is not None:
            raise PlanCompileError(
                "plan compiler: a federation nested as a redirected section "
                "(inside PS/STS) is not supported in S05."
            )
        saved = self._dt
        pre_dt = saved * federation.lam  # timedelta * float: rounds like T0
        post_dt = saved - pre_dt  # exact complement (SSUS.__call__)
        self._path.append("ssus.pre")
        try:
            self._dt = pre_dt
            self._dispatch(federation.pre)
        finally:
            self._path.pop()
            self._dt = saved
        self._path.append("ssus.core")
        try:
            self._emit_section(federation.core, None)
        finally:
            self._path.pop()
        self._path.append("ssus.post")
        try:
            self._dt = post_dt
            self._dispatch(federation.post)
        finally:
            self._path.pop()
            self._dt = saved

    def visit_calling_frequency(self, wrapper: Any) -> None:
        ev = self._eval
        if ev is None:
            raise PlanCompileError(
                f"plan compiler: CallingFrequency {name_of(wrapper)!r} around a "
                f"Stepper-shaped component is not compilable in S05 (its cached output "
                f"would need copy-on-replay semantics); wrap tendency/diagnostic "
                f"components."
            )
        if self._in_cadence:
            raise PlanCompileError(
                f"plan compiler: nested CallingFrequency ({name_of(wrapper)!r}) is not "
                f"supported in S05."
            )
        if self._dt != self._timestep:
            raise PlanCompileError(
                f"plan compiler: CallingFrequency {name_of(wrapper)!r} under a scaled "
                f"timestep ({self._dt!r} vs loop {self._timestep!r}, e.g. inside SSUS "
                f"or Subcycle) has time-dependent firing the S05 cadence masks cannot "
                f"express."
            )
        if id(wrapper) in self._seen_cf:
            raise PlanCompileError(
                f"plan compiler: CallingFrequency {name_of(wrapper)!r} is evaluated more "
                f"than once per step — either it occurs twice in the composition or a "
                f"multi-stage scheme (rk2/rk3ws/ssprk3) re-evaluates its coupling per "
                f"stage. T0 fires once and replays the cache; expressing that replay at "
                f"T1 needs per-stage cache-slot aliasing the S05 compiler does not "
                f"implement (S05 restriction — use forward_euler around "
                f"CallingFrequency, or lift it out of the multi-stage section)."
            )
        self._seen_cf.add(id(wrapper))
        if wrapper.last_update_time is not None:
            raise PlanCompileError(
                f"plan compiler: CallingFrequency {name_of(wrapper)!r} carries a live "
                f"phase (last_update_time set); the S05 compiler binds fresh wrappers "
                f"only (restart phases are a follow-up)."
            )
        period = wrapper.period_for(self._timestep)
        steps = _dt_us(period) // _dt_us(self._timestep)
        if steps * _dt_us(self._timestep) != _dt_us(period):
            raise PlanCompileError(
                f"plan compiler: CallingFrequency period {period!r} is not an integer "
                f"multiple of the loop timestep {self._timestep!r}."
            )
        fires = self.phase % steps == 0 and ev.stage == 0
        self._path.append(f"cf{steps}")
        saved_ops = self._ops
        self._ops = []
        self._in_cadence = True
        ev.in_cadence = True
        try:
            self._dispatch(wrapper.component)
        finally:
            self._in_cadence = False
            ev.in_cadence = False
            self._path.pop()
            sink = self._ops
            self._ops = saved_ops
        if steps > 1:
            self.cadence_periods.add(steps)
        if fires:
            if steps == 1:
                self._ops.extend(sink)
            else:
                self._emit(_DraftMask(period=steps, phase=0, ops=tuple(sink), tag=self._tag()))
        # Non-fire phases (and stage > 0 re-evaluations) emit nothing: the wrapper's
        # cached output *is* the persistent cells the sink ops would have written —
        # cell registration and env effects above already happened (§8.2 LFC).

    def visit_subcycle(self, wrapper: Any) -> None:
        if self._eval is not None:
            raise PlanCompileError(
                f"plan compiler: Subcycle {name_of(wrapper)!r} wraps Steppers; it cannot "
                f"sit inside a tendency evaluation."
            )
        n = wrapper.n
        if n is None:
            raise PlanCompileError(
                f"plan compiler: Subcycle {name_of(wrapper)!r} uses an adaptive "
                f"ratio_provider; adaptive substep counts are a T2 signature-cache "
                f"feature (post-S05)."
            )
        inner = wrapper.component
        parsed = parsed_properties_of(inner)
        fields = tuple(parsed.get("output_properties", {}))
        diag_clash = set(parsed.get("input_properties", {})) & set(
            parsed.get("diagnostic_properties", {})
        )
        if diag_clash:
            raise PlanCompileError(
                f"plan compiler: Subcycle over {name_of(inner)!r}: inputs {sorted(diag_clash)} "
                f"are also its diagnostics; T0 substeps do not chain diagnostics, so T1 "
                f"cell reuse would diverge (S05 restriction)."
            )
        binding = self._output_binding
        self._output_binding = None
        entry_env = dict(self.env)
        saved_dt = self._dt
        sub_dt = saved_dt / n  # exact T0 expression (Subcycle.__call__)
        self._dt = sub_dt
        try:
            for index in range(n):
                last = index == n - 1
                self._path.append(f"sub{index}")
                try:
                    if last:
                        target = (
                            binding
                            if binding is not None
                            else {f: self._pair_partner(f, entry_env) for f in fields}
                        )
                    else:
                        target = {
                            f: self._scratch_like(
                                ("/".join(self._path[:-1]), "subchain", index % 2, f),
                                entry_env[f],
                                f"{self._tag()}/chain{index % 2}/{f}",
                            )
                            for f in fields
                        }
                    self._emit_section(inner, target)
                finally:
                    self._path.pop()
                for f in fields:
                    self.env[f] = target[f]
        finally:
            self._dt = saved_dt
        if binding is not None:
            # Redirected: the caller owns env bookkeeping for the stepped fields
            # (final values live in the caller's binding cells).
            for f in fields:
                self.env[f] = entry_env[f]

    def visit_scaling_wrapper(self, wrapper: Any) -> None:
        inner = wrapper.component
        if not isinstance(inner, Component):
            raise PlanCompileError(
                f"plan compiler: ScalingWrapper around {name_of(inner)!r} "
                f"({type(inner).__name__}) is only compilable around leaf components "
                f"in S05."
            )
        if self._post_scale is not None or self._input_override is not None:
            raise PlanCompileError(
                "plan compiler: nested ScalingWrappers are not supported in S05."
            )
        factors = wrapper.scale_factors
        env = self._eval.stage_env if self._eval is not None else self.env
        override: dict[str, int] = {}
        self._path.append("scale")
        try:
            for name, factor in factors["input_scale_factors"].items():
                if name not in env:
                    raise PlanCompileError(
                        f"plan compiler: ScalingWrapper input scale target {name!r} is "
                        f"missing from the bound state."
                    )
                cell = self._scratch_like(
                    (self._tag(), "scaled_in", name), env[name], f"{self._tag()}/in/{name}"
                )
                # T0: array.data * float(factor) — one scalar multiply.
                self._emit_axpy(cell, (float(factor), env[name]), (), note=f"in/{name}")
                override[name] = cell
        finally:
            self._path.pop()
        self._input_override = override or None
        self._post_scale = {
            "tendency_properties": dict(factors["tendency_scale_factors"]),
            "diagnostic_properties": dict(factors["diagnostic_scale_factors"]),
            "output_properties": dict(factors["output_scale_factors"]),
        }
        try:
            self._dispatch(inner)
        finally:
            self._input_override = None
            self._post_scale = None

    # -- leaf emitters ------------------------------------------------------------------------

    def _apply_post_scale(self, component: Any, outputs: Mapping[str, int]) -> None:
        post = self._post_scale
        if post is None:
            return
        for dict_name in getattr(component, "output_dict_names", ()):
            for name, factor in post.get(dict_name, {}).items():
                if name in outputs:
                    cell = outputs[name]
                    # T0: part[name].data[...] *= float(factor) — in-place scale.
                    self._emit_axpy(cell, (float(factor), cell), (), note=f"scale/{name}")

    def _emit_member(self, component: Any) -> None:
        """One coupling member evaluation (tendency- or diagnostic-kind leaf)."""
        ev = self._eval
        assert ev is not None
        if not (is_tendency_kind(component) or is_diagnostic_kind(component)):
            raise PlanCompileError(
                f"plan compiler: {name_of(component)!r} is neither tendency- nor "
                f"diagnostic-kind; Steppers belong in federations, not couplings."
            )
        parsed = parsed_properties_of(component)
        inputs = self._ingress_bindings(component, ev.stage_env)
        outputs: dict[str, int] = {}
        path = self._tag()
        stage_key = 0 if ev.in_cadence else ev.stage
        for dict_name in component.output_dict_names:
            for name, spec in parsed.get(dict_name, {}).items():
                if dict_name == "tendency_properties":
                    like = self._slot_by_key.get(("state", name))
                    dtype = (
                        spec.dtype
                        if spec.dtype is not None
                        else (self.slots[like].dtype if like is not None else np.dtype(np.float64))
                    )
                    sid = self._new_slot(
                        key=("scratch", (path, "tend", stage_key, name)),
                        label=f"{path}/tend{stage_key}/{name}",
                        field_name=None,
                        published=False,
                        dims=spec.dims,
                        units=spec.units,
                        dtype=dtype,
                        location=spec.location,
                    )
                    ev.tendencies.setdefault(name, []).append(sid)
                elif ev.stage == 0 or ev.in_cadence:
                    sid = self._published_cell(name, spec, component)
                    self._record_diag_write(name, path)
                    ev.stage_env[name] = sid
                    ev.diag_published[name] = sid
                else:
                    sid = self._scratch_like(
                        (path, "diag", ev.stage, name),
                        self._published_cell(name, spec, component),
                        f"{path}/diag{ev.stage}/{name}",
                    )
                    ev.stage_env[name] = sid
                outputs[name] = sid
        self._emit(
            _DraftCall(
                component=component,
                method="array_call",
                prefix=(),
                inputs=inputs,
                outputs=tuple(outputs.items()),
                timestep_us=_dt_us(self._dt),
                tag=f"{path}/{name_of(component)}",
            )
        )
        self._apply_post_scale(component, outputs)

    def _emit_bare_stepper(self, component: Any) -> None:
        """A Stepper-kind leaf: one BoundCall with ping-pong outputs (T0: fresh arrays)."""
        binding = self._output_binding
        self._output_binding = None
        parsed = parsed_properties_of(component)
        inputs = self._ingress_bindings(component, self.env)
        outputs: dict[str, int] = {}
        path = self._tag()
        diag_cells: dict[str, int] = {}
        out_cells: dict[str, int] = {}
        for name, spec in parsed.get("diagnostic_properties", {}).items():
            sid = self._published_cell(name, spec, component)
            self._record_diag_write(name, path)
            diag_cells[name] = sid
            outputs[name] = sid
        for name, spec in parsed.get("output_properties", {}).items():
            if binding is not None:
                sid = binding[name]
            elif name in self.env:
                sid = self._pair_partner(name, self.env)
            else:
                sid = self._published_cell(name, spec, component)
            out_cells[name] = sid
            outputs[name] = sid
        self._emit(
            _DraftCall(
                component=component,
                method="array_call",
                prefix=(),
                inputs=inputs,
                outputs=tuple(outputs.items()),
                timestep_us=_dt_us(self._dt),
                tag=f"{path}/{name_of(component)}",
            )
        )
        self._apply_post_scale(component, outputs)
        self.env.update(diag_cells)
        if binding is None:
            self.env.update(out_cells)

    def _emit_scheme(
        self,
        stepper: Any,
        *,
        forcing: dict[str, int] | None,
        binding: dict[str, int] | None,
    ) -> None:
        """One TendencyStepper/SequentialTendencyStepper: stages as evaluate + Axpy.

        Reproduces the T0 ``_integrate`` arithmetic of the four S04 schemes as the
        exact ufunc sequences of :class:`~icon_sc.core.plan.ops.Axpy` (bitwise
        contract; coefficients are the same Python floats T0 computes).
        """
        scheme = _classify_scheme(stepper)
        self._path.append(f"{scheme}")
        try:
            dt_td = self._dt
            dt = dt_td.total_seconds()
            prognostics = tuple(stepper.prognostics)
            for f in prognostics:
                if f not in self.env:
                    raise PlanCompileError(
                        f"plan compiler: prognostic {f!r} of {name_of(stepper)!r} is "
                        f"missing from the bound state."
                    )
            phi = {f: self.env[f] for f in prognostics}
            path = self._tag()
            coupling = stepper.coupling
            diag_published: dict[str, int] = {}

            def evaluate(stage: int, stage_phi: Mapping[str, int]) -> dict[str, int]:
                ev = _EvalCtx(
                    stage=stage,
                    stage_env={**self.env, **stage_phi},
                    tendencies={},
                    diag_published={},
                )
                saved_eval = self._eval
                self._eval = ev
                self._path.append(f"stage{stage}")
                try:
                    self._dispatch(coupling)
                finally:
                    self._path.pop()
                    self._eval = saved_eval
                if stage == 0:
                    diag_published.update(ev.diag_published)
                ks: dict[str, int] = {}
                for f in prognostics:
                    cells = ev.tendencies.get(f)
                    if not cells:
                        raise PlanCompileError(
                            f"plan compiler: coupling of {name_of(stepper)!r} produced no "
                            f"tendency for prognostic {f!r}."
                        )
                    if len(cells) == 1:
                        ksum = cells[0]
                    else:
                        # T0 ConcurrentCoupling: acc = c1; acc += c2; ... (member order).
                        ksum = self._scratch_like(
                            (path, "ksum", stage, f), phi[f], f"{path}/ksum{stage}/{f}"
                        )
                        self._emit_axpy(
                            ksum,
                            (1.0, cells[0]),
                            [(1.0, c) for c in cells[1:]],
                            note=f"ksum{stage}/{f}",
                        )
                    if forcing is not None:
                        # T0: tendencies[f].data + forcing[f] (steppers._make_evaluate).
                        kf = self._scratch_like(
                            (path, "kf", stage, f), phi[f], f"{path}/kf{stage}/{f}"
                        )
                        self._emit_axpy(kf, (1.0, ksum), [(1.0, forcing[f])], note=f"kf{stage}/{f}")
                        ksum = kf
                    ks[f] = ksum
                return ks

            def stage_cells(kind: str) -> dict[str, int]:
                return {
                    f: self._scratch_like((path, kind, f), phi[f], f"{path}/{kind}/{f}")
                    for f in prognostics
                }

            def final(f: str, terms: Sequence[tuple[float, int]], divisor: float = 1.0) -> None:
                y = binding[f] if binding is not None else phi[f]
                self._emit_axpy(y, (1.0, phi[f]), terms, divisor=divisor, note=f"final/{f}")

            if scheme == "forward_euler":
                k1 = evaluate(0, phi)
                for f in prognostics:
                    final(f, [(dt, k1[f])])  # T0: phi + dt*k1
            elif scheme == "rk2":
                k1 = evaluate(0, phi)
                phi1 = stage_cells("phi1")
                for f in prognostics:
                    self._emit_axpy(phi1[f], (1.0, phi[f]), [(dt, k1[f])], note=f"phi1/{f}")
                k2 = evaluate(1, phi1)
                s = stage_cells("k1k2")
                for f in prognostics:
                    # T0: 0.5*dt*(k1 + k2) — one array add, then one scalar multiply.
                    self._emit_axpy(s[f], (1.0, k1[f]), [(1.0, k2[f])], note=f"k1k2/{f}")
                    final(f, [(0.5 * dt, s[f])])
            elif scheme == "rk3ws":
                k1 = evaluate(0, phi)
                phi1 = stage_cells("phi1")
                for f in prognostics:
                    self._emit_axpy(phi1[f], (1.0, phi[f]), [(dt / 3.0, k1[f])], note=f"phi1/{f}")
                k2 = evaluate(1, phi1)
                phi2 = stage_cells("phi2")
                for f in prognostics:
                    self._emit_axpy(phi2[f], (1.0, phi[f]), [(dt / 2.0, k2[f])], note=f"phi2/{f}")
                k3 = evaluate(2, phi2)
                for f in prognostics:
                    final(f, [(dt, k3[f])])  # T0: phi + dt*k3
            else:  # ssprk3
                k1 = evaluate(0, phi)
                phi1 = stage_cells("phi1")
                for f in prognostics:
                    self._emit_axpy(phi1[f], (1.0, phi[f]), [(dt, k1[f])], note=f"phi1/{f}")
                k2 = evaluate(1, phi1)
                u = stage_cells("u")
                phi2 = stage_cells("phi2")
                for f in prognostics:
                    # T0: 0.75*phi + 0.25*(phi1 + dt*k2)
                    self._emit_axpy(u[f], (1.0, phi1[f]), [(dt, k2[f])], note=f"u/{f}")
                    self._emit_axpy(phi2[f], (0.75, phi[f]), [(0.25, u[f])], note=f"phi2/{f}")
                k3 = evaluate(2, phi2)
                v = stage_cells("v")
                for f in prognostics:
                    # T0: (phi + 2.0*(phi2 + dt*k3)) / 3.0
                    self._emit_axpy(v[f], (1.0, phi2[f]), [(dt, k3[f])], note=f"v/{f}")
                    final(f, [(2.0, v[f])], divisor=3.0)

            self.env.update(diag_published)
        finally:
            self._path.pop()

    def _emit_dycore(self, core: Any) -> None:
        """Unroll the DynamicalCore stage/substep tiers with bound dt (§8.2)."""
        if core.fast_tendency_component is not None:
            raise PlanCompileError(
                f"plan compiler: DynamicalCore {name_of(core)!r} has a "
                f"fast_tendency_component; compiling the per-stage fast tier needs "
                f"per-stage coupling evaluation on provisional state (post-slice "
                f"follow-up; T0 runs it fine)."
            )
        if core.ratio_provider is not None:
            raise PlanCompileError(
                f"plan compiler: DynamicalCore {name_of(core)!r} uses an adaptive "
                f"ratio_provider; adaptive substep counts are a T2 signature-cache "
                f"feature (post-S05)."
            )
        nesting = str(getattr(core, "substep_nesting", "stage_outer"))
        if nesting == "substep_outer":
            self._emit_dycore_substep_outer(core)
            return
        if nesting != "stage_outer":
            raise PlanCompileError(
                f"plan compiler: DynamicalCore {name_of(core)!r} declares "
                f"substep_nesting={nesting!r}; known nestings are 'stage_outer' "
                f"(Fig. 3.10) and 'substep_outer' (ICON, S14)."
            )
        binding = self._output_binding
        self._output_binding = None
        parsed = parsed_properties_of(core)
        dt_td = self._dt
        n_substeps = int(core.substeps)
        fractions = tuple(core.substep_fractions)
        n_stages = int(core.n_stages)
        prognostics = tuple(parsed.get("output_properties", {}))
        path = self._tag()

        base_inputs = dict(self._ingress_bindings(core, self.env))
        diag_cells: dict[str, int] = {}
        for name, spec in parsed.get("diagnostic_properties", {}).items():
            sid = self._published_cell(name, spec, core)
            self._record_diag_write(name, f"{path}/{name_of(core)}")
            diag_cells[name] = sid

        entry_env = dict(self.env)
        final_targets = (
            binding
            if binding is not None
            else {f: self._pair_partner(f, entry_env) for f in prognostics}
        )

        current = {f: base_inputs[f] for f in prognostics}
        for stage in range(n_stages):
            last_stage = stage == n_stages - 1
            n_sub = max(1, round(fractions[stage] * n_substeps)) if n_substeps else 0
            stage_inputs = {**base_inputs, **current}
            if last_stage and n_sub == 0:
                stage_out = dict(final_targets)
            else:
                stage_out = {
                    f: self._scratch_like(
                        (path, "stage", stage, f), entry_env[f], f"{path}/stage{stage}/{f}"
                    )
                    for f in prognostics
                }
            self._emit(
                _DraftCall(
                    component=core,
                    method="stage_array_call",
                    prefix=(stage,),
                    inputs=tuple(stage_inputs.items()),
                    outputs=tuple({**stage_out, **diag_cells}.items()),
                    timestep_us=_dt_us(dt_td),
                    tag=f"{path}/{name_of(core)}/stage{stage}",
                )
            )
            result = stage_out
            if n_sub:
                sub_dt = dt_td / n_substeps  # exact T0 expression (dycore.array_call)
                stage_view = {f"stage/{f}": stage_out[f] for f in prognostics}
                sub_state = dict(current)
                for substep in range(n_sub):
                    if last_stage and substep == n_sub - 1:
                        sub_out = dict(final_targets)
                    else:
                        sub_out = {
                            f: self._scratch_like(
                                (path, "subchain", stage, substep % 2, f),
                                entry_env[f],
                                f"{path}/stage{stage}chain{substep % 2}/{f}",
                            )
                            for f in prognostics
                        }
                    sub_inputs = {**base_inputs, **current, **sub_state, **stage_view}
                    self._emit(
                        _DraftCall(
                            component=core,
                            method="substep_array_call",
                            prefix=(stage, substep),
                            inputs=tuple(sub_inputs.items()),
                            outputs=tuple({**sub_out, **diag_cells}.items()),
                            timestep_us=_dt_us(sub_dt),
                            tag=f"{path}/{name_of(core)}/stage{stage}sub{substep}",
                        )
                    )
                    sub_state = sub_out
                result = sub_state
            current = dict(result)

        self.env.update(diag_cells)
        if binding is None:
            self.env.update(final_targets)

    #: The plan-hook quartet a substep-outer core must implement (S14; the
    #: contract is documented on ``DynamicalCore.substep_nesting``).
    _SUBSTEP_OUTER_HOOKS = (
        "plan_ingress",
        "plan_substep_begin",
        "substep_array_call",
        "plan_substep_end",
        "plan_egress",
    )

    def _emit_dycore_substep_outer(self, core: Any) -> None:
        """Unroll ICON's substep-outer nesting: substeps outer, stages inner (S14).

        Emits the exact op order of ``mo_nh_stepping.f90::perform_dyn_substepping``
        / the icon4py driver ``_do_dyn_substepping`` (REFERENCES.lock
        ``icon4py-driver-substep-op-order``, ``icon-fortran-substep-op-order``):
        step ingress, then per substep the private carry swaps
        (``plan_substep_begin``), the full stage sequence, and the private
        time-level swap between substeps (``plan_substep_end``, postponed past
        the last substep), then step egress. All data flows through the
        component-private state (§4.5): the hooks are plain BoundCalls sharing
        one pre-bound boundary pack, and the **only** vault-visible effect is the
        step-level ping-pong of the boundary prognostics — the per-substep
        internal swaps never leak into the even/odd variants (PLAN S14 pitfall).
        """
        missing = [h for h in self._SUBSTEP_OUTER_HOOKS if not callable(getattr(core, h, None))]
        if missing:
            raise PlanCompileError(
                f"plan compiler: substep-outer DynamicalCore {name_of(core)!r} lacks "
                f"plan hooks {missing!r} (contract: DynamicalCore.substep_nesting)."
            )
        n_substeps = int(core.substeps)
        if n_substeps < 1:
            raise PlanCompileError(
                f"plan compiler: substep-outer DynamicalCore {name_of(core)!r} has "
                f"substeps={n_substeps}; the substep tier is mandatory for the ICON "
                f"nesting (every substep runs the full stage sequence)."
            )
        dt_td = self._dt
        sub_dt = dt_td / n_substeps  # exact T0 expression (NonhydroSolver.array_call)
        if sub_dt * n_substeps != dt_td:
            raise PlanCompileError(
                f"plan compiler: timestep {dt_td} is not divisible into {n_substeps} "
                f"substeps at timedelta (microsecond) resolution; choose a compatible "
                f"Δt/substeps pair (the T0 array_call refuses the same split)."
            )
        binding = self._output_binding
        self._output_binding = None
        parsed = parsed_properties_of(core)
        n_stages = int(core.n_stages)
        prognostics = tuple(parsed.get("output_properties", {}))
        path = self._tag()

        inputs = self._ingress_bindings(core, self.env)
        diag_cells: dict[str, int] = {}
        for name, spec in parsed.get("diagnostic_properties", {}).items():
            sid = self._published_cell(name, spec, core)
            self._record_diag_write(name, f"{path}/{name_of(core)}")
            diag_cells[name] = sid

        entry_env = dict(self.env)
        final_targets = (
            binding
            if binding is not None
            else {f: self._pair_partner(f, entry_env) for f in prognostics}
        )
        outputs = tuple({**final_targets, **diag_cells}.items())
        tag = f"{path}/{name_of(core)}"

        def call(method: str, prefix: tuple[int, ...], dt: timedelta, note: str) -> None:
            self._emit(
                _DraftCall(
                    component=core,
                    method=method,
                    prefix=prefix,
                    inputs=inputs,
                    outputs=outputs,
                    timestep_us=_dt_us(dt),
                    tag=f"{tag}/{note}",
                )
            )

        call("plan_ingress", (n_substeps,), dt_td, "ingress")
        for substep in range(n_substeps):
            call("plan_substep_begin", (substep,), sub_dt, f"sub{substep}/begin")
            for stage in range(n_stages):
                call("substep_array_call", (stage, substep), sub_dt, f"stage{stage}sub{substep}")
            if substep != n_substeps - 1:
                call("plan_substep_end", (substep,), sub_dt, f"sub{substep}/end")
        call("plan_egress", (), dt_td, "egress")

        self.env.update(diag_cells)
        if binding is None:
            self.env.update(final_targets)

    # -- serialization ---------------------------------------------------------------------

    def describe(self) -> str:
        lines = [
            f"schema {schema_fingerprint(self._schema0)}",
            (
                # backend_name, not the raw backend: a Backend *object* reprs
                # with live executor objects (memory addresses), which would
                # make plan_hash instance-dependent (S14 fix; string backends
                # are unaffected — their name is the string itself).
                f"ctx backend={self._ctx.backend_name} strict={self._ctx.strict} "
                f"tier={self._ctx.tier} timestep_us={_dt_us(self._timestep)} "
                f"device={self._ctx.device}"
            ),
        ]
        lines.extend(slot.describe() for slot in self.slots)
        for phase, drafts in enumerate(self.phases):
            lines.append(f"phase {phase} of {self.period}:")
            lines.extend(f"  {draft.describe()}" for draft in drafts)
        return "\n".join(lines)


class ExecutionPlan:
    """The frozen product of one bind (frozen interface, SPEC S05).

    ``ExecutionPlan.bind(composition, schema, ctx)`` compiles; ``run_step(vault,
    step_index)`` interprets the pre-bound op variant of the step's signature
    (T1). Materialization against a concrete vault happens lazily on the first
    ``run_step`` (buffers become available only then); ``plan_hash`` and
    ``signatures`` are properties of the symbolic plan and stable across
    processes.
    """

    def __init__(self, compiler: _Compiler) -> None:
        self._compiler = compiler
        self._describe = compiler.describe()
        self._hash = hashlib.sha256(self._describe.encode()).hexdigest()
        self._bound: _Bound | None = None
        self._cursor = 0

    @classmethod
    def bind(cls, composition: Any, schema: StateSchema, ctx: ComputeContext) -> ExecutionPlan:
        """Compile ``composition`` against ``schema``/``ctx`` (frozen interface)."""
        compiler = _Compiler(composition, schema, ctx)
        compiler.compile()
        return cls(compiler)

    @property
    def plan_hash(self) -> str:
        """Stable content hash of the symbolic plan (frozen interface)."""
        return self._hash

    @property
    def signatures(self) -> tuple[str, ...]:
        """Labels of the distinct step signatures (one op-list variant each)."""
        period = self._compiler.period
        return tuple(f"step {p} (mod {period})" for p in range(period))

    @property
    def schema(self) -> StateSchema:
        """The bind-time state schema (input to :func:`bind`)."""
        return self._compiler._schema0

    def describe(self) -> str:
        """Canonical plan serialization (the ``plan_hash`` preimage)."""
        return self._describe

    # -- materialization ------------------------------------------------------------------

    def _materialize(self, vault: StateVault) -> _Bound:
        compiler = self._compiler
        ctx = compiler._ctx
        for name, field in compiler._schema0.fields.items():
            index = vault.names.get(name)
            if index is None:
                raise StalePlanError(
                    f"plan/vault mismatch: bound field {name!r} is missing from the vault."
                )
            meta = vault.meta(index)
            if meta.dims != field.dims or meta.units != field.units or meta.dtype != field.dtype:
                raise StalePlanError(
                    f"plan/vault mismatch on {name!r}: vault has (dims={meta.dims!r}, "
                    f"units={meta.units!r}, dtype={meta.dtype}), plan bound (dims="
                    f"{field.dims!r}, units={field.units!r}, dtype={field.dtype})."
                )
        dim_sizes = vault.dim_sizes()

        def shape_of(slot: _SlotDef) -> tuple[int, ...]:
            try:
                return tuple(dim_sizes[d] for d in slot.dims)
            except KeyError as exc:
                raise StalePlanError(
                    f"plan/vault mismatch: dim {exc.args[0]!r} of slot {slot.label!r} "
                    f"has no length in the vault."
                ) from None

        contents: list[FieldBuffer] = []
        for slot in compiler.slots:
            if slot.published:
                assert slot.field_name is not None
                index = vault.names.get(slot.field_name)
                if index is None:
                    shape = shape_of(slot)
                    if slot.creator is not None and slot.spec is not None:
                        buffer = slot.creator.allocate_output(
                            slot.field_name, OutputSchema(slot.spec, shape, slot.dtype), ctx
                        )
                    else:
                        buffer = ctx.require_allocator.empty(shape, slot.dtype)
                    vault.add_slot(
                        slot.field_name,
                        buffer,
                        SlotMeta(
                            name=slot.field_name,
                            dims=slot.dims,
                            units=slot.units,
                            location=slot.location,
                            dtype=slot.dtype,
                            attrs={"units": slot.units, "location": slot.location},
                        ),
                    )
                    contents.append(buffer)
                else:
                    contents.append(vault.buffers[index])
            else:
                contents.append(ctx.require_allocator.empty(shape_of(slot), slot.dtype))

        scratch_pool: dict[tuple[tuple[int, ...], str], FieldBuffer] = {}

        def scratch_for(sid: int) -> Any:
            slot = compiler.slots[sid]
            key = (shape_of(slot), slot.dtype.str)
            buffer = scratch_pool.get(key)
            if buffer is None:
                buffer = ctx.require_allocator.empty(key[0], slot.dtype)
                scratch_pool[key] = buffer
            return buffer

        def materialize_one(draft: _Draft) -> Any:
            if isinstance(draft, _DraftCall):
                fn = getattr(draft.component, draft.method)
                inputs = {field: contents[sid] for field, sid in draft.inputs}
                outputs = {field: contents[sid] for field, sid in draft.outputs}
                args: tuple[Any, ...] = (
                    *draft.prefix,
                    inputs,
                    outputs,
                    timedelta(microseconds=draft.timestep_us),
                )
                return BoundCall(fn=fn, args=args, tag=draft.tag)
            if isinstance(draft, _DraftAxpy):
                init = (draft.init[0], contents[draft.init[1]]) if draft.init is not None else None
                terms = tuple((a, contents[x]) for a, x in draft.terms)
                return Axpy(
                    y=contents[draft.y],
                    init=init,
                    terms=terms,
                    scratch=scratch_for(draft.y) if terms else None,
                    divisor=draft.divisor,
                    tag=draft.tag,
                )
            if isinstance(draft, _DraftDiffScale):
                return DiffScale(
                    y=contents[draft.y],
                    minuend=contents[draft.minuend],
                    subtrahend=contents[draft.subtrahend],
                    divisor=draft.divisor,
                    tag=draft.tag,
                )
            if isinstance(draft, _DraftSwap):
                return Swap(
                    vault=vault,
                    slot=vault.names[draft.field],
                    alt_store=contents,
                    alt_index=draft.alt_sid,
                    tag=draft.tag,
                )
            if isinstance(draft, _DraftMask):
                return CadenceMask(
                    period=draft.period,
                    phase=draft.phase,
                    ops=tuple(materialize_one(op) for op in draft.ops),
                    tag=draft.tag,
                )
            assert isinstance(draft, _DraftMarker)
            return SegmentMarker(kind=draft.kind, tag=draft.tag)

        def materialize_phase(phase: int, drafts: tuple[_Draft, ...]) -> tuple[Any, ...]:
            ops: list[Any] = []
            for draft in drafts:
                if isinstance(draft, _DraftMask) and phase % draft.period == draft.phase:
                    # §8.2: cadence masks resolve into the per-signature op lists —
                    # the guard is statically true for every step this variant
                    # serves (compiler emits masks in firing phases only), so the
                    # masked ops inline flat and the hot path never re-evaluates it.
                    ops.extend(materialize_one(op) for op in draft.ops)
                else:
                    ops.append(materialize_one(draft))
            return tuple(ops)

        variants = tuple(
            materialize_phase(phase, drafts) for phase, drafts in enumerate(compiler.phases)
        )
        return _Bound(
            vault=vault, variants=variants, epoch=vault.epoch, schema_hash=vault.schema_hash
        )

    # -- the T1 step (hot path) --------------------------------------------------------------

    def run_step(
        self,
        vault: StateVault,
        step_index: int,
        *,
        on_segment: Any = None,
    ) -> None:
        """Execute one step's pre-bound op list (frozen interface, SPEC S05).

        ``step_index`` must advance sequentially from 0 (modulo the signature
        period): the ping-pong swap state of the vault is phase-dependent.
        Materializes against ``vault`` on first use.

        ``on_segment`` (S14, additive keyword with default) is the host-step
        seam: a callback invoked with every
        :class:`~icon_sc.core.plan.ops.SegmentMarker` the interpreter reaches
        (see :mod:`icon_sc.core.plan.interpreter`); monitors and time
        advancement live there, outside the plan.

        Raises:
            StalePlanError: After any out-of-band façade mutation (materialization
                against ``vault`` detects a changed epoch).
        """
        bound = self._bound
        if bound is None or bound.vault is not vault:
            bound = self._materialize(vault)
            self._bound = bound
            self._cursor = step_index % len(bound.variants)
        if vault.epoch != bound.epoch:
            raise StalePlanError(
                "the vault was mutated through its façade after the plan was bound; "
                "re-bind (negotiation) is required."
            )
        if vault.schema_hash != bound.schema_hash:
            raise StalePlanError(
                "the vault schema changed after the plan was bound; re-bind is required."
            )
        variants = bound.variants
        slot = step_index % len(variants)
        if slot != self._cursor:
            raise StalePlanError(
                f"run_step called with step_index {step_index} (signature {slot}) but the "
                f"vault's swap state expects signature {self._cursor}; step_index must "
                f"advance sequentially."
            )
        self._cursor = slot + 1 if slot + 1 < len(variants) else 0
        run_ops(variants[slot], step_index, on_segment)
