"""FieldBuffer protocol and Location/HaloState enums (architecture §2.2)."""

from __future__ import annotations

import numpy as np

from symcon.core.typing import FieldBuffer, HaloState, Location


def test_numpy_ndarray_is_a_fieldbuffer() -> None:
    assert isinstance(np.zeros((2, 3)), FieldBuffer)


def test_plain_python_objects_are_not() -> None:
    assert not isinstance([1.0, 2.0], FieldBuffer)
    assert not isinstance(3.0, FieldBuffer)


def test_duck_typed_object_passes() -> None:
    class Fake:
        shape = (2,)
        dtype = np.dtype(np.float64)

        def __dlpack__(self, *, stream: int | None = None) -> object:
            raise NotImplementedError

        def __dlpack_device__(self) -> tuple[int, int]:
            return (2, 0)  # kDLCUDA

    assert isinstance(Fake(), FieldBuffer)


def test_enum_values_match_the_architecture_table() -> None:
    assert [m.value for m in Location] == ["cell", "edge", "vertex", "scalar"]
    assert [m.value for m in HaloState] == ["valid", "dirty"]
    # str-valued enums: attrs comparisons with plain strings work
    assert Location.CELL == "cell"
    assert HaloState.VALID == "valid"
    assert str(Location.EDGE) == "edge"
    assert str(HaloState.DIRTY) == "dirty"
