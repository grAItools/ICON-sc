"""Op-algebra semantics (SPEC S05 plan/ops.py; docstrings are normative).

Each arithmetic op must execute exactly its documented ufunc sequence — the
assertions here are bit-exact against hand-computed numpy expressions.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from icon_sc.core import StateVault
from icon_sc.core.plan.interpreter import run_ops
from icon_sc.core.plan.ops import (
    Axpy,
    BoundCall,
    CadenceMask,
    DiffScale,
    SegmentMarker,
    Swap,
)
from icon_sc.core.testing.toys import column_state

_RNG = np.random.default_rng(20260709)


def _buf(shape: tuple[int, ...] = (3, 5)) -> np.ndarray:
    return _RNG.uniform(-2.0, 2.0, size=shape)


def test_axpy_assign_form_is_exact() -> None:
    y, x0, x1, scratch = _buf(), _buf(), _buf(), _buf()
    op = Axpy(y=y, init=(1.0, x0), terms=((0.125, x1),), scratch=scratch, divisor=1.0, tag="t")
    run_ops((op,), 0)
    np.testing.assert_array_equal(y, x0 + 0.125 * x1, strict=True)


def test_axpy_accumulate_form_is_exact() -> None:
    y, x1, scratch = _buf(), _buf(), _buf()
    expected = y + 0.3 * x1  # evaluated before the in-place op
    op = Axpy(y=y, init=None, terms=((0.3, x1),), scratch=scratch, divisor=1.0, tag="t")
    run_ops((op,), 0)
    np.testing.assert_array_equal(y, expected, strict=True)


def test_axpy_scaled_init_and_divisor_match_ssprk3_shapes() -> None:
    # phi2 = 0.75*phi + 0.25*u  and  (phi + 2*v)/3 — the ssprk3 stage forms.
    phi, u, scratch = _buf(), _buf(), _buf()
    y = np.empty_like(phi)
    run_ops(
        (Axpy(y=y, init=(0.75, phi), terms=((0.25, u),), scratch=scratch, divisor=1.0, tag="t"),),
        0,
    )
    np.testing.assert_array_equal(y, 0.75 * phi + 0.25 * u, strict=True)

    v = _buf()
    y2 = np.empty_like(phi)
    run_ops(
        (Axpy(y=y2, init=(1.0, phi), terms=((2.0, v),), scratch=scratch, divisor=3.0, tag="t"),),
        0,
    )
    np.testing.assert_array_equal(y2, (phi + 2.0 * v) / 3.0, strict=True)


def test_axpy_kary_term_order_is_sequential() -> None:
    # PS recombination: acc = psi1; acc += psi2; acc += -psi_n; ... in order.
    y = np.empty((3, 5))
    p1, p2, p3, psi_n, scratch = _buf(), _buf(), _buf(), _buf(), _buf()
    op = Axpy(
        y=y,
        init=(1.0, p1),
        terms=((1.0, p2), (-1.0, psi_n), (1.0, p3), (-1.0, psi_n)),
        scratch=scratch,
        divisor=1.0,
        tag="t",
    )
    run_ops((op,), 0)
    expected = p1.copy()
    expected += 1.0 * p2
    expected += -1.0 * psi_n
    expected += 1.0 * p3
    expected += -1.0 * psi_n
    np.testing.assert_array_equal(y, expected, strict=True)


def test_diffscale_matches_sts_forcing() -> None:
    y = np.empty((3, 5))
    prov, phi = _buf(), _buf()
    dt = 12.5
    run_ops((DiffScale(y=y, minuend=prov, subtrahend=phi, divisor=dt, tag="t"),), 0)
    np.testing.assert_array_equal(y, (prov - phi) / dt, strict=True)


def test_boundcall_invokes_the_pack() -> None:
    calls: list[tuple] = []

    def kernel(inputs: dict, outputs: dict, timestep: timedelta) -> None:
        calls.append((inputs, outputs, timestep))

    pack = ({"a": 1}, {"b": 2}, timedelta(minutes=1))
    run_ops((BoundCall(fn=kernel, args=pack, tag="t"),), 0)
    assert calls == [pack]


def test_swap_exchanges_buffers_and_bumps_generation() -> None:
    state = column_state()
    vault = StateVault.from_state(state)
    index = vault.names["air_temperature"]
    original = vault.buffers[index]
    alternate = np.zeros_like(np.asarray(original))
    store: list = [alternate]
    generation = vault.generation
    op = Swap(vault=vault, slot=index, alt_store=store, alt_index=0, tag="t")
    run_ops((op,), 0)
    assert vault.buffers[index] is alternate
    assert store[0] is original
    assert vault.generation == generation + 1
    run_ops((op,), 1)  # swap back
    assert vault.buffers[index] is original


def test_cadence_mask_guards_on_step_index() -> None:
    y, x, scratch = np.zeros((2, 2)), np.ones((2, 2)), np.empty((2, 2))
    inner = Axpy(y=y, init=None, terms=((1.0, x),), scratch=scratch, divisor=1.0, tag="t")
    mask = CadenceMask(period=3, phase=1, ops=(inner,), tag="t")
    for step in range(9):
        run_ops((mask,), step)
    np.testing.assert_array_equal(y, np.full((2, 2), 3.0), strict=True)  # steps 1, 4, 7


def test_segment_marker_is_a_noop_and_unknown_ops_raise() -> None:
    run_ops((SegmentMarker(kind="step_end", tag="t"),), 0)
    with pytest.raises(TypeError, match="unknown plan op"):
        run_ops(("not an op",), 0)  # type: ignore[arg-type]
