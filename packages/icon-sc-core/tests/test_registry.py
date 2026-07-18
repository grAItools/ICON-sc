"""Factory/MetaFactory acceptance (SPEC S02 §4): thesis Fig. 3.5 semantics."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from icon_sc.core.registry import Factory, RegistrationError


class Stepper(Factory):
    """Registry root."""


class ForwardEuler(Stepper):
    name = "forward_euler"

    def __init__(self, order: int = 1) -> None:
        self.order = order


class RK2(Stepper):
    name = "rk2"


class OtherRoot(Factory):
    """Independent root: registries must not bleed across hierarchies."""


class OtherImpl(OtherRoot):
    name = "other"


@pytest.fixture(autouse=True)
def _restore_registries() -> Iterator[None]:
    # Tests below register throwaway classes; snapshot/restore keeps every test
    # independent of execution order.
    saved = {root: dict(root.registry) for root in (Stepper, OtherRoot)}
    yield
    for root, snapshot in saved.items():
        root.registry.clear()
        root.registry.update(snapshot)


def test_registry_populated_on_import() -> None:
    # Registration happened at class-creation (= module import) time, with no
    # explicit register() call anywhere.
    assert Stepper.registry == {"forward_euler": ForwardEuler, "rk2": RK2}


def test_factory_resolves_and_instantiates() -> None:
    stepper = Stepper.factory("forward_euler", order=3)
    assert isinstance(stepper, ForwardEuler)
    assert stepper.order == 3


def test_unknown_name_is_keyerror_listing_known_names() -> None:
    with pytest.raises(KeyError, match=r"rk3ws.*forward_euler.*rk2"):
        Stepper.factory("rk3ws")


def test_registries_are_per_root() -> None:
    assert OtherRoot.registry == {"other": OtherImpl}
    assert "other" not in Stepper.registry


def test_duplicate_name_rejected() -> None:
    with pytest.raises(RegistrationError, match="forward_euler"):

        class Duplicate(Stepper):
            name = "forward_euler"


def test_unnamed_intermediate_stays_unregistered() -> None:
    class AbstractRK(Stepper):
        pass

    class RK3WS(AbstractRK):
        name = "rk3ws"

    assert Stepper.registry["rk3ws"] is RK3WS
    assert not any(cls is AbstractRK for cls in Stepper.registry.values())


def test_named_class_without_root_rejected() -> None:
    with pytest.raises(RegistrationError, match="registry root"):
        type("Orphan", (Factory,), {})  # direct subclass is a root, fine ...

        # ... but a named grandchild of a *rootless* chain cannot exist: the only
        # way to get there is naming Factory's own subclass tree without a root,
        # which the direct-subclass rule makes impossible; simulate by removing
        # the registry.
        class Root(Factory):
            pass

        del Root.registry

        class Named(Root):
            name = "x"
