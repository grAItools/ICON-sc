"""S10: generated PyTrees (StateTree/ParamTree) — pytree.py unit tests."""

from __future__ import annotations

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from symcon.core.functional.pytree import (  # noqa: E402
    build_param_tree,
    build_state_tree,
    make_pytree_type,
    mapping_of,
    sanitize_leaf_name,
    tree_of,
)
from symcon.core.state.dataarray import make_dataarray  # noqa: E402
from symcon.core.time import datetime  # noqa: E402


def test_sanitize_leaf_name() -> None:
    assert sanitize_leaf_name("icon:qnc") == "icon_qnc"
    assert sanitize_leaf_name("fcarry/0/a b") == "fcarry_0_a_b"
    assert sanitize_leaf_name("0abc") == "f_0abc"
    assert sanitize_leaf_name("class") == "f_class"


def test_make_pytree_type_sorted_deterministic() -> None:
    cls_a = make_pytree_type("T", ["b", "a", "icon:x"])
    cls_b = make_pytree_type("T", ["icon:x", "a", "b"])
    assert cls_a.__symcon_leaves__ == cls_b.__symcon_leaves__
    assert [name for name, _ in cls_a.__symcon_leaves__] == ["a", "b", "icon:x"]


def test_pytree_registration_roundtrip() -> None:
    cls = make_pytree_type("T", ["a", "b"])
    tree = tree_of(cls, {"a": jnp.ones(3), "b": jnp.zeros(2)})
    leaves, treedef = jax.tree_util.tree_flatten(tree)
    assert len(leaves) == 2
    rebuilt = jax.tree_util.tree_unflatten(treedef, leaves)
    assert mapping_of(rebuilt).keys() == {"a", "b"}
    # frozen: functional updates only
    with pytest.raises((AttributeError, TypeError)):
        tree.a = jnp.zeros(3)  # type: ignore[misc]


def test_duplicate_and_colliding_names_raise() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        make_pytree_type("T", ["a", "a"])
    with pytest.raises(ValueError, match="collide"):
        make_pytree_type("T", ["icon:x", "icon/x"])


def test_tree_of_missing_and_unknown() -> None:
    cls = make_pytree_type("T", ["a"])
    with pytest.raises(KeyError, match="missing"):
        tree_of(cls, {})
    with pytest.raises(KeyError, match="unknown"):
        tree_of(cls, {"a": 1.0, "b": 2.0})


def test_build_state_tree_skips_time_and_unwraps() -> None:
    state = {
        "time": datetime(2000, 1, 1),
        "eastward_wind": make_dataarray(
            np.arange(4.0).reshape(1, 4),
            name="eastward_wind",
            dims=("cell", "height"),
            units="m s-1",
            location="cell",
        ),
    }
    _, tree = build_state_tree(state, {"fstep": np.asarray(0.0)})
    values = mapping_of(tree)
    assert set(values) == {"eastward_wind", "fstep"}
    assert isinstance(values["eastward_wind"], jax.Array)
    assert values["eastward_wind"].dtype == jnp.float64
    np.testing.assert_array_equal(np.asarray(values["eastward_wind"]), state["eastward_wind"].data)
    with pytest.raises(ValueError, match="collides"):
        build_state_tree(state, {"eastward_wind": np.zeros(1)})


def test_build_param_tree_float64() -> None:
    cls, tree = build_param_tree({"graupel/kcau": 9.44e9})
    (value,) = jax.tree_util.tree_leaves(tree)
    assert value.dtype == jnp.float64
    assert cls.__symcon_leaves__[0][0] == "graupel/kcau"
