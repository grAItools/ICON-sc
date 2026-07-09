"""``ConcurrentCoupling`` — tasmania's heterogeneous composite (architecture §4.2).

``ConcurrentCoupling(comps)`` bundles :class:`~symcon.core.components.base.TendencyComponent`,
:class:`~symcon.core.components.base.ImplicitTendencyComponent` and
:class:`~symcon.core.components.base.DiagnosticComponent` instances (wrappers and
nested couplings included) into one tendency provider: tendency contributions are
**summed**, diagnostics are **unioned in declared order** and — tasmania's ``serial``
execution policy, the only one ported — each member sees the diagnostics computed by
the members before it. It is the building block of full coupling (FC: evaluate at
every integrator stage) and, held constant by the dycore's slow port or by
``CallingFrequency``, of lazy full coupling (LFC; thesis eq. 2.9).

The coupling is itself a component: it exposes the tendency-kind call signature
``(state, timestep, *, out=None) -> (tendencies, diagnostics)``, parsed property
dicts, and the restart/functional-state protocol (delegated to its members), so
couplings nest and wrap like any §4.1 component.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from typing import Any, ClassVar, cast

import xarray as xr

from symcon.core.components.base import DataArrayDict
from symcon.core.contracts.properties import PropertyDictError, PropertySpec

__all__ = ["ConcurrentCoupling"]

#: ``output_dict_names`` of the diagnostic kind (used for duck kind detection).
_DIAGNOSTIC_DICTS = ("diagnostic_properties",)
#: Member restart keys are namespaced per position (nested couplings re-prefix).
_MEMBER_PREFIX = "component"


def output_dict_names_of(component: object) -> tuple[str, ...]:
    """The component-kind fingerprint (``output_dict_names``), via delegation."""
    names = getattr(component, "output_dict_names", None)
    if names is None:
        raise TypeError(
            f"{component!r} exposes no output_dict_names; it is not a symcon component."
        )
    return tuple(names)


def is_diagnostic_kind(component: object) -> bool:
    """True for DiagnosticComponent-shaped objects (wrappers delegate the fingerprint)."""
    return output_dict_names_of(component) == _DIAGNOSTIC_DICTS


def is_tendency_kind(component: object) -> bool:
    """True for (Implicit)TendencyComponent-shaped objects, nested couplings included."""
    names = output_dict_names_of(component)
    return bool(names) and names[0] == "tendency_properties"


def parsed_properties_of(component: object) -> Mapping[str, Mapping[str, PropertySpec]]:
    """The parsed property dicts of a component-shaped object."""
    parsed = getattr(component, "parsed_properties", None)
    if parsed is None:
        raise TypeError(f"{component!r} exposes no parsed_properties.")
    return cast("Mapping[str, Mapping[str, PropertySpec]]", parsed)


def name_of(component: object) -> str:
    """Best-effort display name of a component-shaped object."""
    return str(getattr(component, "name", type(component).__name__))


def _compatible(a: PropertySpec, b: PropertySpec) -> bool:
    return a.dims == b.dims and a.units == b.units


class ConcurrentCoupling:
    """Sum tendencies, union diagnostics, chain serially (frozen interface, SPEC S04)."""

    #: Tendency-kind fingerprint: couplings nest inside couplings and steppers.
    output_dict_names: ClassVar[tuple[str, ...]] = (
        "tendency_properties",
        "diagnostic_properties",
    )

    def __init__(self, components: Sequence[Any], *, name: str | None = None) -> None:
        members = tuple(components)
        if not members:
            raise ValueError("ConcurrentCoupling: at least one component is required.")
        for member in members:
            if not (is_diagnostic_kind(member) or is_tendency_kind(member)):
                raise TypeError(
                    f"ConcurrentCoupling: {name_of(member)!r} is neither a tendency-kind "
                    f"nor a diagnostic-kind component (output_dict_names="
                    f"{output_dict_names_of(member)!r}); Steppers belong in federations, "
                    f"not couplings."
                )
        self._components = members
        self.name = (
            name
            if name is not None
            else f"ConcurrentCoupling({', '.join(name_of(m) for m in members)})"
        )
        #: Whether any member needs a timestep (ImplicitTendencyComponent semantics).
        self.timestep_required = any(
            bool(getattr(member, "timestep_required", False)) for member in members
        )
        self._parsed = self._merge_properties()

    # -- negotiation surface -------------------------------------------------------

    def _merge_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        inputs: dict[str, PropertySpec] = {}
        tendencies: dict[str, PropertySpec] = {}
        diagnostics: dict[str, PropertySpec] = {}
        produced: set[str] = set()

        def merge(
            target: dict[str, PropertySpec],
            incoming: Mapping[str, PropertySpec],
            member: object,
            role: str,
        ) -> None:
            for field, spec in incoming.items():
                held = target.get(field)
                if held is None:
                    target[field] = spec
                elif not _compatible(held, spec):
                    raise PropertyDictError(
                        f"{self.name}: {role} {field!r} declared as "
                        f"(dims={held.dims!r}, units={held.units!r}) upstream but "
                        f"(dims={spec.dims!r}, units={spec.units!r}) by {name_of(member)!r}."
                    )

        for member in self._components:
            parsed = parsed_properties_of(member)
            fresh_inputs = {
                field: spec
                for field, spec in parsed.get("input_properties", {}).items()
                if field not in produced  # provided by an earlier member's diagnostics
            }
            merge(inputs, fresh_inputs, member, "input")
            merge(tendencies, parsed.get("tendency_properties", {}), member, "tendency")
            member_diags = parsed.get("diagnostic_properties", {})
            merge(diagnostics, member_diags, member, "diagnostic")
            produced.update(member_diags)
        return {
            "input_properties": inputs,
            "tendency_properties": tendencies,
            "diagnostic_properties": diagnostics,
        }

    @property
    def components(self) -> tuple[Any, ...]:
        """The wrapped components, in declared (serial) order."""
        return self._components

    @property
    def parsed_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        """Merged parsed property dicts (inputs net of internally chained diagnostics)."""
        return self._parsed

    def __str__(self) -> str:
        lines = [f"instance of {type(self).__name__}"]
        lines.extend(f"    {name_of(member)}" for member in self._components)
        return "\n".join(lines)

    # -- the call path -------------------------------------------------------------

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta | None = None,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Return ``(tendencies, diagnostics)`` of the bundle at ``state``.

        Serial policy (tasmania): members run in declared order and each sees the
        diagnostics of its predecessors; tendency contributions for the same field
        are summed. ``out`` optionally provides output DataArrays (flat namespace
        across tendencies and diagnostics).
        """
        if self.timestep_required and timestep is None:
            raise TypeError(f"{self.name}: a member requires a timestep (implicit tendencies).")
        if out is not None:
            known = set(self._parsed["tendency_properties"]) | set(
                self._parsed["diagnostic_properties"]
            )
            unknown = set(out) - known
            if unknown:
                raise ValueError(
                    f"{self.name}: out= names {sorted(unknown)} are not outputs of "
                    f"this coupling (outputs: {sorted(known)})."
                )

        working: dict[str, Any] = dict(state)
        tendencies: DataArrayDict = {}
        diagnostics: DataArrayDict = {}
        for member in self._components:
            call = cast("Callable[..., Any]", member)
            if is_diagnostic_kind(member):
                member_diags: DataArrayDict = call(working, timestep)
                member_tends: DataArrayDict = {}
            else:
                member_tends, member_diags = call(working, timestep)
            for field, array in member_diags.items():
                if out is not None and field in out:
                    out[field].data[...] = array.data
                    array = out[field]
                diagnostics[field] = array
                working[field] = array
            for field, array in member_tends.items():
                held = tendencies.get(field)
                if held is not None:
                    held.data[...] += array.data
                elif out is not None and field in out:
                    out[field].data[...] = array.data
                    tendencies[field] = out[field]
                else:
                    # First contribution: adopt the member's freshly allocated
                    # output as the accumulator (components allocate per call).
                    tendencies[field] = array
        return tendencies, diagnostics

    # -- restart / functional carry (delegated, §4.5/§8.5) --------------------------

    def restart_state(self) -> dict[str, xr.DataArray]:
        """Union of the members' private state, namespaced by member position."""
        result: dict[str, xr.DataArray] = {}
        for index, member in enumerate(self._components):
            for key, value in member.restart_state().items():
                result[f"{_MEMBER_PREFIX}{index}/{key}"] = value
        return result

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        """Route restart entries back to the owning members."""
        per_member: dict[int, dict[str, xr.DataArray]] = {
            index: {} for index in range(len(self._components))
        }
        for key, value in restart.items():
            prefix, _, inner = key.partition("/")
            if not (prefix.startswith(_MEMBER_PREFIX) and inner):
                raise ValueError(f"{self.name}: unknown restart key {key!r}.")
            try:
                index = int(prefix[len(_MEMBER_PREFIX) :])
                bucket = per_member[index]
            except (KeyError, ValueError):
                raise ValueError(f"{self.name}: unknown restart key {key!r}.") from None
            bucket[inner] = value
        for index, member in enumerate(self._components):
            member.load_restart_state(per_member[index])

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """Union of the members' carry schemas, namespaced by member position."""
        schema: dict[str, PropertySpec] = {}
        for index, member in enumerate(self._components):
            for key, spec in member.functional_state().items():
                name = f"{_MEMBER_PREFIX}{index}/{key}"
                schema[name] = dataclasses.replace(spec, name=name)
        return schema
