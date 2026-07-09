"""PEP 420 two-package import test (PLAN S01 item 2)."""

from __future__ import annotations


def test_namespace_spans_all_three_distributions() -> None:
    import symcon
    import symcon.bridges
    import symcon.core
    import symcon.icon

    roots = {p.rsplit("/", 3)[-3] for p in symcon.__path__}
    assert roots == {"symcon-core", "symcon-icon", "symcon-bridges"}
    assert not hasattr(symcon, "__file__") or symcon.__file__ is None  # no __init__.py


def test_core_is_typed() -> None:
    from importlib import resources

    assert resources.files("symcon.core").joinpath("py.typed").is_file()
