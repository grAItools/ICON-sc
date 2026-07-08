"""Backend parametrization stub: values are strings until S02 gives them meaning."""

from __future__ import annotations

SEEN: set[str] = set()


def test_backend_is_a_known_string(backend: str) -> None:
    assert backend in {"embedded", "gtfn_cpu", "gtfn_gpu"}
    SEEN.add(backend)


def test_cpu_backends_always_parametrized() -> None:
    # Runs after the parametrized test within this module (pytest keeps file order).
    # gtfn_gpu is absent without a CUDA device (gpu marker -> clean skip).
    assert {"embedded", "gtfn_cpu"} <= SEEN
