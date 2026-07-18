"""Marker plumbing: gpu/mpi-marked tests must skip (not fail) without the hardware.

These placeholders also keep ``pytest -m gpu`` / ``pytest -m mpi`` collecting at least
one test each, so the CI skeleton jobs exit 0 instead of pytest's exit code 5.
"""

from __future__ import annotations

import pytest


@pytest.mark.mpi
def test_mpi_placeholder() -> None:
    # pytest-mpi skips this unless run under mpirun with --with-mpi.
    from mpi4py import MPI

    assert MPI.COMM_WORLD.Get_size() >= 1


@pytest.mark.gpu
def test_gpu_placeholder() -> None:
    # The plugin's collection hook skips this without a CUDA device.
    import cupy

    assert cupy.cuda.runtime.getDeviceCount() >= 1
