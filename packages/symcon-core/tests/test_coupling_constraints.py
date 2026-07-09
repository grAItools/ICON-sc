"""Coupling-constraints unit tests (SPEC S04): declaration + validation rules."""

from __future__ import annotations

import pytest

from symcon.core.coupling import (
    CouplingConstraintError,
    CouplingConstraints,
    constraints_of,
    validate_composition,
)


class _Named:
    def __init__(self, name: str, constraints: CouplingConstraints | None = None) -> None:
        self.name = name
        if constraints is not None:
            self.coupling_constraints = constraints


def test_constraints_default_to_empty() -> None:
    assert constraints_of(_Named("plain")) == CouplingConstraints()


def test_constraints_type_is_enforced() -> None:
    bad = _Named("bad")
    bad.coupling_constraints = {"must_follow": ("x",)}  # type: ignore[assignment]
    with pytest.raises(TypeError, match="must be a CouplingConstraints"):
        constraints_of(bad)


def test_must_follow_violation_names_both_components() -> None:
    first = _Named("micro", CouplingConstraints(must_follow=("conv",)))
    second = _Named("conv")
    with pytest.raises(CouplingConstraintError) as excinfo:
        validate_composition([first, second], operator="sequential_update_splitting")
    message = str(excinfo.value)
    assert "micro" in message
    assert "conv" in message


def test_must_follow_satisfied() -> None:
    conv = _Named("conv")
    micro = _Named("micro", CouplingConstraints(must_follow=("conv",)))
    validate_composition([conv, micro], operator="sequential_update_splitting")


def test_must_precede() -> None:
    turb = _Named("turb", CouplingConstraints(must_precede=("surface",)))
    surface = _Named("surface")
    validate_composition([turb, surface], operator="sequential_update_splitting")
    with pytest.raises(CouplingConstraintError, match="must precede"):
        validate_composition([surface, turb], operator="sequential_update_splitting")


def test_absent_reference_does_not_bind() -> None:
    micro = _Named("micro", CouplingConstraints(must_follow=("conv",), must_precede=("sfc",)))
    validate_composition([micro], operator="sequential_update_splitting")


def test_admissible_operators() -> None:
    picky = _Named("picky", CouplingConstraints(admissible_operators=("ssus",)))
    validate_composition([picky], operator="ssus")
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        validate_composition([picky], operator="parallel_splitting")


def test_unordered_mode_skips_ordering_but_keeps_admissibility() -> None:
    first = _Named("micro", CouplingConstraints(must_follow=("conv",)))
    second = _Named("conv")
    # Parallel composition: order carries no semantics.
    validate_composition([first, second], operator="parallel_splitting", ordered=False)
    picky = _Named("picky", CouplingConstraints(admissible_operators=("ssus",)))
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        validate_composition([picky], operator="parallel_splitting", ordered=False)
