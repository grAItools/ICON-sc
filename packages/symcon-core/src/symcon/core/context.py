"""``ComputeContext`` with the S05 execution-tier surface (architecture §5.2, §8.2).

The one object threaded through component construction. It carries the
**backend** — an opaque name string, or (since S07, the first real gt4py
component) a :class:`~symcon.core.ingress.gt4py.Backend` object bundling the
gt4py program processor and allocator — the **strict-mode flag** (§2.4), an
**allocator** choosing numpy or cupy, and — since S05 — the **execution tier**
(``"interpret"`` = T0 reference dispatch, ``"plan"`` = the §8.2 bind + T1
interpreter) plus the bound loop ``timestep`` the plan compiler treats as a
bind-time constant.

``ctx.timeloop(state, composition, ...)`` is the canonical entry of §5.1's run
script: under ``tier="interpret"`` it is the plain T0 loop over the composed
step; under ``tier="plan"`` it performs the bind (negotiation happens exactly
once) and interprets the frozen plan — nothing sympl-shaped executes per step.

Components allocate their private and output fields through the context; nothing
else in symcon touches devices directly (§5.2).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterable, Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

import numpy as np

from symcon.core.ingress.gt4py import Backend
from symcon.core.typing import FieldBuffer

if TYPE_CHECKING:
    from symcon.core.components.base import Monitor

__all__ = ["Allocator", "ComputeContext"]

#: Backend-name substrings that select the cupy allocator on the opaque-string
#: path (a :class:`~symcon.core.ingress.gt4py.Backend` object carries its own
#: allocator instead, S07).
_GPU_MARKERS: tuple[str, ...] = ("gpu", "cuda")

#: The execution tiers of §8.3 available in this slice.
_TIERS: tuple[str, ...] = ("interpret", "plan")


@runtime_checkable
class Allocator(Protocol):
    """Minimal allocator protocol: uninitialized device buffers by shape/dtype."""

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer: ...


class _NumpyAllocator:
    """Host allocator (numpy)."""

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer:
        return np.empty(shape, dtype=dtype)


class _CupyAllocator:
    """CUDA device allocator (cupy); constructing it requires cupy."""

    def __init__(self) -> None:
        import cupy

        self._cupy = cupy

    def empty(self, shape: tuple[int, ...], dtype: Any) -> FieldBuffer:
        buffer: FieldBuffer = self._cupy.empty(shape, dtype=dtype)
        return buffer


def _resolve_steps(timestep: timedelta, n_steps: int | None, until: timedelta | None) -> int:
    if timestep <= timedelta(0):
        raise ValueError(f"timestep must be positive, got {timestep!r}.")
    if (n_steps is None) == (until is None):
        raise ValueError("give exactly one of n_steps and until.")
    if until is not None:
        n_steps = until // timestep
        if n_steps * timestep != until:
            raise ValueError(
                f"until={until!r} is not an integer multiple of timestep={timestep!r}."
            )
    assert n_steps is not None
    if n_steps < 0:
        raise ValueError(f"n_steps must be non-negative, got {n_steps}.")
    return n_steps


@dataclasses.dataclass(frozen=True)
class ComputeContext:
    """Compute context (frozen interface, SPEC S03; S05 adds ``tier``/``timestep``).

    ``ComputeContext(backend, strict=True, allocator=..., tier=..., timestep=...)``
    — ``backend`` is an opaque string (``embedded``/``gtfn_cpu``/``gtfn_gpu``)
    or, since S07, a :class:`~symcon.core.ingress.gt4py.Backend` object; when
    ``allocator`` is not given it is derived from the backend (a ``Backend``
    contributes its own allocator; a name string selects cupy for GPU-flavoured
    backends, numpy otherwise). ``strict`` is the §2.4 strict-mode flag consumed
    by the dynamic checkers on every component call.

    ``tier`` selects the execution tier of :meth:`timeloop` (§8.3): T0
    ``"interpret"`` (default) or T1 ``"plan"``. ``timestep`` is the loop Δt the
    §8.2 plan compiler binds against; :meth:`timeloop` stamps it, so it is
    usually left ``None`` at construction.

    ``device`` is the DLPack device tuple of the allocator's buffers, probed once
    at construction; it is the device expectation handed to the
    :class:`~symcon.core.contracts.checkers.DynamicChecker`.
    """

    backend: str | Backend
    strict: bool = True
    allocator: Allocator | None = None
    tier: str = "interpret"
    timestep: timedelta | None = None
    device: tuple[int, int] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        if self.tier not in _TIERS:
            raise ValueError(f"tier must be one of {_TIERS!r}, got {self.tier!r}.")
        if self.allocator is None:
            if isinstance(self.backend, Backend):
                allocator: Allocator = self.backend.allocator
            else:
                gpu = any(marker in self.backend.lower() for marker in _GPU_MARKERS)
                allocator = _CupyAllocator() if gpu else _NumpyAllocator()
            object.__setattr__(self, "allocator", allocator)
        probe = self.require_allocator.empty((0,), np.float64)
        raw_device = probe.__dlpack_device__()
        object.__setattr__(self, "device", (int(raw_device[0]), int(raw_device[1])))

    @property
    def backend_name(self) -> str:
        """The backend name string (``backend`` itself on the opaque-string path)."""
        return self.backend if isinstance(self.backend, str) else self.backend.name

    @property
    def require_allocator(self) -> Allocator:
        """The resolved allocator (never ``None`` after construction)."""
        assert self.allocator is not None  # resolved in __post_init__
        return self.allocator

    # -- the §5.1 run-script entry (S05) ------------------------------------------------

    def timeloop(
        self,
        state: Mapping[str, Any],
        composition: Any,
        *,
        timestep: timedelta,
        n_steps: int | None = None,
        until: timedelta | None = None,
        monitors: Iterable[Monitor] = (),
        debug_renegotiate_every: int | None = None,
    ) -> dict[str, Any]:
        """Run ``composition`` for ``n_steps`` (or ``until``) under this tier.

        ``composition`` is any Stepper-shaped component — ``(state, timestep, *,
        out=None) -> (diagnostics, new_state)`` — including federations, wrappers
        and dynamical cores. Per step the state is advanced by the composition,
        ``time`` moves by ``timestep``, then monitors store the advanced state;
        the final state (diagnostics included) is returned as a plain dict.

        Under ``tier="plan"`` the bind (§8.2 negotiation) happens **once** at
        entry — the loop body is ``plan.run_step(vault, i)`` on the frozen plan
        — and ``debug_renegotiate_every=N`` re-runs the negotiation every N
        steps, diffing against the bound plan (raises
        :class:`~symcon.core.plan.guards.PlanDriftError` on drift). Under
        ``tier="interpret"`` the same composition runs with full T0 per-call
        semantics (the reference the SPEC's T0≡T1 equivalence is stated
        against).
        """
        n = _resolve_steps(timestep, n_steps, until)
        if "time" not in state:
            raise KeyError("state has no 'time' entry; the loop cannot advance it.")
        monitor_list = tuple(monitors)

        if self.tier == "interpret":
            call = cast("Callable[..., Any]", composition)
            current: dict[str, Any] = dict(state)
            for _ in range(n):
                diagnostics, new_state = call(current, timestep)
                current.update(diagnostics)
                current.update(new_state)
                current["time"] = current["time"] + timestep
                for monitor in monitor_list:
                    monitor.store(current)
            return current

        from symcon.core.contracts.checkers import StateSchema
        from symcon.core.plan.bind import ExecutionPlan
        from symcon.core.plan.guards import renegotiate_and_diff
        from symcon.core.state.vault import StateVault

        bind_ctx = dataclasses.replace(self, timestep=timestep)
        vault = StateVault.from_state(state)
        plan = ExecutionPlan.bind(composition, StateSchema.from_state(state), bind_ctx)
        facade = vault.facade()

        # Monitors are excluded from the plan (S14): they run in the host step
        # the interpreter yields to at every SegmentMarker — at T1 the
        # ``step_end`` marker closes the step's single segment; T2 will stop
        # graph replay at exactly these markers (§8.3 design note).
        def host_step(marker: Any) -> None:
            if marker.kind != "step_end":
                return
            vault.time = vault.time + timestep
            for monitor in monitor_list:
                monitor.store(facade)

        for index in range(n):
            plan.run_step(vault, index, on_segment=host_step)
            if debug_renegotiate_every is not None and (index + 1) % debug_renegotiate_every == 0:
                renegotiate_and_diff(plan, composition, bind_ctx)
        return dict(facade)
