"""PEP 420 two-package import test (PLAN S01 item 2)."""

from __future__ import annotations


def test_namespace_spans_all_three_distributions() -> None:
    import icon_sc
    import icon_sc.bridges
    import icon_sc.core
    import icon_sc.icon

    roots = {p.rsplit("/", 3)[-3] for p in icon_sc.__path__}
    assert roots == {"icon-sc-core", "icon-sc-icon", "icon-sc-bridges"}
    assert not hasattr(icon_sc, "__file__") or icon_sc.__file__ is None  # no __init__.py


def test_core_is_typed() -> None:
    from importlib import resources

    assert resources.files("icon_sc.core").joinpath("py.typed").is_file()
