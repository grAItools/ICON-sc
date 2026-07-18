"""Backend parametrization stub: values are strings until S02 gives them meaning."""

from __future__ import annotations

import pytest

from icon_sc.core.testing.plugin import BACKEND_PARAMS


def test_backend_is_a_known_string(backend: str) -> None:
    assert backend in {"embedded", "gtfn_cpu", "gtfn_gpu"}


def test_cpu_backends_always_parametrized() -> None:
    plain = {p for p in BACKEND_PARAMS if isinstance(p, str)}
    assert plain == {"embedded", "gtfn_cpu"}


def test_gpu_backend_carries_gpu_marker() -> None:
    gpu_params = [p for p in BACKEND_PARAMS if not isinstance(p, str)]
    assert len(gpu_params) == 1
    (param,) = gpu_params
    assert isinstance(param, type(pytest.param("x")))
    assert param.values == ("gtfn_gpu",)
    assert any(mark.name == "gpu" for mark in param.marks)
