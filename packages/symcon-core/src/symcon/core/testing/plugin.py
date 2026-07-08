"""pytest plugin: marker registration, hardware-based skips, backend fixture stub.

Loaded via ``pytest_plugins = ("symcon.core.testing.plugin",)`` in the repo-root
conftest. The ``backend`` values are plain strings until S02 gives them meaning.
"""

from __future__ import annotations

from typing import Union

import pytest

from symcon.core.testing import register_markers

#: Backend parametrization stub (PLAN S01 item 4). ``gtfn_gpu`` carries the gpu marker
#: so it skips cleanly on machines without a CUDA device.
BACKEND_PARAMS: tuple[Union[str, "pytest.ParameterSet"], ...] = (
    "embedded",
    "gtfn_cpu",
    pytest.param("gtfn_gpu", marks=pytest.mark.gpu),
)


def pytest_configure(config: pytest.Config) -> None:
    register_markers(config)


def _gpu_available() -> bool:
    try:
        import cupy  # noqa: PLC0415

        return bool(cupy.cuda.runtime.getDeviceCount() > 0)
    except Exception:  # ImportError or any CUDA runtime error
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """gpu-marked tests must skip, not fail, without a device (AGENTS.md).

    mpi-marked tests are handled by pytest-mpi (skipped unless run ``--with-mpi``).
    """
    if _gpu_available():
        return
    skip_gpu = pytest.mark.skip(reason="no CUDA device available")
    for item in items:
        if "gpu" in item.keywords:
            item.add_marker(skip_gpu)


@pytest.fixture(params=BACKEND_PARAMS)
def backend(request: pytest.FixtureRequest) -> str:
    """Backend name the test should build/run against (string stub until S02)."""
    return str(request.param)
