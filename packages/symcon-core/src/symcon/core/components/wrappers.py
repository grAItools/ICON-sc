"""Control-flow wrappers: CallingFrequency, Subcycle, ScalingWrapper (SPEC S03).

Pure control flow around the §4.1 kinds — at T0 they are ordinary callables
honoring the component ABI (``__call__(state, timestep, *, out=None)``, property
dicts delegated to the wrapped component); at T1+ they dissolve into the
execution plan (§8.2: cadence masks, unrolled subcycles, folded constants).

Semantics donors (REFERENCES.lock): sympl ``UpdateFrequencyWrapper`` (firing
rule + cached output) for :class:`CallingFrequency`; tasmania's per-section
``substeps`` for :class:`Subcycle`; sympl ``ScalingWrapper`` verbatim in spirit.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import xarray as xr

if TYPE_CHECKING:
    from symcon.core.plan.bind import PlanBuilder

from symcon.core.components.base import Component, DataArrayDict, Stepper
from symcon.core.contracts.properties import PropertySpec
from symcon.core.typing import Location

__all__ = ["CallingFrequency", "ComponentWrapper", "ScalingWrapper", "Subcycle"]

_MICROSECOND = timedelta(microseconds=1)

#: restart_state key of the CallingFrequency phase.
_PHASE_KEY = "calling_frequency/last_update_time"
_ARITY_KEY = "calling_frequency/cache_is_tuple"
_PARTS_KEY = "calling_frequency/cache_parts"
_CACHE_PREFIX = "calling_frequency/cache"
_INNER_PREFIX = "component"


def _scalar_dataarray(value: Any) -> xr.DataArray:
    """A 0-d DataArray carrying ``value`` exactly in its attrs.

    The value rides in ``attrs["value"]`` rather than the array payload: xarray
    coerces object arrays of stdlib datetimes to ``datetime64[ns]``, which would
    break the bit-exact phase round trip (and cftime objects would round-trip
    differently from stdlib ones). Attrs survive ``copy`` untouched.
    """
    return xr.DataArray(np.zeros(()), attrs={"value": value})


def _scalar_value(array: xr.DataArray) -> Any:
    return array.attrs["value"]


class ComponentWrapper:
    """Shared delegation base of the control-flow wrappers.

    Property dicts, names and every other attribute delegate to the wrapped
    component via ``__getattr__``. Wrappers accept ``Component | ComponentWrapper``
    so they compose (``CallingFrequency(Subcycle(...), ...)``) without casts.
    """

    name: str

    def __init__(self, component: Component | ComponentWrapper) -> None:
        self._component = component
        self.name = f"{type(self).__name__}({component.name})"

    @property
    def component(self) -> Component | ComponentWrapper:
        """The wrapped component."""
        return self._component

    def __getattr__(self, item: str) -> Any:
        return getattr(self._component, item)

    def visit(self, plan_builder: PlanBuilder) -> None:
        """Refuse plan compilation for unknown wrappers (S05).

        Defined on the base so ``__getattr__`` can never silently delegate the
        walk to the wrapped component (which would dissolve the wrapper's
        semantics); the three known wrappers override with their real hooks.
        """
        from symcon.core.plan.guards import PlanCompileError

        del plan_builder
        raise PlanCompileError(
            f"{type(self).__name__} implements no plan-compilation hook; "
            f"the S05 compiler cannot dissolve it."
        )

    def _call_component(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None,
        out: Mapping[str, xr.DataArray] | None,
    ) -> Any:
        # The four kinds share the ABI but differ in return shape; call untyped.
        call = cast("Callable[..., Any]", self._component)
        return call(state, timestep, out=out)


class CallingFrequency(ComponentWrapper):
    """Reduced calling frequency with piecewise-constant cached output (§4.2 LFC).

    ``CallingFrequency(component, dt)`` calls the wrapped component only when
    ``state["time"]`` has advanced at least one *effective period* past the last
    update, returning the cached output verbatim in between (ICON's slow-physics
    choice: lazy evaluation stretched over N steps).

    **Rounding-to-multiple rule:** when a call supplies the loop ``timestep``,
    the effective period is the nearest positive integer multiple of it (exact
    integer-microsecond arithmetic, ties round up); without a timestep the raw
    per-process ``dt`` applies. **Phase** (the last update time) and the cached
    output are component-private carry: surfaced by :meth:`restart_state` and
    declared in :meth:`functional_state` (S10 relies on this being carry).
    """

    def __init__(self, component: Component | ComponentWrapper, dt: timedelta) -> None:
        super().__init__(component)
        if dt <= timedelta(0):
            raise ValueError(f"{self.name}: dt must be positive, got {dt!r}.")
        self._dt = dt
        self._last_update_time: Any = None
        self._cached: tuple[DataArrayDict, ...] | None = None
        self._cache_is_tuple = True

    def period_for(self, timestep: timedelta | None) -> timedelta:
        """Effective period under the rounding-to-multiple rule (SPEC S03)."""
        if timestep is None:
            return self._dt
        if timestep <= timedelta(0):
            raise ValueError(f"{self.name}: timestep must be positive, got {timestep!r}.")
        step_us = timestep // _MICROSECOND
        period_us = self._dt // _MICROSECOND
        multiples = max(1, (2 * period_us + step_us) // (2 * step_us))
        return timedelta(microseconds=multiples * step_us)

    @property
    def update_period(self) -> timedelta:
        """The raw per-process ``dt`` (pre rounding-to-multiple; S05 accessor)."""
        return self._dt

    @property
    def last_update_time(self) -> Any:
        """The firing phase (``None`` until the first call; S05 bind accessor)."""
        return self._last_update_time

    def visit(self, plan_builder: PlanBuilder) -> None:
        """S05 plan-compiler hook: dissolve into a cadence mask (§8.2)."""
        plan_builder.visit_calling_frequency(self)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None = None,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> Any:
        time = state["time"]
        period = self.period_for(timestep)
        if self._last_update_time is None or time >= self._last_update_time + period:
            result = self._call_component(state, timestep, out)
            parts = result if isinstance(result, tuple) else (result,)
            self._cache_is_tuple = isinstance(result, tuple)
            # Snapshot: the cache must stay piecewise-constant even if the caller
            # mutates the returned (or out=) DataArrays afterwards.
            self._cached = tuple(
                {name: array.copy(deep=True) for name, array in part.items()} for part in parts
            )
            self._last_update_time = time
            return result
        return self._replay(out)

    def _replay(self, out: Mapping[str, xr.DataArray] | None) -> Any:
        assert self._cached is not None
        filled: list[DataArrayDict] = []
        for part in self._cached:
            result: DataArrayDict = {}
            for name, array in part.items():
                if out is not None and name in out:
                    out[name].data[...] = array.data
                    result[name] = out[name]
                else:
                    result[name] = array.copy(deep=True)
            filled.append(result)
        if self._cache_is_tuple:
            return tuple(filled)
        return filled[0]

    # -- carry: phase + cache (PLAN item 3) ---------------------------------------

    def restart_state(self) -> dict[str, xr.DataArray]:
        result = {
            f"{_INNER_PREFIX}/{key}": value
            for key, value in self._component.restart_state().items()
        }
        if self._last_update_time is not None:
            assert self._cached is not None
            result[_PHASE_KEY] = _scalar_dataarray(self._last_update_time)
            result[_ARITY_KEY] = _scalar_dataarray(self._cache_is_tuple)
            # The part count is persisted explicitly: a part may legitimately be an
            # empty dict (e.g. a component with no diagnostics), which would leave
            # no per-field key and silently change the cache arity on restore.
            result[_PARTS_KEY] = _scalar_dataarray(len(self._cached))
            for index, part in enumerate(self._cached):
                for name, array in part.items():
                    result[f"{_CACHE_PREFIX}/{index}/{name}"] = array.copy(deep=True)
        return result

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        inner: dict[str, xr.DataArray] = {}
        parts: dict[int, DataArrayDict] = {}
        phase: xr.DataArray | None = None
        arity: xr.DataArray | None = None
        n_parts: xr.DataArray | None = None
        for key, value in restart.items():
            if key.startswith(f"{_INNER_PREFIX}/"):
                inner[key[len(_INNER_PREFIX) + 1 :]] = value
            elif key == _PHASE_KEY:
                phase = value
            elif key == _ARITY_KEY:
                arity = value
            elif key == _PARTS_KEY:
                n_parts = value
            elif key.startswith(f"{_CACHE_PREFIX}/"):
                index_str, _, name = key[len(_CACHE_PREFIX) + 1 :].partition("/")
                parts.setdefault(int(index_str), {})[name] = value.copy(deep=True)
            else:
                raise ValueError(f"{self.name}: unknown restart key {key!r}.")
        self._component.load_restart_state(inner)
        if phase is None:
            if parts or arity is not None or n_parts is not None:
                raise ValueError(f"{self.name}: cache present but phase missing.")
            self._last_update_time = None
            self._cached = None
            return
        if n_parts is None:
            raise ValueError(f"{self.name}: restart cache is missing {_PARTS_KEY!r}.")
        count = int(_scalar_value(n_parts))
        if parts and max(parts) >= count:
            raise ValueError(
                f"{self.name}: restart cache has part index {max(parts)} but "
                f"declares only {count} part(s)."
            )
        self._last_update_time = _scalar_value(phase)
        self._cache_is_tuple = bool(_scalar_value(arity)) if arity is not None else True
        # Reconstruct by declared count: empty parts (components with an empty
        # output dict) leave no per-field keys but must keep their slot.
        self._cached = tuple(parts.get(index, {}) for index in range(count))

    def functional_state(self) -> Mapping[str, PropertySpec]:
        schema: dict[str, PropertySpec] = {
            f"{_INNER_PREFIX}/{key}": spec
            for key, spec in self._component.functional_state().items()
        }
        schema[_PHASE_KEY] = PropertySpec(
            name=_PHASE_KEY, dims=(), units="1", location=Location.SCALAR
        )
        for index, dict_name in enumerate(self._component.output_dict_names):
            for name, spec in self._component.parsed_properties.get(dict_name, {}).items():
                key = f"{_CACHE_PREFIX}/{index}/{name}"
                schema[key] = dataclasses.replace(spec, name=key)
        return schema


class Subcycle(ComponentWrapper):
    """Run a :class:`Stepper` ``n`` times over ``timestep / n`` (§4.2 combinator).

    Exactly one of ``n`` (static) and ``ratio_provider`` (adaptive: called once
    per outer step with the current state, must return an integer >= 1) is given.
    Intermediate sub-states chain through the stepper (tasmania's substep
    semantics); ``out=`` is forwarded to the **final** substep only, so earlier
    substeps never alias the caller's buffers. ``state["time"]`` is not advanced
    between substeps (deliberately dumb at T0; the plan compiler owns cadence).

    .. note:: Because time does not advance between substeps, a time-triggered
       wrapper inside a subcycle — ``Subcycle(CallingFrequency(...), ...)`` —
       degenerates to at most one effective fire per outer step: every substep
       after the first sees an unchanged ``state["time"]`` and replays the cache.
    """

    def __init__(
        self,
        stepper: Stepper | ComponentWrapper,
        n: int | None = None,
        ratio_provider: Callable[[Mapping[str, Any]], int] | None = None,
    ) -> None:
        super().__init__(stepper)
        if (n is None) == (ratio_provider is None):
            raise ValueError(f"{self.name}: give exactly one of n and ratio_provider.")
        if n is not None and n < 1:
            raise ValueError(f"{self.name}: n must be >= 1, got {n}.")
        self._n = n
        self._ratio_provider = ratio_provider

    @property
    def n(self) -> int | None:
        """The static substep count (``None`` under a ratio_provider; S05 accessor)."""
        return self._n

    @property
    def ratio_provider(self) -> Callable[[Mapping[str, Any]], int] | None:
        """The adaptive substep-count provider (S05 accessor)."""
        return self._ratio_provider

    def visit(self, plan_builder: PlanBuilder) -> None:
        """S05 plan-compiler hook: unroll with bound dt (§8.2)."""
        plan_builder.visit_subcycle(self)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        if self._n is not None:
            ratio = self._n
        else:
            assert self._ratio_provider is not None
            ratio = int(self._ratio_provider(state))
            if ratio < 1:
                raise ValueError(f"{self.name}: ratio_provider returned {ratio}; need >= 1.")
        sub_timestep = timestep / ratio
        current: dict[str, Any] = dict(state)
        diagnostics: DataArrayDict = {}
        new_state: DataArrayDict = {}
        for index in range(ratio):
            sub_out = out if index == ratio - 1 else None
            diagnostics, new_state = self._call_component(current, sub_timestep, sub_out)
            current.update(new_state)
        return diagnostics, new_state


class ScalingWrapper(ComponentWrapper):
    """Scale selected inputs/outputs of a wrapped component (sympl semantics).

    Scale-factor dict keys are validated against the wrapped component's property
    dicts at construction. Inputs are scaled into attr-preserving copies before
    the call (allocating — T0/debug affordance); outputs/tendencies/diagnostics
    are scaled **in place** after the call, so ``out=`` pointer identity is
    preserved.
    """

    _FACTOR_DICTS: Mapping[str, str] = {
        "input_scale_factors": "input_properties",
        "tendency_scale_factors": "tendency_properties",
        "diagnostic_scale_factors": "diagnostic_properties",
        "output_scale_factors": "output_properties",
    }

    def __init__(
        self,
        component: Component | ComponentWrapper,
        *,
        input_scale_factors: Mapping[str, float] | None = None,
        tendency_scale_factors: Mapping[str, float] | None = None,
        diagnostic_scale_factors: Mapping[str, float] | None = None,
        output_scale_factors: Mapping[str, float] | None = None,
    ) -> None:
        super().__init__(component)
        given: dict[str, Mapping[str, float]] = {
            "input_scale_factors": input_scale_factors or {},
            "tendency_scale_factors": tendency_scale_factors or {},
            "diagnostic_scale_factors": diagnostic_scale_factors or {},
            "output_scale_factors": output_scale_factors or {},
        }
        for factor_name, factors in given.items():
            dict_name = self._FACTOR_DICTS[factor_name]
            declared = component.parsed_properties.get(dict_name, {})
            unknown = set(factors) - set(declared)
            if unknown:
                raise ValueError(
                    f"{self.name}: {factor_name} names {sorted(unknown)} are not in "
                    f"{component.name}.{dict_name} (declared: {sorted(declared)})."
                )
        self._factors = given

    @property
    def scale_factors(self) -> Mapping[str, Mapping[str, float]]:
        """The validated scale-factor dicts, keyed by factor-dict name (S05 accessor)."""
        return self._factors

    def visit(self, plan_builder: PlanBuilder) -> None:
        """S05 plan-compiler hook: fold into bound constants (§8.2)."""
        plan_builder.visit_scaling_wrapper(self)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None = None,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> Any:
        scaled_state: dict[str, Any] = dict(state)
        for name, factor in self._factors["input_scale_factors"].items():
            array = state[name]
            scaled = array.copy(data=array.data * float(factor))
            scaled.attrs = dict(array.attrs)
            scaled_state[name] = scaled

        result = self._call_component(scaled_state, timestep, out)

        parts = result if isinstance(result, tuple) else (result,)
        factor_of_dict = {
            dict_name: self._factors[factor_name]
            for factor_name, dict_name in self._FACTOR_DICTS.items()
        }
        for dict_name, part in zip(self._component.output_dict_names, parts, strict=True):
            for name, factor in factor_of_dict[dict_name].items():
                if name in part:
                    part[name].data[...] *= float(factor)
        return result
