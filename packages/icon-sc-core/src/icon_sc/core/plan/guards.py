"""Plan staleness guards and debug renegotiation (architecture §8.2, SPEC S05).

A plan is valid for one ``(composition, schema, ctx)`` triple, enforced by:

- the vault ``schema_hash`` + ``epoch`` recorded at materialization — any
  out-of-band mutation through the façade (field rebind/delete) bumps the epoch
  and the next ``run_step`` raises :class:`StalePlanError` instead of silently
  binding dead buffers;
- ``plan_hash`` — a stable content hash over the canonical serialization of the
  symbolic op lists (names and slots, never object ids), the schema, and the
  context configuration; identical inputs hash identically across processes;
- debug renegotiation — :func:`renegotiate_and_diff` re-runs the full bind
  against the live composition every N steps and diffs the result against the
  bound plan, raising :class:`PlanDriftError` on any divergence
  (``ctx.timeloop(..., debug_renegotiate_every=N)`` wires it into the loop).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from icon_sc.core.contracts.checkers import StateSchema

if TYPE_CHECKING:
    from icon_sc.core.context import ComputeContext
    from icon_sc.core.plan.bind import ExecutionPlan

__all__ = [
    "PlanCompileError",
    "PlanDriftError",
    "StalePlanError",
    "renegotiate_and_diff",
    "schema_fingerprint",
]


class PlanCompileError(ValueError):
    """The composition cannot be compiled to an execution plan (bind-time)."""


class StalePlanError(RuntimeError):
    """The vault mutated out of band since the plan was bound (§8.2 guard)."""


class PlanDriftError(RuntimeError):
    """Debug renegotiation produced a plan differing from the bound one."""


def schema_fingerprint(schema: StateSchema) -> str:
    """Stable content hash of a :class:`StateSchema` (sorted canonical text)."""
    parts = []
    for name in sorted(schema.fields):
        field = schema.fields[name]
        parts.append(
            f"{name}|{','.join(field.dims)}|{field.units}|{field.dtype.str}"
            f"|{field.device}|{field.location.value if field.location else ''}"
        )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def renegotiate_and_diff(
    plan: ExecutionPlan,
    composition: Any,
    ctx: ComputeContext,
) -> None:
    """Re-run the full negotiation and diff against ``plan`` (debug builds, §8.2).

    Binds the live ``composition`` afresh against the plan's schema and context
    and compares plan hashes and the canonical op serialization. Returns silently
    when the plans agree.

    Raises:
        PlanDriftError: Naming the first divergence between the re-bound plan and
            ``plan``.
    """
    from icon_sc.core.plan.bind import ExecutionPlan

    fresh = ExecutionPlan.bind(composition, plan.schema, ctx)
    if fresh.plan_hash == plan.plan_hash:
        return
    bound_text = plan.describe().splitlines()
    fresh_text = fresh.describe().splitlines()
    for line, (old, new) in enumerate(zip(bound_text, fresh_text, strict=False)):
        if old != new:
            raise PlanDriftError(
                f"renegotiation drift at plan line {line}:\n  bound: {old}\n  fresh: {new}"
            )
    raise PlanDriftError(
        f"renegotiation drift: op counts differ "
        f"(bound {len(bound_text)} lines, fresh {len(fresh_text)} lines)."
    )
