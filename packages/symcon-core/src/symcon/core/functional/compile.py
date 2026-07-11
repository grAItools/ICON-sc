"""Functional compile: composition → pure ``step_fn`` + ``scan_window`` (§8.5, SPEC S10).

``functional_compile(composition, state, timestep=...)`` is the F-tier consumer
of the composition walk (the same ``visit(plan_builder)`` double-dispatch the
S05 plan compiler uses): instead of an imperative op list it emits a pure JAX
function over explicit PyTrees,

    step_fn: (StateTree, ParamTree, StaticArgs) -> StateTree      # one Δt, traced
    window  = scan_window(step_fn, n_steps, remat="per_step")     # lax.scan + checkpoint

The semantic mapping is mechanical (§8.5): sequential updates become functional
updates (memory recovered by ``donate_argnums`` under ``jit``); cadence wrappers
become carry (cached output + last-fire phase) selected by ``jnp.where`` on a
carried step counter — the trace is static across step signatures; monitors and
``time`` are outside the trace.

**Component protocol** (§8.6 ``native``/``custom``): a compilable component
provides a pure ``functional_call(inputs, params, dt=...) -> outputs`` — inputs
keyed by its contract names, outputs the flat union of its output dicts —
co-located with its imperative kernel and drawing on the same scheme-constants
module, plus ``functional_params() -> {name: default}`` for its ``params``
declarations. Components whose contracts declare no ``native``/``custom``
output are ``none`` under the differentiability contract: per differentiated
region the composition-time ``policy`` is ``"error"`` (default) or
``"stop_gradient"`` — explicit, warned, and stamped into provenance. Gradient
truncation is never silent.
"""

from __future__ import annotations

import dataclasses
import warnings
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from datetime import timedelta
from typing import Any

import jax
import numpy as np

from symcon.core.contracts.properties import Differentiable, PropertySpec
from symcon.core.functional.pytree import build_param_tree, build_state_tree, mapping_of, tree_of

__all__ = [
    "FunctionalCompileError",
    "FunctionalProgram",
    "StaticArgs",
    "functional_compile",
    "scan_window",
]

#: The step-counter carry leaf (owned by the compiler, not by any component).
_STEP_LEAF = "fstep"
#: Carry namespace prefix (explicit carry per §8.5, keyed by node position).
_CARRY_PREFIX = "fcarry"

#: One lowered operation: reads/writes the per-step name → array environment.
_Op = Callable[[MutableMapping[str, Any], Mapping[str, Any], "StaticArgs"], None]

_POLICIES = ("error", "stop_gradient")


class FunctionalCompileError(Exception):
    """The composition cannot be lowered to a pure function (names the node)."""


@dataclasses.dataclass(frozen=True)
class StaticArgs:
    """Per-call static/scalar arguments of the pure step (frozen interface, SPEC S10).

    ``dt`` must equal the ``timestep`` the program was compiled against: cadence
    periods are folded into the trace as step counts at compile time.
    """

    dt: float


jax.tree_util.register_dataclass(StaticArgs, data_fields=["dt"], meta_fields=[])


@dataclasses.dataclass(frozen=True)
class FunctionalProgram:
    """The compiled F-tier program (frozen interface, SPEC S10).

    ``step_fn(state, params, static) -> state`` is pure and traced; ``state`` /
    ``params`` are instances of the generated ``state_type`` / ``param_type``
    PyTrees; ``provenance`` stamps every composition-time decision (cadence
    folds, ``stop_gradient`` truncations, freezes) — never silent (§8.6).
    """

    step_fn: Callable[[Any, Any, StaticArgs], Any]
    state: Any
    params: Any
    static: StaticArgs
    state_type: type
    param_type: type
    carry_names: tuple[str, ...]
    provenance: tuple[str, ...]


def _dim_sizes(state: Mapping[str, Any]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for name, value in state.items():
        if name == "time":
            continue
        dims = getattr(value, "dims", None)
        shape = getattr(value, "shape", None)
        if dims is None or shape is None:
            continue
        for dim, size in zip(dims, shape, strict=True):
            if sizes.setdefault(str(dim), int(size)) != int(size):
                raise FunctionalCompileError(
                    f"state dim {dim!r} has inconsistent lengths "
                    f"({sizes[str(dim)]} vs {int(size)}, found at {name!r})."
                )
    return sizes


def _name_of(node: Any) -> str:
    return str(getattr(node, "name", type(node).__name__))


def _declared_axis(component: Any) -> Differentiable:
    """The component's differentiability axis: the strongest declared output axis."""
    parsed: Mapping[str, Mapping[str, PropertySpec]] = component.parsed_properties
    axes = {
        spec.differentiable
        for dict_name in component.output_dict_names
        for spec in parsed.get(dict_name, {}).values()
    }
    for axis in (Differentiable.CUSTOM, Differentiable.NATIVE):
        if axis in axes:
            return axis
    return Differentiable.NONE


class _FunctionalCompiler:
    """Composition walk → op list + carry/param/zero-seed collection."""

    def __init__(
        self,
        state: Mapping[str, Any],
        timestep: timedelta,
        policy: str,
    ) -> None:
        self._state = state
        self._timestep = timestep
        self._policy = policy
        self._sizes = _dim_sizes(state)
        self.ops: list[_Op] = []
        self.carry_init: dict[str, Any] = {}
        self.seeded: dict[str, Any] = {}  # declared outputs absent from the state
        self.params: dict[str, float] = {}
        self.provenance: list[str] = []
        self._param_owner: dict[str, Any] = {}
        self._prefix: str = _CARRY_PREFIX

    # -- dispatch ---------------------------------------------------------------------

    def lower(self, node: Any, prefix: str) -> None:
        visit = getattr(node, "visit", None)
        if visit is None or not callable(visit):
            raise FunctionalCompileError(
                f"{_name_of(node)!r} does not implement the visit(plan_builder) "
                f"protocol; it cannot be functionally compiled."
            )
        previous = self._prefix
        self._prefix = prefix
        try:
            visit(self)
        finally:
            self._prefix = previous

    # -- PlanBuilder hooks (§8.2 protocol, F-tier consumer) ------------------------------

    def visit_component(self, component: Any) -> None:
        self.ops.append(self._component_op(component))

    def visit_concurrent_coupling(self, coupling: Any) -> None:
        # Serial policy (S04): members run in declared order, each sees its
        # predecessors' outputs; same-field tendency contributions are summed.
        written: set[str] = set()
        for index, member in enumerate(coupling.components):
            accumulate = {
                name
                for name in member.parsed_properties.get("tendency_properties", {})
                if name in written
            }
            self.lower(_Accumulating(member, accumulate), f"{self._prefix}/component{index}")
            written.update(member.parsed_properties.get("tendency_properties", {}))

    def visit_sequential_update_splitting(self, federation: Any) -> None:
        for index, stepper in enumerate(federation.sections):
            if tuple(getattr(stepper, "output_dict_names", ())) != (
                "diagnostic_properties",
                "output_properties",
            ):
                raise FunctionalCompileError(
                    f"{_name_of(federation)!r}: section {index} "
                    f"({_name_of(stepper)!r}) is not a bare Stepper; scheme-wrapped "
                    f"sections are outside the S10 functional slice."
                )
            self.lower(stepper, f"{self._prefix}/section{index}")

    def visit_calling_frequency(self, wrapper: Any) -> None:
        component = wrapper.component
        period = wrapper.period_for(self._timestep)
        multiple = period // self._timestep
        if multiple * self._timestep != period:  # pragma: no cover - period_for guarantees
            raise FunctionalCompileError(
                f"{_name_of(wrapper)!r}: effective period {period!r} is not a "
                f"multiple of the loop timestep {self._timestep!r}."
            )
        # Phase: the last-fire *step index* relative to the bound state's clock
        # (-inf = never fired -> fires at step 0, sympl's first-call rule).
        last = wrapper.last_update_time
        t0 = self._state.get("time")
        if last is None:
            last_fire = -np.inf
        else:
            if t0 is None:
                raise FunctionalCompileError(
                    f"{_name_of(wrapper)!r} carries a firing phase but the state "
                    f"has no 'time' entry to anchor it."
                )
            last_fire = (last - t0) / self._timestep
        phase_key = f"{self._prefix}/calling_frequency/last_update_time"
        self.carry_init[phase_key] = np.asarray(float(last_fire))

        # Cached output carry: one leaf per declared output, restored from the
        # wrapper's live cache (restart surface) when present, else zeros.
        restart = wrapper.restart_state()
        cache_keys: list[tuple[str, str]] = []  # (env name, carry key)
        parsed = component.parsed_properties
        for index, dict_name in enumerate(component.output_dict_names):
            for name, spec in parsed.get(dict_name, {}).items():
                carry_key = f"{self._prefix}/calling_frequency/cache/{index}/{name}"
                cached = restart.get(f"calling_frequency/cache/{index}/{name}")
                self.carry_init[carry_key] = (
                    np.asarray(cached.data, dtype=np.float64)
                    if cached is not None
                    else self._zeros(spec, wrapper)
                )
                cache_keys.append((name, carry_key))

        inner_op = self._component_op(component)
        self.provenance.append(
            f"cadence:{_name_of(wrapper)}:every {multiple} step(s), "
            f"phase {'unset' if last is None else last_fire}"
        )

        def op(env: MutableMapping[str, Any], params: Mapping[str, Any], static: StaticArgs) -> None:
            import jax.numpy as jnp

            step = env[_STEP_LEAF]
            last_fired = env[phase_key]
            fire = (step - last_fired) >= float(multiple)
            # Recompute-vs-cached select (§8.5): both branches live in the trace,
            # the cache being carry keeps it static across step signatures.
            scratch: dict[str, Any] = dict(env)
            inner_op(scratch, params, static)
            for name, carry_key in cache_keys:
                value = jnp.where(fire, scratch[name], env[carry_key])
                env[carry_key] = value
                env[name] = value
            env[phase_key] = jnp.where(fire, step, last_fired)

        self.ops.append(op)

    # -- unsupported nodes (S10 slice) ----------------------------------------------------

    def visit_dynamical_core(self, core: Any) -> None:
        self._unsupported(core)

    def visit_tendency_stepper(self, stepper: Any) -> None:
        self._unsupported(stepper)

    def visit_sequential_tendency_stepper(self, stepper: Any) -> None:
        self._unsupported(stepper)

    def visit_parallel_splitting(self, federation: Any) -> None:
        self._unsupported(federation)

    def visit_sequential_tendency_splitting(self, federation: Any) -> None:
        self._unsupported(federation)

    def visit_ssus(self, federation: Any) -> None:
        self._unsupported(federation)

    def visit_subcycle(self, wrapper: Any) -> None:
        self._unsupported(wrapper)

    def visit_scaling_wrapper(self, wrapper: Any) -> None:
        self._unsupported(wrapper)

    def _unsupported(self, node: Any) -> None:
        raise FunctionalCompileError(
            f"{_name_of(node)!r} ({type(node).__name__}) is outside the S10 "
            f"functional slice; supported: components, ConcurrentCoupling, "
            f"SequentialUpdateSplitting of bare Steppers, CallingFrequency."
        )

    # -- component lowering ---------------------------------------------------------------

    def _zeros(self, spec: PropertySpec, owner: Any) -> Any:
        try:
            shape = tuple(self._sizes[dim] for dim in spec.dims)
        except KeyError as exc:
            raise FunctionalCompileError(
                f"{_name_of(owner)!r}: cannot infer the length of dim "
                f"{exc.args[0]!r} for field {spec.name!r} from the state."
            ) from None
        return np.zeros(shape, dtype=np.float64)

    def _component_op(self, component: Any, accumulate: frozenset[str] = frozenset()) -> _Op:
        name = _name_of(component)
        fn = getattr(component, "functional_call", None)
        if fn is None:
            raise FunctionalCompileError(
                f"component {name!r} provides no functional core "
                f"(functional_call); it cannot enter a differentiated region."
            )
        axis = _declared_axis(component)
        truncate = False
        if axis is Differentiable.NONE:
            if self._policy == "error":
                raise FunctionalCompileError(
                    f"component {name!r} is differentiable: 'none' under the "
                    f"§8.6 contract; compile with policy='stop_gradient' to "
                    f"truncate its gradients explicitly."
                )
            truncate = True
            warnings.warn(
                f"functional_compile: gradients are truncated (stop_gradient) "
                f"at component {name!r} (differentiable: 'none').",
                UserWarning,
                stacklevel=2,
            )
            self.provenance.append(f"stop_gradient:{name}")

        # params declarations (§8.6): defaults from functional_params(), the
        # per-field `params` spec names must be covered by them.
        declared = getattr(component, "functional_params", None)
        defaults: Mapping[str, float] = declared() if declared is not None else {}
        parsed: Mapping[str, Mapping[str, PropertySpec]] = component.parsed_properties
        spec_params = {
            param
            for dict_name in component.output_dict_names
            for spec in parsed.get(dict_name, {}).values()
            for param in spec.params
        }
        unknown = spec_params - set(defaults)
        if unknown:
            raise FunctionalCompileError(
                f"component {name!r} declares params {sorted(unknown)!r} on its "
                f"contracts but functional_params() does not provide them."
            )
        param_keys: dict[str, str] = {}
        for short, value in defaults.items():
            full = f"{name}/{short}"
            owner = self._param_owner.get(full)
            if owner is None:
                self._param_owner[full] = component
                self.params[full] = float(value)
            elif owner is not component:
                raise FunctionalCompileError(
                    f"two distinct components share the name {name!r}; "
                    f"ParamTree keys would collide on {full!r}."
                )
            param_keys[short] = full

        input_names = tuple(parsed.get("input_properties", {}))
        output_names = tuple(
            spec_name
            for dict_name in component.output_dict_names
            for spec_name in parsed.get(dict_name, {})
        )
        for dict_name in component.output_dict_names:
            for spec_name, spec in parsed.get(dict_name, {}).items():
                if spec_name not in self._state and spec_name not in self.seeded:
                    self.seeded[spec_name] = self._zeros(spec, component)

        def op(env: MutableMapping[str, Any], params: Mapping[str, Any], static: StaticArgs) -> None:
            import jax.numpy as jnp

            try:
                inputs = {field: env[field] for field in input_names}
            except KeyError as exc:
                raise FunctionalCompileError(
                    f"component {name!r} consumes {exc.args[0]!r}, which is neither "
                    f"in the state nor produced upstream in the composition."
                ) from None
            comp_params = {short: params[full] for short, full in param_keys.items()}
            outputs = fn(inputs, comp_params, dt=static.dt)
            missing = [field for field in output_names if field not in outputs]
            if missing:
                raise FunctionalCompileError(
                    f"component {name!r}: functional_call returned no value for "
                    f"declared output(s) {missing!r}."
                )
            for field in output_names:
                value = outputs[field]
                if truncate:
                    value = jax.lax.stop_gradient(value)
                if field in accumulate:
                    env[field] = env[field] + value
                else:
                    env[field] = jnp.asarray(value)

        return op


class _Accumulating:
    """Marks a coupling member whose repeated tendency fields must accumulate."""

    def __init__(self, member: Any, accumulate: set[str]) -> None:
        self._member = member
        self._accumulate = frozenset(accumulate)

    def visit(self, plan_builder: _FunctionalCompiler) -> None:
        member = self._member
        if isinstance(member, _Accumulating):  # pragma: no cover - defensive
            raise FunctionalCompileError("nested accumulation markers")
        inner_visit = getattr(member, "visit", None)
        if inner_visit is None:
            raise FunctionalCompileError(
                f"{_name_of(member)!r} does not implement the visit protocol."
            )
        if not self._accumulate:
            inner_visit(plan_builder)
            return
        # Only plain components can double-publish a tendency field in S10.
        plan_builder.ops.append(plan_builder._component_op(member, self._accumulate))


def functional_compile(
    composition: Any,
    state: Mapping[str, Any],
    *,
    timestep: timedelta,
    policy: str = "error",
) -> FunctionalProgram:
    """Lower a composition to a pure ``step_fn`` over explicit PyTrees (SPEC S10).

    ``composition`` is one composition node or an ordered sequence of nodes (the
    §5.1 loop-body order — e.g. the SCM preset's ``(slow, core, fast)``); every
    node lowers through the same ``visit(plan_builder)`` protocol the S05 plan
    compiler consumes. ``state`` is the schema-representative boundary state the
    trees are generated from. ``policy`` governs ``differentiable: 'none'``
    components per §8.6: ``"error"`` (default) or ``"stop_gradient"``.
    """
    if policy not in _POLICIES:
        raise ValueError(f"policy must be one of {_POLICIES!r}, got {policy!r}.")
    if timestep <= timedelta(0):
        raise ValueError(f"timestep must be positive, got {timestep!r}.")
    if not jax.config.jax_enable_x64:
        warnings.warn(
            "functional_compile: jax is running in fp32; fp64 is the default "
            "for gradient work (§8.6) — jax.config.update('jax_enable_x64', True).",
            UserWarning,
            stacklevel=2,
        )

    nodes: Sequence[Any]
    if isinstance(composition, Sequence) and not isinstance(composition, (str, bytes)):
        nodes = tuple(composition)
    else:
        nodes = (composition,)
    if not nodes:
        raise ValueError("functional_compile: at least one composition node is required.")

    compiler = _FunctionalCompiler(state, timestep, policy)
    compiler.provenance.append(f"policy={policy}")
    compiler.provenance.append("frozen:time/monitors outside the trace")
    for index, node in enumerate(nodes):
        compiler.lower(node, f"{_CARRY_PREFIX}/{index}")

    if _STEP_LEAF in state:
        raise FunctionalCompileError(
            f"state field {_STEP_LEAF!r} collides with the compiler's step counter."
        )
    extra: dict[str, Any] = dict(compiler.seeded)
    extra.update(compiler.carry_init)
    extra[_STEP_LEAF] = np.asarray(0.0)
    state_type, state_tree = build_state_tree(state, extra)
    param_type, param_tree = build_param_tree(compiler.params)
    static = StaticArgs(dt=timestep.total_seconds())
    ops = tuple(compiler.ops)

    def step_fn(state_in: Any, params_in: Any, static_in: StaticArgs) -> Any:
        env: dict[str, Any] = dict(mapping_of(state_in))
        params = mapping_of(params_in)
        for op in ops:
            op(env, params, static_in)
        env[_STEP_LEAF] = env[_STEP_LEAF] + 1.0
        return tree_of(state_type, env)

    return FunctionalProgram(
        step_fn=step_fn,
        state=state_tree,
        params=param_tree,
        static=static,
        state_type=state_type,
        param_type=param_type,
        carry_names=tuple(sorted((*compiler.carry_init, _STEP_LEAF))),
        provenance=tuple(compiler.provenance),
    )


def scan_window(
    step_fn: Callable[[Any, Any, StaticArgs], Any],
    n_steps: int,
    *,
    remat: str | None = "per_step",
    ys_of: Callable[[Any], Any] | None = None,
) -> Callable[..., Any]:
    """A multi-step window over ``step_fn``: ``lax.scan`` + checkpoint policy (§8.5).

    Returns ``window(state, params, static)``. ``remat="per_step"`` wraps the
    step in ``jax.checkpoint`` (reverse-mode memory ≈ one extra forward, §8.7);
    ``remat=None`` stores all activations. ``ys_of`` optionally maps each
    post-step state to a per-step observable; the window then returns
    ``(final_state, stacked_ys)`` instead of ``final_state``.
    """
    if n_steps < 1:
        raise ValueError(f"n_steps must be >= 1, got {n_steps}.")
    if remat not in (None, "per_step"):
        raise ValueError(f"remat must be None or 'per_step', got {remat!r}.")

    def window(state: Any, params: Any, static: StaticArgs) -> Any:
        def one_step(carry: Any, params_in: Any) -> Any:
            return step_fn(carry, params_in, static)

        step = jax.checkpoint(one_step) if remat == "per_step" else one_step

        def body(carry: Any, _: Any) -> tuple[Any, Any]:
            advanced = step(carry, params)
            return advanced, (ys_of(advanced) if ys_of is not None else None)

        final, ys = jax.lax.scan(body, state, xs=None, length=n_steps)
        return (final, ys) if ys_of is not None else final

    return window
