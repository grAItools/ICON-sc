"""Component taxonomy with the Ubbiali ABI (architecture §4.1-§4.2, SPEC S03).

The five sympl kinds — :class:`DiagnosticComponent`, :class:`TendencyComponent`,
:class:`ImplicitTendencyComponent`, :class:`Stepper`, :class:`Monitor` — with the
object-oriented ABI adopted from stubbiali/sympl ``oop`` (see REFERENCES.lock):

- ``__call__(state, timestep, *, out=None)`` with caller-provided output
  DataArrays (``out`` is one flat ``name -> DataArray`` mapping across the
  component's output property dicts);
- ``array_call(inputs, outputs, timestep)`` receiving both input **and output**
  raw buffers and writing outputs in place;
- ``allocate_output(name, schema, ctx)`` invoked exactly once per output field
  the caller did not provide;
- the restart protocol (``restart_state``/``load_restart_state``) and the
  explicit-carry schema ``functional_state()`` (§4.5, §8.5).

All checking routes through S02's contracts machinery: ``__init_subclass__``
runs the :class:`~symcon.core.contracts.checkers.StaticChecker` at class
creation; ``__call__`` runs the
:class:`~symcon.core.contracts.checkers.DynamicChecker` + ``Ingress``/
``EgressPlan`` per call — T0's fully dynamic reference semantics — with one
negotiation cached per (instance, state-schema) so an unchanged schema does not
renegotiate (PLAN item 2; *not* the S05 plan compiler: dicts and DataArrays stay
on the path).
"""

from __future__ import annotations

import abc
import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Any, ClassVar, cast

import numpy as np
import xarray as xr

if TYPE_CHECKING:
    from symcon.core.plan.bind import PlanBuilder

from symcon.core.context import ComputeContext
from symcon.core.contracts.checkers import (
    PROPERTY_DICT_NAMES,
    DynamicChecker,
    FieldSchema,
    StateSchema,
    StaticChecker,
)
from symcon.core.contracts.conversion import apply_conversion_plan
from symcon.core.contracts.operators import ConversionPlan, EgressPlan, IngressPlan
from symcon.core.contracts.properties import PropertyDictError, PropertySpec
from symcon.core.state.dataarray import make_dataarray
from symcon.core.typing import FieldBuffer

__all__ = [
    "Component",
    "DiagnosticComponent",
    "ImplicitTendencyComponent",
    "Monitor",
    "OutputSchema",
    "Stepper",
    "TendencyComponent",
]

#: One state snapshot: canonical names -> boundary DataArrays (+ the ``time`` key).
DataArrayDict = dict[str, xr.DataArray]

_SchemaKey = tuple[tuple[str, FieldSchema], ...]


def _schema_key(schema: StateSchema) -> _SchemaKey:
    return tuple(sorted(schema.fields.items()))


def _dim_sizes(state: Mapping[str, Any], *, component: str) -> dict[str, int]:
    """Dimension-name -> length map of a state (consistency-checked)."""
    sizes: dict[str, int] = {}
    for name, value in state.items():
        if not isinstance(value, xr.DataArray):
            continue
        for dim, size in value.sizes.items():
            key = str(dim)
            if sizes.setdefault(key, int(size)) != int(size):
                raise ValueError(
                    f"component {component!r}: dim {key!r} has inconsistent lengths "
                    f"in the state ({sizes[key]} vs {int(size)}, found at {name!r})."
                )
    return sizes


@dataclasses.dataclass(frozen=True, slots=True)
class OutputSchema:
    """What :meth:`Component.allocate_output` needs to allocate one output field."""

    spec: PropertySpec
    shape: tuple[int, ...]
    dtype: np.dtype[Any]


class Component(abc.ABC):
    """Shared machinery of the four callable component kinds (frozen ABI, SPEC S03).

    Subclasses declare property dicts as **class attributes**; they are validated
    by the :class:`~symcon.core.contracts.checkers.StaticChecker` at class
    creation (``__init_subclass__``), so a component declaring, e.g.,
    non-canonical units never constructs. Concrete subclasses implement
    :meth:`array_call` only — the base owns negotiation, allocation and egress.
    """

    input_properties: ClassVar[Mapping[str, Any]] = {}
    tendency_properties: ClassVar[Mapping[str, Any]] = {}
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {}
    output_properties: ClassVar[Mapping[str, Any]] = {}

    #: Which property dicts are *outputs* of this kind, in egress order.
    output_dict_names: ClassVar[tuple[str, ...]] = ()
    #: Whether ``__call__`` requires a timestep (Stepper/ImplicitTendencyComponent).
    timestep_required: ClassVar[bool] = False

    _parsed_properties: ClassVar[Mapping[str, Mapping[str, PropertySpec]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._parsed_properties = StaticChecker(cls).specs
        role_dicts = ("input_properties", *cls.output_dict_names)
        for dict_name in PROPERTY_DICT_NAMES:
            if dict_name not in role_dicts and cls._parsed_properties.get(dict_name):
                raise PropertyDictError(
                    f"{cls.__name__}: {dict_name} is not part of the "
                    f"{cls.__name__} kind (allowed: {role_dicts!r})."
                )
        seen: dict[str, str] = {}
        for dict_name in cls.output_dict_names:
            for name in cls._parsed_properties.get(dict_name, {}):
                if name in seen:
                    raise PropertyDictError(
                        f"{cls.__name__}: field {name!r} appears in both "
                        f"{seen[name]} and {dict_name}; the flat out= namespace "
                        f"cannot disambiguate them."
                    )
                seen[name] = dict_name

    def __init__(self, *, ctx: ComputeContext | None = None, name: str | None = None) -> None:
        self._ctx = ctx if ctx is not None else ComputeContext(backend="embedded")
        self.name = name if name is not None else type(self).__name__
        # One negotiation per (instance, schema): T0 amortization (PLAN item 2).
        self._ingress_cache: dict[_SchemaKey, tuple[ConversionPlan, IngressPlan]] = {}
        self._egress_cache: dict[tuple[str, _SchemaKey], EgressPlan] = {}

    def __str__(self) -> str:
        lines = [f"instance of {type(self).__name__}({type(self).__mro__[1].__name__})"]
        for dict_name in ("input_properties", *self.output_dict_names):
            names = ", ".join(self._parsed_properties.get(dict_name, {}))
            lines.append(f"    {dict_name.removesuffix('_properties')}s: {names}")
        return "\n".join(lines)

    @property
    def ctx(self) -> ComputeContext:
        """The compute context this component allocates and checks against."""
        return self._ctx

    @property
    def parsed_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        """Parsed property dicts (per-class, produced by the StaticChecker)."""
        return self._parsed_properties

    # -- the ABI hooks -----------------------------------------------------------

    @abc.abstractmethod
    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        """Compute on raw buffers, writing every output **in place** (frozen ABI).

        ``inputs``/``outputs`` are keyed by contract field names (aliases already
        resolved); ``outputs`` is the flat union of the kind's output dicts.
        """

    def allocate_output(self, name: str, schema: OutputSchema, ctx: ComputeContext) -> FieldBuffer:
        """Allocate one output buffer (frozen ABI); called only for fields not in ``out=``.

        Default: an uninitialized buffer from the context allocator. Override for
        framework-side allocation (gt4py fields, pooled buffers, …).
        """
        del name
        return ctx.require_allocator.empty(schema.shape, schema.dtype)

    # -- restart protocol / explicit carry (§4.5, §8.5) ---------------------------

    def restart_state(self) -> dict[str, xr.DataArray]:
        """Component-private persistent fields to serialize (default: stateless)."""
        return {}

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        """Restore component-private fields from :meth:`restart_state` output."""
        if restart:
            raise ValueError(
                f"component {self.name!r} holds no private state; got {sorted(restart)}."
            )

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """Schema of the private carry surfaced to the F-tier (§8.5; default empty)."""
        return {}

    # -- plan-compiler walk (S05, PLAN item 3) -------------------------------------

    def visit(self, plan_builder: PlanBuilder) -> None:
        """Double-dispatch hook of the S05 plan compiler (and later tree walks)."""
        plan_builder.visit_component(self)

    # -- T0 negotiation-per-call -------------------------------------------------

    def _ingress(
        self, state: Mapping[str, Any]
    ) -> tuple[dict[str, FieldBuffer], Mapping[str, Any]]:
        """DynamicChecker + IngressPlan for the input dict, cached per schema.

        Returns the raw input buffers (keyed by contract names) and the *working*
        state (the input state, or its converted copy under non-strict mode).
        """
        spec = self._parsed_properties.get("input_properties", {})
        schema = StateSchema.from_state(state)
        key = _schema_key(schema)
        cached = self._ingress_cache.get(key)
        if cached is None:
            checker = DynamicChecker(
                spec,
                schema,
                component=self.name,
                strict=self._ctx.strict,
                device=self._ctx.device,
            )
            conversion = checker.plan
            working: Mapping[str, Any] = (
                apply_conversion_plan(conversion, state, component=self.name)
                if conversion
                else state
            )
            plan = IngressPlan.build(spec, StateSchema.from_state(working), component=self.name)
            self._ingress_cache[key] = (conversion, plan)
        else:
            conversion, plan = cached
            working = (
                apply_conversion_plan(conversion, state, component=self.name)
                if conversion
                else state
            )
        buffers = plan.apply(working)
        return dict(zip(plan.fields, buffers, strict=True)), working

    def _resolve_outputs(
        self,
        dict_name: str,
        state: Mapping[str, Any],
        out: Mapping[str, xr.DataArray] | None,
    ) -> tuple[dict[str, FieldBuffer], DataArrayDict]:
        """Extract caller-provided output buffers; allocate the missing ones."""
        specs = self._parsed_properties.get(dict_name, {})
        buffers: dict[str, FieldBuffer] = {}
        wrapped: DataArrayDict = {}

        provided = {name: out[name] for name in specs if out is not None and name in out}
        if provided:
            # Caller-provided outputs are validated strictly always: array_call
            # writes into them raw, so no conversion could reconcile a mismatch.
            sub_spec = {name: specs[name] for name in provided}
            out_schema = StateSchema.from_state(provided)
            egress_key = (dict_name, _schema_key(out_schema))
            plan = self._egress_cache.get(egress_key)
            if plan is None:
                # IngressPlan.build is annotated on the parent; the subclass build
                # constructs an EgressPlan (classmethod on cls).
                plan = cast(
                    EgressPlan,
                    EgressPlan.build(
                        sub_spec, out_schema, component=self.name, device=self._ctx.device
                    ),
                )
                self._egress_cache[egress_key] = plan
            # Shape check per call (schemas are shape-free, so the cached plan can't
            # carry it): a wrong-shaped buffer with the right dim names would silently
            # broadcast inside array_call and corrupt the reference tier.
            sizes = _dim_sizes(state, component=self.name)
            for name, array in provided.items():
                for dim, length in zip(specs[name].dims, array.shape, strict=False):
                    expected = sizes.get(dim)
                    if expected is not None and length != expected:
                        raise ValueError(
                            f"component {self.name!r}: out[{name!r}] has length "
                            f"{length} along dim {dim!r}, but the state has "
                            f"{expected}; refusing to broadcast into an output "
                            f"buffer."
                        )
            for name, buffer in zip(plan.fields, plan.apply(provided), strict=True):
                buffers[name] = buffer
                wrapped[name] = provided[name]

        missing = [name for name in specs if name not in provided]
        if missing:
            sizes = _dim_sizes(state, component=self.name)
            for name in missing:
                spec = specs[name]
                try:
                    shape = tuple(sizes[dim] for dim in spec.dims)
                except KeyError as exc:
                    raise ValueError(
                        f"component {self.name!r}: cannot infer the length of dim "
                        f"{exc.args[0]!r} for output {name!r} from the state; "
                        f"provide the field via out= or override allocate_output."
                    ) from None
                if spec.dtype is not None:
                    dtype = spec.dtype
                elif name in state and isinstance(state[name], xr.DataArray):
                    dtype = np.dtype(state[name].data.dtype)
                else:
                    dtype = np.dtype(np.float64)
                buffer = self.allocate_output(name, OutputSchema(spec, shape, dtype), self._ctx)
                buffers[name] = buffer
                wrapped[name] = make_dataarray(
                    buffer,
                    name=name,
                    dims=spec.dims,
                    units=spec.units,
                    location=spec.location,
                )
        return buffers, wrapped

    def _run(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None,
        out: Mapping[str, xr.DataArray] | None,
    ) -> dict[str, DataArrayDict]:
        """The full T0 call: checks + ingress + allocate/extract + array_call + egress."""
        if self.timestep_required and timestep is None:
            raise TypeError(
                f"component {self.name!r} ({type(self).__name__} kind) requires a timestep."
            )
        if out is not None:
            known = {
                name
                for dict_name in self.output_dict_names
                for name in self._parsed_properties.get(dict_name, {})
            }
            unknown = set(out) - known
            if unknown:
                raise ValueError(
                    f"component {self.name!r}: out= names {sorted(unknown)} are not "
                    f"outputs of this component (outputs: {sorted(known)})."
                )
        inputs, working = self._ingress(state)
        outputs: dict[str, FieldBuffer] = {}
        wrapped: dict[str, DataArrayDict] = {}
        for dict_name in self.output_dict_names:
            dict_buffers, dict_wrapped = self._resolve_outputs(dict_name, working, out)
            outputs.update(dict_buffers)  # cross-dict collisions rejected at class creation
            wrapped[dict_name] = dict_wrapped
        self.array_call(inputs, outputs, timestep)
        return wrapped


class DiagnosticComponent(Component):
    """Pure function of the state at one time: computes diagnostics (§4.1)."""

    output_dict_names: ClassVar[tuple[str, ...]] = ("diagnostic_properties",)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None = None,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> DataArrayDict:
        """Compute the declared diagnostics from ``state`` (frozen ABI, SPEC S03)."""
        wrapped = self._run(state, timestep, out)
        return wrapped["diagnostic_properties"]


class TendencyComponent(Component):
    """Computes instantaneous tendencies (+ diagnostics) of the state (§4.1)."""

    output_dict_names: ClassVar[tuple[str, ...]] = (
        "tendency_properties",
        "diagnostic_properties",
    )

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None = None,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Return ``(tendencies, diagnostics)`` (frozen ABI, SPEC S03)."""
        wrapped = self._run(state, timestep, out)
        return wrapped["tendency_properties"], wrapped["diagnostic_properties"]


class ImplicitTendencyComponent(Component):
    """A :class:`TendencyComponent` whose tendencies depend on the timestep (§4.1)."""

    output_dict_names: ClassVar[tuple[str, ...]] = (
        "tendency_properties",
        "diagnostic_properties",
    )
    timestep_required: ClassVar[bool] = True

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Return ``(tendencies, diagnostics)`` for the given timestep (frozen ABI)."""
        wrapped = self._run(state, timestep, out)
        return wrapped["tendency_properties"], wrapped["diagnostic_properties"]


class Stepper(Component):
    """Steps the state forward by one timestep with its own numerics (§4.1)."""

    output_dict_names: ClassVar[tuple[str, ...]] = (
        "diagnostic_properties",
        "output_properties",
    )
    timestep_required: ClassVar[bool] = True

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Return ``(diagnostics, new_state)`` (frozen ABI, SPEC S03).

        ``new_state`` holds the declared output fields only (no ``time``; the
        driver owns time advancement).
        """
        wrapped = self._run(state, timestep, out)
        return wrapped["diagnostic_properties"], wrapped["output_properties"]


class Monitor(abc.ABC):
    """Consumes states for output/inspection; never on the component call path."""

    def __init__(self, *, name: str | None = None) -> None:
        self.name = name if name is not None else type(self).__name__

    def __str__(self) -> str:
        return f"instance of {type(self).__name__}(Monitor)"

    @abc.abstractmethod
    def store(self, state: Mapping[str, Any]) -> None:
        """Store the given state (side effect defined by the concrete monitor)."""
