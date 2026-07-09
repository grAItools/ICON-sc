"""Name-keyed ``Factory``/``MetaFactory`` registries (architecture §4.2 ← Ubbiali).

Semantics ported from the stubbiali/sympl ``oop`` fork (``sympl/_core/factory.py``,
thesis Fig. 3.5), not the code: subclasses self-register at class-creation time (i.e.
on import), keyed by their ``name`` class attribute; duplicate names are rejected;
``Factory.factory(name)`` resolves a configuration string to a class and instantiates
it, raising ``KeyError`` listing the known names when the string is unknown.

Usage: a *registry root* subclasses :class:`Factory` directly and gets a fresh
``registry``; concrete implementations subclass the root and set ``name``.
Intermediate classes that set no ``name`` of their own stay unregistered.
"""

from __future__ import annotations

import abc
from typing import Any, ClassVar, TypeVar

__all__ = ["Factory", "MetaFactory", "RegistrationError"]

_F = TypeVar("_F", bound="Factory")


class RegistrationError(Exception):
    """A class could not be registered (duplicate name or missing registry root)."""


class MetaFactory(abc.ABCMeta):
    """Metaclass performing register-on-import for :class:`Factory` hierarchies."""

    def __init__(cls, clsname: str, bases: tuple[type, ...], ns: dict[str, Any], **kw: Any):
        super().__init__(clsname, bases, ns, **kw)
        try:
            factory_cls = Factory
        except NameError:  # creating Factory itself
            return
        if factory_cls in bases:  # a registry root: fresh, name-keyed registry
            fresh: dict[str, type[Factory]] = {}
            cls.registry = fresh
            return
        if "name" not in ns:  # unnamed intermediate: stays unregistered
            return
        registry: dict[str, type[Factory]] | None = getattr(cls, "registry", None)
        if registry is None:
            raise RegistrationError(
                f"{clsname} sets name={ns['name']!r} but no ancestor subclasses "
                "Factory directly (no registry root)."
            )
        name = ns["name"]
        if name in registry:
            raise RegistrationError(
                f"cannot register {clsname} as {name!r}: "
                f"{registry[name].__name__} already holds that name."
            )
        registry[name] = cls  # type: ignore[assignment]


class Factory(metaclass=MetaFactory):
    """Base for name-keyed registries; see module docstring for the usage pattern."""

    name: ClassVar[str]
    registry: ClassVar[dict[str, type[Factory]]]

    @classmethod
    def factory(cls: type[_F], name: str, *args: Any, **kwargs: Any) -> _F:
        """Instantiate the class registered under ``name`` (KeyError if unknown)."""
        registry = getattr(cls, "registry", {})
        if name not in registry:
            raise KeyError(
                f"no {cls.__name__} registered under {name!r}; known names: {sorted(registry)}"
            )
        subclass: type[_F] = registry[name]
        return subclass(*args, **kwargs)
