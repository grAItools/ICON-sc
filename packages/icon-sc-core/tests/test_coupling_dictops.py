"""dict_axpy / dict_fma unit tests (SPEC S04, PLAN item 3)."""

from __future__ import annotations

from typing import Any

import numpy as np

from icon_sc.core.coupling import dict_axpy, dict_fma
from icon_sc.core.state.dataarray import make_dataarray
from icon_sc.core.testing import assert_allclose
from icon_sc.core.time import datetime

_DIMS = ["cell", "height"]


def _field(name: str, values: Any) -> Any:
    return make_dataarray(
        np.asarray(values, dtype=np.float64).reshape(1, -1),
        name=name,
        dims=_DIMS,
        units="m s-1",
        location="cell",
    )


def test_dict_axpy_updates_in_place_over_shared_fields() -> None:
    y = {"time": datetime(2000, 1, 1), "a": _field("a", [1.0, 2.0]), "b": _field("b", [3.0])}
    x = {"time": datetime(2000, 1, 2), "a": _field("a", [10.0, 20.0]), "c": _field("c", [7.0])}
    buffer_a = y["a"].data
    dict_axpy(y, 0.5, x)  # default fields: shared keys minus "time"
    assert y["a"].data is buffer_a  # buffer identity preserved (vault property)
    assert_allclose(y["a"].data, [[6.0, 12.0]], rtol=0.0, names="a")
    assert_allclose(y["b"].data, [[3.0]], rtol=0.0, names="b untouched")
    assert y["time"] == datetime(2000, 1, 1)  # time never combined


def test_dict_axpy_explicit_fields() -> None:
    y = {"a": _field("a", [1.0]), "b": _field("b", [1.0])}
    x = {"a": _field("a", [1.0]), "b": _field("b", [1.0])}
    dict_axpy(y, -2.0, x, fields=["b"])
    assert_allclose(y["a"].data, [[1.0]], rtol=0.0, names="a untouched")
    assert_allclose(y["b"].data, [[-1.0]], rtol=0.0, names="b")


def test_dict_fma_returns_fresh_buffers() -> None:
    base = {"a": _field("a", [1.0, 2.0])}
    increment = {"a": _field("a", [10.0, 10.0]), "extra": _field("extra", [0.0])}
    result = dict_fma(base, increment, 0.1)
    assert set(result) == {"a"}  # shared fields only
    assert_allclose(result["a"], [[2.0, 3.0]], rtol=1e-15, names="fma")
    # Out-of-place: neither input buffer was written.
    assert_allclose(base["a"].data, [[1.0, 2.0]], rtol=0.0, names="base untouched")
    assert result["a"] is not base["a"].data


def test_dict_fma_explicit_fields() -> None:
    base = {"a": _field("a", [1.0]), "b": _field("b", [5.0])}
    increment = {"a": _field("a", [1.0]), "b": _field("b", [1.0])}
    result = dict_fma(base, increment, 2.0, fields=["b"])
    assert set(result) == {"b"}
    assert_allclose(result["b"], [[7.0]], rtol=0.0, names="b")
