"""Generated frozen-dataclass PyTrees: StateTree and ParamTree (§8.5, SPEC S10).

``StateTree`` is derived from the state/vault schema — one leaf per slot —
extended with **explicit carry**: every leaf a component declared in
``functional_state()`` is surfaced into the tree (tension T7: §4.5's privacy is
an imperative-tier convenience, demoted here by contract). ``ParamTree`` holds
the tunable scheme constants of the §8.6 ``params`` declarations, distinct from
state — calibration never smuggles constants through state fields.

Leaf ordering is deterministic: leaves are sorted by canonical name at type
generation (PLAN pitfall — carry ordering must not depend on dict insertion
order). Canonical names (``icon:qnc``, ``fcarry/0/...``) are not identifiers;
they are sanitized into attribute names with the canonical → attribute map kept
on the generated class (``__symcon_leaves__``).
"""

from __future__ import annotations

import dataclasses
import keyword
import re
from collections.abc import Mapping, Sequence
from typing import Any

import jax

__all__ = [
    "build_param_tree",
    "build_state_tree",
    "make_pytree_type",
    "mapping_of",
    "sanitize_leaf_name",
    "tree_of",
]

_INVALID = re.compile(r"\W")


def sanitize_leaf_name(name: str) -> str:
    """A valid Python attribute name for one canonical leaf name."""
    attr = _INVALID.sub("_", name)
    if not attr or attr[0].isdigit() or keyword.iskeyword(attr):
        attr = f"f_{attr}"
    return attr


def make_pytree_type(type_name: str, leaf_names: Sequence[str]) -> type:
    """Generate a frozen-dataclass PyTree type with one field per leaf name.

    Leaves are sorted by canonical name; the generated class is registered with
    ``jax.tree_util.register_dataclass`` (all fields are data fields) and carries
    ``__symcon_leaves__``: the ``(canonical_name, attribute_name)`` pairs in
    field order.
    """
    ordered = sorted(leaf_names)
    if len(set(ordered)) != len(ordered):
        dupes = sorted({n for n in ordered if ordered.count(n) > 1})
        raise ValueError(f"{type_name}: duplicate leaf names {dupes!r}.")
    pairs = tuple((name, sanitize_leaf_name(name)) for name in ordered)
    attrs = [attr for _, attr in pairs]
    if len(set(attrs)) != len(attrs):
        dupes = sorted({a for a in attrs if attrs.count(a) > 1})
        raise ValueError(
            f"{type_name}: sanitized leaf names collide on {dupes!r}; "
            f"rename the offending fields."
        )
    cls = dataclasses.make_dataclass(
        type_name,
        [(attr, Any) for attr in attrs],
        frozen=True,
        namespace={"__symcon_leaves__": pairs},
    )
    jax.tree_util.register_dataclass(cls, data_fields=attrs, meta_fields=[])
    return cls


def tree_of(cls: type, values: Mapping[str, Any]) -> Any:
    """Instantiate a generated PyTree type from a canonical-name → leaf mapping."""
    pairs: tuple[tuple[str, str], ...] = cls.__symcon_leaves__  # type: ignore[attr-defined]
    missing = [name for name, _ in pairs if name not in values]
    if missing:
        raise KeyError(f"{cls.__name__}: missing leaves {missing!r}.")
    extra = sorted(set(values) - {name for name, _ in pairs})
    if extra:
        raise KeyError(f"{cls.__name__}: unknown leaves {extra!r}.")
    return cls(**{attr: values[name] for name, attr in pairs})


def mapping_of(tree: Any) -> dict[str, Any]:
    """The canonical-name → leaf mapping of a generated PyTree instance."""
    pairs: tuple[tuple[str, str], ...] = type(tree).__symcon_leaves__  # type: ignore[attr-defined]
    return {name: getattr(tree, attr) for name, attr in pairs}


def _leaf_array(value: Any) -> Any:
    """One state entry as an fp-preserving jax array (DataArrays unwrap to .data)."""
    import jax.numpy as jnp

    data = getattr(value, "data", value)  # boundary DataArray → raw buffer (§2.2)
    return jnp.asarray(data)


def build_state_tree(
    state: Mapping[str, Any],
    extra_leaves: Mapping[str, Any] | None = None,
    *,
    type_name: str = "StateTree",
) -> tuple[type, Any]:
    """StateTree type + instance from a state dict (one leaf per slot) plus carry.

    ``state`` is a boundary state (dict of DataArrays; ``time`` is skipped — the
    F-tier trace has no clock, cadence rides in the carry). ``extra_leaves`` are
    the explicit-carry leaves and any compiler-seeded slots (already arrays).
    """
    values: dict[str, Any] = {}
    for name, value in state.items():
        if name == "time":
            continue
        values[name] = _leaf_array(value)
    for name, value in (extra_leaves or {}).items():
        if name in values:
            raise ValueError(f"{type_name}: extra leaf {name!r} collides with a state field.")
        values[name] = _leaf_array(value)
    cls = make_pytree_type(type_name, tuple(values))
    return cls, tree_of(cls, values)


def build_param_tree(
    params: Mapping[str, Any], *, type_name: str = "ParamTree"
) -> tuple[type, Any]:
    """ParamTree type + instance from a flat name → default-value mapping (§8.6)."""
    import jax.numpy as jnp

    values = {name: jnp.asarray(value, dtype=jnp.float64) for name, value in params.items()}
    cls = make_pytree_type(type_name, tuple(values))
    return cls, tree_of(cls, values)
