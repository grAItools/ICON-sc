"""The four federations: PS, STS, SUS, SSUS (architecture §4.2, SPEC S04).

Each federation realizes one of the thesis's coupling strategies over a list of
*sections*. A section is either a bare Stepper-shaped component (adjustment-type
processes enter directly; wrappers and dynamical cores qualify by duck kind) or a
``(TendencyComponent, stepper_name)`` pair resolved through the S02 registries of
:mod:`symcon.core.coupling.steppers`.

- :class:`ParallelSplitting` — thesis eq. (2.10): every section integrates
  independently from ψⁿ; the recombination ``ψⁿ⁺¹ = Σₗ ψₗⁿ⁺¹ - L·ψⁿ`` (2.10d) is a
  per-field axpy accumulation (:func:`~symcon.core.coupling.dictops.dict_axpy`
  shape; a fused multi-axpy vault op at T1).
- :class:`SequentialTendencySplitting` — eq. (2.11): the first section (the
  dynamics) is stepped plainly from ψⁿ; every later section is a
  :class:`~symcon.core.coupling.steppers.SequentialTendencyStepper` integrating
  **from the step-initial ψⁿ** with the accumulated provisional state as forcing.
  Diagnostics land on the ψⁿ-level state (visible to later sections), provisional
  outputs accumulate separately (tasmania's two-dict discipline).
- :class:`SequentialUpdateSplitting` — eq. (2.12): each section corrects the state
  left by its predecessor.
- :class:`SSUS` — eq. (2.13a-e): sections traversed in **reverse** over ``λΔt``
  (per-side steppers ``Eₗ*``, which may differ from ``Eₗ`` — thesis §2.3.5), the
  core over ``Δt``, sections forward over ``(1-λ)Δt``; built from two
  :class:`SequentialUpdateSplitting` passes. ``λ = ½`` (Strang) is the only choice
  with second-order coupling error regardless of problem structure.

Every federation is itself a component (Stepper-shaped: ``(state, timestep, *,
out=None) -> (diagnostics, new_state)``), so federations compose. Declared
coupling constraints (:mod:`symcon.core.coupling.constraints`) are validated at
construction.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
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
from symcon.core.coupling.constraints import validate_composition
from symcon.core.coupling.steppers import SequentialTendencyStepper, TendencyStepper
from symcon.core.registry import Factory

__all__ = [
    "SSUS",
    "ParallelSplitting",
    "SequentialTendencySplitting",
    "SequentialUpdateSplitting",
]

#: A federation section: a bare Stepper-shaped component or (component, stepper name).
SectionSpec = Any

_STEPPER_DICTS = ("diagnostic_properties", "output_properties")


@dataclasses.dataclass(frozen=True, slots=True)
class _Section:
    """One normalized section: the constraint carrier + the callable stepper."""

    carrier: Any
    stepper: Any


def _is_stepper_kind(obj: object) -> bool:
    return callable(obj) and output_dict_names_of(obj) == _STEPPER_DICTS


def _normalize_section(
    section: SectionSpec,
    *,
    registry_root: type[Factory],
    federation: str,
    position: int,
) -> _Section:
    """Resolve one section spec into (carrier, stepper)."""
    if isinstance(section, tuple):
        if len(section) != 2 or not isinstance(section[1], str):
            raise TypeError(
                f"{federation}: section {position} must be (component, stepper_name), "
                f"got {section!r}."
            )
        component, stepper_name = section
        if not is_tendency_kind(component):
            raise TypeError(
                f"{federation}: section {position} pairs {name_of(component)!r} with "
                f"stepper {stepper_name!r}, but it is not a tendency provider "
                f"(output_dict_names={output_dict_names_of(component)!r})."
            )
        stepper = registry_root.factory(stepper_name, component)
        return _Section(carrier=component, stepper=stepper)
    if _is_stepper_kind(section):
        return _Section(carrier=section, stepper=section)
    raise TypeError(
        f"{federation}: section {position} is neither a Stepper-shaped component nor "
        f"a (TendencyComponent, stepper_name) pair: {section!r} "
        f"(output_dict_names={getattr(section, 'output_dict_names', None)!r})."
    )


def _call_stepper(
    stepper: Any,
    state: Mapping[str, Any],
    timestep: timedelta,
) -> tuple[DataArrayDict, DataArrayDict]:
    call = cast("Callable[..., Any]", stepper)
    result: tuple[DataArrayDict, DataArrayDict] = call(state, timestep)
    return result


class _FederationBase:
    """Shared surface making federations composable components (SPEC S04)."""

    #: Federation kind label, used for constraint validation and errors.
    kind: ClassVar[str]
    #: Stepper-kind fingerprint: federations compose like §4.1 Steppers.
    output_dict_names: ClassVar[tuple[str, ...]] = _STEPPER_DICTS
    timestep_required: ClassVar[bool] = True

    _sections: tuple[_Section, ...]

    def __init__(self, sections: Sequence[_Section], *, name: str | None = None) -> None:
        self._sections = tuple(sections)
        if not self._sections:
            raise ValueError(f"{type(self).__name__}: at least one section is required.")
        self.name = name if name is not None else type(self).__name__
        self._parsed = self._merge_properties()

    def _merge_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        """Aggregate section property dicts (approximate union view at T0).

        Inputs are unioned net of fields produced by earlier sections (sequential
        reading); outputs and diagnostics are unioned with later sections winning.
        Cross-section spec conflicts are not re-validated here — every section
        validates its own contract on call (T0 reference semantics).
        """
        inputs: dict[str, PropertySpec] = {}
        outputs: dict[str, PropertySpec] = {}
        diagnostics: dict[str, PropertySpec] = {}
        produced: set[str] = set()
        for section in self._sections:
            parsed = parsed_properties_of(section.stepper)
            for field, spec in parsed.get("input_properties", {}).items():
                if field not in produced and field not in inputs:
                    inputs[field] = spec
            diagnostics.update(parsed.get("diagnostic_properties", {}))
            outputs.update(parsed.get("output_properties", {}))
            produced.update(parsed.get("diagnostic_properties", {}))
            produced.update(parsed.get("output_properties", {}))
        return {
            "input_properties": inputs,
            "diagnostic_properties": diagnostics,
            "output_properties": outputs,
        }

    @property
    def sections(self) -> tuple[Any, ...]:
        """The normalized section steppers, in declared order."""
        return tuple(section.stepper for section in self._sections)

    @property
    def parsed_properties(self) -> Mapping[str, Mapping[str, PropertySpec]]:
        """Aggregated parsed property dicts (see :meth:`_merge_properties`)."""
        return self._parsed

    def __str__(self) -> str:
        lines = [f"instance of {type(self).__name__}"]
        lines.extend(f"    {name_of(section.stepper)}" for section in self._sections)
        return "\n".join(lines)

    def _validate_out(self, out: Mapping[str, xr.DataArray] | None) -> None:
        if out is None:
            return
        known = set(self._parsed["diagnostic_properties"]) | set(self._parsed["output_properties"])
        unknown = set(out) - known
        if unknown:
            raise ValueError(
                f"{self.name}: out= names {sorted(unknown)} are not outputs of this "
                f"federation (outputs: {sorted(known)})."
            )

    def _package(
        self,
        state: Mapping[str, Any],
        diagnostics: DataArrayDict,
        updates: Mapping[str, Any],
        out: Mapping[str, xr.DataArray] | None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """Deliver (diagnostics, new_state); ``updates`` maps field -> DataArray|buffer."""
        diag_result: DataArrayDict = {}
        for field, array in diagnostics.items():
            if out is not None and field in out:
                out[field].data[...] = array.data
                diag_result[field] = out[field]
            else:
                diag_result[field] = array
        new_state: DataArrayDict = {}
        for field, value in updates.items():
            array = value if isinstance(value, xr.DataArray) else state[field].copy(data=value)
            if out is not None and field in out:
                out[field].data[...] = array.data
                new_state[field] = out[field]
            else:
                new_state[field] = array
        return diag_result, new_state

    # -- restart / functional carry (delegated per section) ---------------------------

    def restart_state(self) -> dict[str, xr.DataArray]:
        """Union of the sections' private state, namespaced by section position."""
        result: dict[str, xr.DataArray] = {}
        for index, section in enumerate(self._sections):
            for key, value in section.stepper.restart_state().items():
                result[f"section{index}/{key}"] = value
        return result

    def load_restart_state(self, restart: Mapping[str, xr.DataArray]) -> None:
        """Route restart entries back to the owning sections."""
        per_section: dict[int, dict[str, xr.DataArray]] = {
            index: {} for index in range(len(self._sections))
        }
        for key, value in restart.items():
            prefix, _, inner = key.partition("/")
            if not (prefix.startswith("section") and inner):
                raise ValueError(f"{self.name}: unknown restart key {key!r}.")
            try:
                bucket = per_section[int(prefix[len("section") :])]
            except (KeyError, ValueError):
                raise ValueError(f"{self.name}: unknown restart key {key!r}.") from None
            bucket[inner] = value
        for index, section in enumerate(self._sections):
            section.stepper.load_restart_state(per_section[index])

    def functional_state(self) -> Mapping[str, PropertySpec]:
        """Union of the sections' carry schemas, namespaced by section position."""
        schema: dict[str, PropertySpec] = {}
        for index, section in enumerate(self._sections):
            for key, spec in section.stepper.functional_state().items():
                name = f"section{index}/{key}"
                schema[name] = dataclasses.replace(spec, name=name)
        return schema


class ParallelSplitting(_FederationBase):
    """PS — thesis eq. (2.10) (frozen interface, SPEC S04).

    Every section is integrated independently from ψⁿ; the provisional states are
    recombined per field as ``ψⁿ⁺¹ = Σₗ ψₗⁿ⁺¹ - L·ψⁿ`` where ``L`` counts the
    sections stepping that field (eq. 2.10d). Section diagnostics are all computed
    on ψⁿ (sections are order-independent by construction).
    """

    kind: ClassVar[str] = "parallel_splitting"

    def __init__(self, sections: Sequence[SectionSpec], *, name: str | None = None) -> None:
        normalized = [
            _normalize_section(
                section, registry_root=TendencyStepper, federation=self.kind, position=i
            )
            for i, section in enumerate(sections)
        ]
        validate_composition(
            [section.carrier for section in normalized], operator=self.kind, ordered=False
        )
        super().__init__(normalized, name=name)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """One PS step from ``state`` over ``timestep``."""
        self._validate_out(out)
        diagnostics: DataArrayDict = {}
        accumulated: dict[str, Any] = {}
        for section in self._sections:
            section_diags, section_state = _call_stepper(section.stepper, state, timestep)
            diagnostics.update(section_diags)
            for field, array in section_state.items():
                held = accumulated.get(field)
                if held is None:
                    accumulated[field] = array.data
                else:
                    # ψⁿ⁺¹ = Σψₗ - L·ψⁿ, accumulated one axpy at a time (2.10d).
                    accumulated[field] = held + (array.data - state[field].data)
        return self._package(state, diagnostics, accumulated, out)


class SequentialUpdateSplitting(_FederationBase):
    """SUS — thesis eq. (2.12) (frozen interface, SPEC S04).

    Sections are chained: each corrects the state left by its predecessor
    (diagnostics included). Ordering is semantics and is validated against the
    sections' declared coupling constraints at construction.
    """

    kind: ClassVar[str] = "sequential_update_splitting"

    def __init__(
        self,
        sections: Sequence[SectionSpec],
        *,
        name: str | None = None,
        _validate: bool = True,
        _operator_label: str | None = None,
    ) -> None:
        label = _operator_label if _operator_label is not None else self.kind
        normalized = [
            _normalize_section(section, registry_root=TendencyStepper, federation=label, position=i)
            for i, section in enumerate(sections)
        ]
        if _validate:
            validate_composition([section.carrier for section in normalized], operator=label)
        super().__init__(normalized, name=name)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """One SUS step from ``state`` over ``timestep``."""
        self._validate_out(out)
        working: dict[str, Any] = dict(state)
        diagnostics: DataArrayDict = {}
        updates: DataArrayDict = {}
        for section in self._sections:
            section_diags, section_state = _call_stepper(section.stepper, working, timestep)
            working.update(section_diags)
            working.update(section_state)
            diagnostics.update(section_diags)
            updates.update(section_state)
        return self._package(state, diagnostics, updates, out)


class SequentialTendencySplitting(_FederationBase):
    """STS — thesis eq. (2.11) (frozen interface, SPEC S04).

    The first section (the dynamics, eq. 2.11a) is stepped plainly from ψⁿ; every
    later section must be a ``(TendencyComponent, stepper_name)`` pair resolved to
    a :class:`~symcon.core.coupling.steppers.SequentialTendencyStepper` — it
    integrates **from the step-initial ψⁿ** (eq. 2.11b), with the accumulated
    provisional state entering as the constant forcing ``(ψ_prov - ψⁿ)/Δt``.
    Bare Steppers cannot express that signature and are rejected past position 0
    (adjustment-type processes belong in :class:`SequentialUpdateSplitting`).
    """

    kind: ClassVar[str] = "sequential_tendency_splitting"

    def __init__(self, sections: Sequence[SectionSpec], *, name: str | None = None) -> None:
        specs = list(sections)
        if not specs:
            raise ValueError(f"{type(self).__name__}: at least one section is required.")
        normalized = [
            _normalize_section(
                specs[0], registry_root=TendencyStepper, federation=self.kind, position=0
            )
        ]
        for position, spec in enumerate(specs[1:], start=1):
            if not isinstance(spec, tuple) and _is_stepper_kind(spec):
                raise TypeError(
                    f"{self.kind}: section {position} ({name_of(spec)!r}) is a bare "
                    f"Stepper, which cannot take the (ψ_prov - ψⁿ)/Δt forcing of "
                    f"eq. (2.11b); use a (TendencyComponent, stepper_name) pair or "
                    f"SequentialUpdateSplitting."
                )
            normalized.append(
                _normalize_section(
                    spec,
                    registry_root=SequentialTendencyStepper,
                    federation=self.kind,
                    position=position,
                )
            )
        validate_composition([section.carrier for section in normalized], operator=self.kind)
        super().__init__(normalized, name=name)

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """One STS step from ``state`` over ``timestep``."""
        self._validate_out(out)
        # ψⁿ-level state: accumulates diagnostics only (tasmania's two-dict discipline).
        current: dict[str, Any] = dict(state)
        diagnostics: DataArrayDict = {}
        updates: DataArrayDict = {}

        first = self._sections[0]
        section_diags, section_state = _call_stepper(first.stepper, current, timestep)
        current.update(section_diags)
        diagnostics.update(section_diags)
        updates.update(section_state)
        # Provisional state: ψⁿ overlaid with the accumulated provisional outputs.
        provisional: dict[str, Any] = dict(state)
        provisional.update(section_state)

        for section in self._sections[1:]:
            stepper = cast("Callable[..., Any]", section.stepper)
            section_diags, section_state = stepper(current, provisional, timestep)
            current.update(section_diags)
            diagnostics.update(section_diags)
            provisional.update(section_state)
            updates.update(section_state)
        return self._package(state, diagnostics, updates, out)


class SSUS(_FederationBase):
    """SSUS — thesis eq. (2.13a-e) (frozen interface, SPEC S04).

    ``SSUS(sections, core, lam=0.5, pre_steppers=None)``: the physics ``sections``
    are traversed in **reverse** over ``λΔt`` (2.13a-b), the dynamics ``core`` runs
    over the full ``Δt`` (2.13c), then the sections run forward over ``(1-λ)Δt``
    (2.13d-e). ``pre_steppers`` optionally names, per section, the scheme used on
    the pre side (``Eₗ* ≠ Eₗ`` is legal, thesis §2.3.5); entries must be ``None``
    for bare-Stepper sections (they own their numerics). Constraints are validated
    on the forward order ``[core, *sections]`` under the ``"ssus"`` label; the
    reverse pass is its mirror by construction.
    """

    kind: ClassVar[str] = "ssus"

    def __init__(
        self,
        sections: Sequence[SectionSpec],
        core: SectionSpec,
        lam: float = 0.5,
        pre_steppers: Sequence[str | None] | None = None,
        *,
        name: str | None = None,
    ) -> None:
        section_specs = list(sections)
        if not section_specs:
            raise ValueError(f"{type(self).__name__}: at least one section is required.")
        if not 0.0 < lam < 1.0:
            raise ValueError(f"{type(self).__name__}: lam must be in (0, 1), got {lam!r}.")
        self._lam = float(lam)

        if pre_steppers is None:
            pre_specs = list(section_specs)
        else:
            pre_names = list(pre_steppers)
            if len(pre_names) != len(section_specs):
                raise ValueError(
                    f"{type(self).__name__}: pre_steppers has {len(pre_names)} entries "
                    f"for {len(section_specs)} sections."
                )
            pre_specs = []
            for spec, pre_name in zip(section_specs, pre_names, strict=True):
                if pre_name is None:
                    pre_specs.append(spec)
                elif isinstance(spec, tuple):
                    pre_specs.append((spec[0], pre_name))
                else:
                    raise ValueError(
                        f"{type(self).__name__}: section {name_of(spec)!r} is a bare "
                        f"Stepper with its own numerics; its pre_steppers entry must "
                        f"be None, got {pre_name!r}."
                    )

        core_section = _normalize_section(
            core, registry_root=TendencyStepper, federation=self.kind, position=0
        )
        # Two SUS passes (SPEC): reverse order first over λΔt, forward over (1-λ)Δt.
        self._pre = SequentialUpdateSplitting(
            tuple(reversed(pre_specs)), _validate=False, _operator_label=self.kind
        )
        self._post = SequentialUpdateSplitting(
            tuple(section_specs), _validate=False, _operator_label=self.kind
        )
        validate_composition(
            [core_section.carrier] + [section.carrier for section in self._post._sections],
            operator=self.kind,
        )
        super().__init__((core_section, *self._post._sections), name=name)
        self._core = core_section

    @property
    def lam(self) -> float:
        """The λ split; ½ is Strang splitting (second-order coupling error)."""
        return self._lam

    def __call__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        *,
        out: Mapping[str, xr.DataArray] | None = None,
    ) -> tuple[DataArrayDict, DataArrayDict]:
        """One SSUS step from ``state`` over ``timestep``."""
        self._validate_out(out)
        pre_dt = timestep * self._lam
        post_dt = timestep - pre_dt  # exact complement: λΔt + (1-λ)Δt ≡ Δt

        working: dict[str, Any] = dict(state)
        diagnostics: DataArrayDict = {}
        updates: DataArrayDict = {}

        def advance(diags: DataArrayDict, new_state: DataArrayDict) -> None:
            working.update(diags)
            working.update(new_state)
            diagnostics.update(diags)
            updates.update(new_state)

        pre_diags, pre_state = self._pre(working, pre_dt)
        advance(pre_diags, pre_state)
        core_diags, core_state = _call_stepper(self._core.stepper, working, timestep)
        advance(core_diags, core_state)
        post_diags, post_state = self._post(working, post_dt)
        advance(post_diags, post_state)
        return self._package(state, diagnostics, updates, out)
