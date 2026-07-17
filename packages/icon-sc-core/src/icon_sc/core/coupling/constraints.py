"""Coupling constraints (architecture §4.2/§11 risk 7; SPEC S04).

Components may declare, via a ``coupling_constraints`` attribute holding a
:class:`CouplingConstraints`, where they are allowed to sit in a composition:

- ``must_follow`` / ``must_precede`` — ordering constraints against other
  components (matched by component ``name``), enforced for the *sequential*
  federations, where ordering is semantics;
- ``admissible_operators`` — the coupling operators the component may enter at
  all (``None`` = any). Operator labels are the federation ``kind`` strings:
  ``"parallel_splitting"``, ``"sequential_tendency_splitting"``,
  ``"sequential_update_splitting"``, ``"ssus"``.

Validation runs **when a federation is constructed** (composition time — never on
the step path); a violation raises :class:`CouplingConstraintError` naming both
components involved. This is what decides whether a composite is merely
structurally legal or also scientifically admissible (§4.2): experimental
composites never inherit the validated-preset label.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from icon_sc.core.components.wrappers import ComponentWrapper
from icon_sc.core.coupling.concurrent import name_of

__all__ = [
    "CouplingConstraintError",
    "CouplingConstraints",
    "constraints_of",
    "validate_composition",
]


class CouplingConstraintError(ValueError):
    """A composition violates a component's declared coupling constraints."""


@dataclasses.dataclass(frozen=True, slots=True)
class CouplingConstraints:
    """Declared placement constraints of one component (frozen interface, SPEC S04)."""

    must_follow: tuple[str, ...] = ()
    must_precede: tuple[str, ...] = ()
    admissible_operators: tuple[str, ...] | None = None


def constraints_of(component: Any) -> CouplingConstraints:
    """The component's declared constraints (empty constraints when undeclared)."""
    declared = getattr(component, "coupling_constraints", None)
    if declared is None:
        return CouplingConstraints()
    if not isinstance(declared, CouplingConstraints):
        raise TypeError(
            f"{name_of(component)!r}: coupling_constraints must be a "
            f"CouplingConstraints, got {type(declared).__name__}."
        )
    return declared


def _constraint_name(component: Any) -> str:
    """The name constraints match against: the innermost wrapped component's.

    Control-flow wrappers rename (``CallingFrequency(Convection)``); constraints
    declared *against* a component must still bind when it enters a composition
    wrapped, so wrapper chains are walked to the scientific component.
    """
    inner = component
    while isinstance(inner, ComponentWrapper):
        inner = inner.component
    return name_of(inner)


def validate_composition(components: Sequence[Any], *, operator: str, ordered: bool = True) -> None:
    """Check a composition against every member's constraints (SPEC S04).

    ``components`` is the composition in execution order (the *constraint
    carriers*: the scientific components, not the steppers wrapped around them).
    ``ordered=False`` (parallel splitting: order carries no semantics) skips the
    ordering constraints and checks ``admissible_operators`` only.

    Constraint names are matched against the **innermost** component of a
    wrapper chain (see :func:`_constraint_name`), so wrapping a component —
    ``CallingFrequency``-wrapped slow physics being the canonical case — neither
    sheds the constraints it declares (attribute delegation) nor the constraints
    declared against it (name unwrapping).

    ``must_follow``/``must_precede`` bind only when the named component is present:
    for a component at position ``i``, every name in ``must_follow`` present in the
    composition must first occur before ``i``, and every name in ``must_precede``
    must last occur after ``i``.
    """
    names = [_constraint_name(component) for component in components]
    for index, component in enumerate(components):
        constraints = constraints_of(component)
        if (
            constraints.admissible_operators is not None
            and operator not in constraints.admissible_operators
        ):
            raise CouplingConstraintError(
                f"component {names[index]!r} does not admit the {operator!r} operator "
                f"(admissible: {list(constraints.admissible_operators)!r})."
            )
        if not ordered:
            continue
        for other in constraints.must_follow:
            if other in names and names.index(other) > index:
                raise CouplingConstraintError(
                    f"{operator}: component {names[index]!r} must follow {other!r}, "
                    f"but {other!r} comes after it "
                    f"(order: {names!r})."
                )
        for other in constraints.must_precede:
            positions = [i for i, name in enumerate(names) if name == other]
            if positions and positions[-1] < index:
                raise CouplingConstraintError(
                    f"{operator}: component {names[index]!r} must precede {other!r}, "
                    f"but {other!r} comes before it "
                    f"(order: {names!r})."
                )
