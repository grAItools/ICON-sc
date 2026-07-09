"""The execution-plan op algebra (architecture §8.2, SPEC S05).

Exactly six op types — ``BoundCall``, ``Swap``, ``Axpy``, ``DiffScale``,
``CadenceMask``, ``SegmentMarker`` — and nothing else. Every op is a flat
``NamedTuple`` with **pre-bound** references: buffers, callables and scalars are
resolved when the plan is materialized against a vault, so interpreting an op
performs no name lookups, no allocation and no negotiation.

The docstrings below are **normative**: the T2/T3 emitters (post-slice) treat
them as the definition of each op's semantics, and the T0≡T1 bitwise-equivalence
contract of SPEC S05 is stated against them. In particular, every arithmetic
op is specified as an exact sequence of numpy ufunc applications; emitters must
preserve that sequence (per-element evaluation order), because reordering
changes floating-point results (AGENTS.md: no reduction-order changes).

Semantics donor: tasmania's ``DataArrayDictOperator`` kernel set (``iadd`` /
``iaddsub`` / ``fma`` / fused ``sts_*_0`` stage kernels, see REFERENCES.lock)
— :class:`Axpy` is the k-ary assign-or-accumulate generalization of the first
three and :class:`DiffScale` is the ``(ψ_prv - ψⁿ)/Δt`` forcing tasmania fuses
into its first-stage kernels.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

__all__ = ["Axpy", "BoundCall", "CadenceMask", "DiffScale", "SegmentMarker", "Swap"]


class BoundCall(NamedTuple):
    """One pre-specialized component-kernel invocation: ``fn(*args)``.

    ``fn`` is the component's raw kernel entry (the bound ``array_call`` /
    ``stage_array_call`` / ``substep_array_call`` method, resolved once at
    materialization), ``args`` the frozen argument pack. For the ``array_call``
    ABI the pack is ``(inputs, outputs, timestep)`` where ``inputs``/``outputs``
    are dicts **built once at bind time** with contract field names mapping to
    pre-resolved raw buffers; buffer identity is stable across steps (vault
    contract), so the same pack is valid for the plan's lifetime. The interpreter
    performs exactly one Python call per ``BoundCall`` and never inspects the
    pack.
    """

    fn: Callable[..., None]
    args: tuple[Any, ...]
    tag: str


class Swap(NamedTuple):
    """Exchange a vault slot's buffer with a plan-held alternate buffer.

    ``vault.buffers[slot]`` and ``alt_store[alt_index]`` exchange contents and the
    vault's ``generation`` counter is bumped (``vault.note_swap()``) so the lazy
    façade rebuilds its DataArray view of the swapped slot on next access. Swaps
    carry **no data movement** — they retarget which buffer the façade exposes
    for a ping-pong field after a step whose kernels wrote the alternate buffer.
    Ops never read through the vault at runtime (references are pre-bound per
    even/odd variant, architecture §8.2), so a ``Swap`` only keeps the vault's
    public view coherent.
    """

    vault: Any  # StateVault (untyped here to keep ops.py dependency-free)
    slot: int
    alt_store: list[Any]
    alt_index: int
    tag: str


class Axpy(NamedTuple):
    """Fused k-ary axpy: ``y ← (init + Σᵢ aᵢ·xᵢ) / divisor``, exact ufunc sequence.

    Normative evaluation order (numpy ufuncs, all with ``out=``):

    1. If ``init is not None`` (*assign* form): ``np.multiply(x₀, a₀, out=y)``
       where ``init = (a₀, x₀)``. ``a₀ = 1.0`` is an exact copy (IEEE-754
       multiplication by one is the identity). If ``init is None``
       (*accumulate* form), ``y``'s current content is the seed.
    2. For each ``(aᵢ, xᵢ)`` in ``terms``, in order:
       ``np.multiply(xᵢ, aᵢ, out=scratch)`` then ``np.add(y, scratch, out=y)``.
    3. If ``divisor != 1.0``: ``np.divide(y, divisor, out=y)``.

    This reproduces bit-for-bit the T0 dict arithmetic it compiles from — e.g.
    ``phi + dt*k1`` (tendency-stepper stages), ``acc += 1.0*x`` (``dict_axpy``),
    ``0.75*phi + 0.25*(phi1 + dt*k2)`` (ssprk3) and
    ``(phi + 2.0*(phi2 + dt*k3))/3.0`` (ssprk3 final; the trailing *division*
    is why ``divisor`` exists — ``x/3.0`` and ``x*(1/3)`` differ in the last
    ulp). ``y`` may alias ``x₀`` and may appear in ``terms`` **only** when the
    aliased read happens before the first write to ``y`` under the sequence
    above (the compiler guarantees this; step 1 with ``x₀ is y`` is safe,
    later aliased terms are not emitted). ``scratch`` is a plan-owned buffer of
    ``y``'s shape/dtype; it carries no state between ops.
    """

    y: Any
    init: tuple[float, Any] | None
    terms: tuple[tuple[float, Any], ...]
    scratch: Any
    divisor: float
    tag: str


class DiffScale(NamedTuple):
    """Provisional-tendency forcing: ``y ← (minuend - subtrahend) / divisor``.

    Normative sequence: ``np.subtract(minuend, subtrahend, out=y)`` then
    ``np.divide(y, divisor, out=y)``. This is thesis eq. (2.11b)'s constant
    forcing ``(ψ_prv - ψⁿ)/Δt`` feeding every SequentialTendencyStepper
    evaluation (S04 computes the same two-op sequence per field). ``y`` must
    alias neither input.
    """

    y: Any
    minuend: Any
    subtrahend: Any
    divisor: float
    tag: str


class CadenceMask(NamedTuple):
    """Cadence guard: run ``ops`` iff ``step_index % period == phase``.

    The compiler resolves every ``CadenceMask`` into the per-signature op lists
    (one flattened list per distinct step signature, architecture §8.2), so the
    interpreter's hot path never evaluates the guard; the op type exists so a
    *symbolic* plan remains a single legible list and so debug tooling can
    interpret an unexpanded plan. When interpreted directly, the guard is one
    integer modulo — the firing rule of a fresh ``CallingFrequency`` wrapper
    under the S03 rounding-to-multiple rule (fires at step indices
    ``phase (mod period)``; see REFERENCES.lock, sympl ``UpdateFrequencyWrapper``).
    """

    period: int
    phase: int
    ops: tuple[Any, ...]
    tag: str


class SegmentMarker(NamedTuple):
    """Boundary of an exchange-free plan segment (architecture §8.3).

    A runtime no-op at T1. T2 graph capture and the T3 native driver split the
    op list at these markers: everything between two consecutive markers is
    capturable as one graph / emittable as one native block. ``kind`` labels the
    boundary reason (``"step_end"`` in S05; halo exchanges, bridge calls and
    framework seams add kinds post-slice).
    """

    kind: str
    tag: str
