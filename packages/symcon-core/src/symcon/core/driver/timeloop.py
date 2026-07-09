"""Plain T0 time loop (SPEC S03): advance ``state["time"]``, call monitors.

Deliberately dumb — a ``for`` loop over a user-supplied step function, per the
sympl paper's run-script pattern (Fig. 2). No negotiation, no plan, no cadence
logic: those belong to ``ctx.timeloop()`` (S05). T0 compositions put all physics
into ``step``; this helper only owns time advancement and monitor calls.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import timedelta
from typing import Any

from symcon.core.components.base import Monitor

__all__ = ["timeloop"]

#: One Δt of model physics: ``(state, timestep) -> state`` (may mutate or replace).
StepFn = Callable[[dict[str, Any], timedelta], Mapping[str, Any]]


def timeloop(
    state: Mapping[str, Any],
    step: StepFn,
    *,
    timestep: timedelta,
    n_steps: int | None = None,
    until: timedelta | None = None,
    monitors: Iterable[Monitor] = (),
) -> dict[str, Any]:
    """Run ``step`` for ``n_steps`` (or ``until``, an exact multiple of ``timestep``).

    Per iteration: ``state = step(state, timestep)``, then ``state["time"]`` is
    advanced by ``timestep``, then every monitor stores the advanced state. The
    input mapping is not mutated (a shallow copy is threaded); the final state is
    returned.
    """
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
    if "time" not in state:
        raise KeyError("state has no 'time' entry; the loop cannot advance it.")

    monitor_list = tuple(monitors)
    current = dict(state)
    for _ in range(n_steps):
        current = dict(step(current, timestep))
        current["time"] = current["time"] + timestep
        for monitor in monitor_list:
            monitor.store(current)
    return current
