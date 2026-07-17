"""S10: functional compile of a composition — T0 equivalence, cadence-as-carry,
policy handling, ``scan_window``, donation (SPEC S10 acceptance 5/6 at toy scale)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, cast

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from icon_sc.core import (  # noqa: E402
    CallingFrequency,
    ConcurrentCoupling,
    SequentialUpdateSplitting,
    Subcycle,
)
from icon_sc.core.components.base import Stepper, TendencyComponent  # noqa: E402
from icon_sc.core.functional.compile import (  # noqa: E402
    FunctionalCompileError,
    StaticArgs,
    functional_compile,
    scan_window,
)
from icon_sc.core.functional.pytree import mapping_of  # noqa: E402
from icon_sc.core.state.dataarray import make_dataarray  # noqa: E402
from icon_sc.core.testing import assert_allclose  # noqa: E402
from icon_sc.core.time import datetime  # noqa: E402
from icon_sc.core.typing import FieldBuffer  # noqa: E402

_DIMS = ("cell", "height")
_SLOT = "tendency_of_eastward_wind"
_DT = timedelta(seconds=1)
_SLOW_DT = timedelta(seconds=3)


class ToyForcing(TendencyComponent):
    """Nonlinear forcing published to a slot (PrescribedCooling stand-in)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    tendency_properties: ClassVar[Mapping[str, Any]] = {
        _SLOT: {"dims": _DIMS, "units": "m s-2", "differentiable": "native"},
    }

    amplitude = 0.5

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        del timestep
        x = cast(Any, inputs["eastward_wind"])
        cast(Any, outputs[_SLOT])[...] = -self.amplitude * np.sin(x)

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        del dt
        return {_SLOT: -params["amplitude"] * jnp.sin(inputs["eastward_wind"])}

    def functional_params(self) -> dict[str, float]:
        return {"amplitude": self.amplitude}


class ToyApply(Stepper):
    """Forward-Euler slot consumer (ApplySlowTendencies stand-in)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        _SLOT: {"dims": _DIMS, "units": "m s-2"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1", "differentiable": "native"},
    }

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        x = cast(Any, inputs["eastward_wind"])
        cast(Any, outputs["eastward_wind"])[...] = x + timestep.total_seconds() * cast(
            Any, inputs[_SLOT]
        )

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        del params
        return {"eastward_wind": inputs["eastward_wind"] + dt * inputs[_SLOT]}


class ToyDecay(Stepper):
    """Nonlinear fast-physics stepper with a tunable rate (params declaration)."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {
            "dims": _DIMS,
            "units": "m s-1",
            "differentiable": "native",
            "params": ("rate",),
        },
    }

    rate = 0.25

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        x = cast(Any, inputs["eastward_wind"])
        cast(Any, outputs["eastward_wind"])[...] = x - timestep.total_seconds() * self.rate * x**3

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        x = inputs["eastward_wind"]
        return {"eastward_wind": x - dt * params["rate"] * x**3}

    def functional_params(self) -> dict[str, float]:
        return {"rate": self.rate}


class ToyOpaque(Stepper):
    """A stepper whose contract declares no differentiable output (§8.6 'none')."""

    input_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
    }

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None
        x = cast(Any, inputs["eastward_wind"])
        cast(Any, outputs["eastward_wind"])[...] = 0.9 * x

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        del params, dt
        return {"eastward_wind": 0.9 * inputs["eastward_wind"]}


def _state() -> dict[str, Any]:
    rng = np.random.default_rng(7)
    return {
        "time": datetime(2000, 1, 1),
        "eastward_wind": make_dataarray(
            rng.uniform(0.5, 1.5, size=(2, 3)),
            name="eastward_wind",
            dims=_DIMS,
            units="m s-1",
            location="cell",
        ),
    }


def _composition() -> tuple[ConcurrentCoupling, ToyApply, SequentialUpdateSplitting]:
    cooling = CallingFrequency(ToyForcing(name="forcing"), _SLOW_DT)
    slow = ConcurrentCoupling([cooling], name="toy_slow")
    core = ToyApply(name="apply")
    fast = SequentialUpdateSplitting([ToyDecay(name="decay")], name="toy_fast")
    return slow, core, fast


def _t0_run(n_steps: int) -> dict[str, np.ndarray]:
    slow, core, fast = _composition()
    working: dict[str, Any] = dict(_state())
    for _ in range(n_steps):
        tends, diags = slow(working, _DT)
        working.update(diags)
        working.update(tends)
        diags, new_state = core(working, _DT)
        working.update(diags)
        working.update(new_state)
        diags, new_state = fast(working, _DT)
        working.update(diags)
        working.update(new_state)
        working["time"] = working["time"] + _DT
    return {
        "eastward_wind": np.asarray(working["eastward_wind"].data),
        _SLOT: np.asarray(working[_SLOT].data),
    }


def test_t0_equivalence_including_cadence_replay() -> None:
    # 7 steps with a 3-step cadence: fires at steps 0, 3 and 6, replays between.
    n_steps = 7
    reference = _t0_run(n_steps)

    program = functional_compile(_composition(), _state(), timestep=_DT)
    state = program.state
    for _ in range(n_steps):
        state = program.step_fn(state, program.params, program.static)
    values = mapping_of(state)
    assert_allclose(
        np.asarray(values["eastward_wind"]),
        reference["eastward_wind"],
        rtol=1e-13,
        names=("F-tier", "T0"),
    )
    assert_allclose(
        np.asarray(values[_SLOT]), reference[_SLOT], rtol=1e-13, names=("F-tier slot", "T0 slot")
    )
    assert float(values["fstep"]) == n_steps
    assert any(
        prov.startswith("cadence:") and "every 3 step(s)" in prov for prov in program.provenance
    )


def test_scan_window_matches_step_loop_and_collects_ys() -> None:
    n_steps = 5
    program = functional_compile(_composition(), _state(), timestep=_DT)
    looped = program.state
    for _ in range(n_steps):
        looped = program.step_fn(looped, program.params, program.static)

    window = scan_window(
        program.step_fn, n_steps, remat="per_step", ys_of=lambda s: jnp.sum(s.eastward_wind)
    )
    final, ys = window(program.state, program.params, program.static)
    assert ys.shape == (n_steps,)
    assert_allclose(
        np.asarray(final.eastward_wind),
        np.asarray(looped.eastward_wind),
        rtol=1e-15,
        names=("scan", "loop"),
    )
    assert float(ys[-1]) == pytest.approx(float(jnp.sum(looped.eastward_wind)))


def test_param_gradients_flow_through_the_window() -> None:
    program = functional_compile(_composition(), _state(), timestep=_DT)
    window = scan_window(program.step_fn, 6, remat="per_step")

    def loss(params: Any) -> Any:
        return jnp.sum(window(program.state, params, program.static).eastward_wind)

    grads = mapping_of(jax.grad(loss)(program.params))
    assert set(grads) == {"forcing/amplitude", "decay/rate"}
    assert abs(float(grads["decay/rate"])) > 0.0
    assert abs(float(grads["forcing/amplitude"])) > 0.0


def test_policy_error_names_the_none_component() -> None:
    fast = SequentialUpdateSplitting([ToyOpaque(name="opaque")], name="toy_fast")
    with pytest.raises(FunctionalCompileError, match="opaque"):
        functional_compile(fast, _state(), timestep=_DT)


def test_policy_stop_gradient_compiles_warns_and_stamps_provenance() -> None:
    fast = SequentialUpdateSplitting([ToyOpaque(name="opaque")], name="toy_fast")
    with pytest.warns(UserWarning, match="stop_gradient.*opaque"):
        program = functional_compile(fast, _state(), timestep=_DT, policy="stop_gradient")
    assert "stop_gradient:opaque" in program.provenance

    def loss(state: Any) -> Any:
        return jnp.sum(program.step_fn(state, program.params, program.static).eastward_wind)

    grad_state = jax.grad(loss)(program.state)
    # The only path runs through the truncated component: gradients are zero, loudly.
    assert float(jnp.sum(jnp.abs(grad_state.eastward_wind))) == 0.0
    # And the primal still runs.
    out = program.step_fn(program.state, program.params, program.static)
    assert_allclose(
        np.asarray(out.eastward_wind),
        0.9 * np.asarray(program.state.eastward_wind),
        rtol=1e-15,
        names="stop_gradient primal",
    )


def test_missing_functional_core_raises() -> None:
    class NoCore(Stepper):
        input_properties: ClassVar[Mapping[str, Any]] = {
            "eastward_wind": {"dims": _DIMS, "units": "m s-1"},
        }
        output_properties: ClassVar[Mapping[str, Any]] = {
            "eastward_wind": {"dims": _DIMS, "units": "m s-1", "differentiable": "native"},
        }

        def array_call(
            self,
            inputs: dict[str, FieldBuffer],
            outputs: dict[str, FieldBuffer],
            timestep: timedelta | None,
        ) -> None:
            raise NotImplementedError

    with pytest.raises(FunctionalCompileError, match="functional core"):
        functional_compile(NoCore(name="bare"), _state(), timestep=_DT)


def test_unsupported_node_raises() -> None:
    sub = Subcycle(ToyDecay(name="decay"), n=2)
    with pytest.raises(FunctionalCompileError, match="outside the S10 functional slice"):
        functional_compile(sub, _state(), timestep=_DT)


def test_donate_argnums_path_runs_under_jit() -> None:
    # SPEC acceptance 6: donation runs; functionality only, memory not asserted.
    program = functional_compile(_composition(), _state(), timestep=_DT)
    jitted = jax.jit(program.step_fn, donate_argnums=0)
    out = jitted(program.state, program.params, program.static)
    out = jitted(out, program.params, program.static)
    assert bool(jnp.all(jnp.isfinite(out.eastward_wind)))


def test_invalid_policy_and_timestep() -> None:
    with pytest.raises(ValueError, match="policy"):
        functional_compile(_composition(), _state(), timestep=_DT, policy="silence")
    with pytest.raises(ValueError, match="timestep"):
        functional_compile(_composition(), _state(), timestep=timedelta(0))


def test_static_args_is_a_pytree() -> None:
    static = StaticArgs(dt=30.0)
    leaves = jax.tree_util.tree_leaves(static)
    assert leaves == [30.0]
