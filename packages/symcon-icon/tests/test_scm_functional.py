"""S10: the F-tier on the SCM composition — L8 at column scale.

SPEC S10 acceptances on the composed window:

- 7: T0 ↔ F-tier forward equivalence over a multi-step window (rtol ≤ 1e-10
  fp64; different kernels ⇒ not bitwise; absolute floor at the scheme's QMIN
  for mixing-ratio-valued fields, justification in STATUS);
- 2/3: Taylor jvp decay and dot-product adjoint consistency through a 10-step
  ``scan_window`` (satad IFT rule included — satad runs twice per step);
- 4: FD cross-check of the example-07 scalar functional (vjp of accumulated
  precipitation w.r.t. the autoconversion parameter), rtol ≤ 1e-6;
- 5: ``stop_gradient`` policy — a `none`-marked satad raises under
  ``policy="error"`` naming the component; compiles + warns + stamps
  provenance under ``policy="stop_gradient"``;
- 6: the ``donate_argnums`` path runs under jit (functionality only).
"""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402

from symcon.core import SequentialUpdateSplitting  # noqa: E402
from symcon.core.functional import (  # noqa: E402
    FunctionalCompileError,
    functional_compile,
    scan_window,
)
from symcon.core.functional.pytree import mapping_of, tree_of  # noqa: E402
from symcon.core.testing import assert_allclose  # noqa: E402
from symcon.core.testing.gradients import dot_product_test, taylor_test  # noqa: E402
from symcon.icon.components.fast.graupel_constants import GRAUPEL_QMIN  # noqa: E402
from symcon.icon.components.fast.satad import SaturationAdjustment  # noqa: E402
from symcon.icon.components.idealized import SLOW_TEMPERATURE_SLOT  # noqa: E402
from symcon.icon.presets import SCMConfig, build_scm  # noqa: E402

from _functional_columns import PROGNOSTICS, RATES  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples" / "07_gradient_scm.py"

#: acceptance-7 contract (+ QMIN absolute floor for mixing-ratio-valued fields).
EQUIV_RTOL = 1.0e-10
EQUIV_ATOL = GRAUPEL_QMIN

DOT_PRODUCT_TOL = 1.0e-10
TAYLOR_SLOPE = 2.0
TAYLOR_TOL = 0.1
FD_RTOL = 1.0e-6

_COMPARED = (*PROGNOSTICS, *RATES, SLOW_TEMPERATURE_SLOT)


def _t0_run(composition: Any, state: dict[str, Any], cfg: Any, n_steps: int) -> dict[str, Any]:
    working = dict(state)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # icon4py embedded-execution warnings
        for _ in range(n_steps):
            working = composition.step(working, cfg.dtime)
            working["time"] = working["time"] + cfg.dtime
    return working


def _compile(state: dict[str, Any], cfg: Any, **kwargs: Any) -> Any:
    composition, _, _ = build_scm(cfg)
    return functional_compile(
        (composition.slow, composition.core, composition.fast),
        state,
        timestep=cfg.dtime,
        **kwargs,
    )


def _assert_equivalent(values: dict[str, Any], reference: dict[str, Any]) -> None:
    for name in _COMPARED:
        assert_allclose(
            np.asarray(values[name]),
            np.asarray(reference[name].data),
            rtol=EQUIV_RTOL,
            atol=0.0 if name == "air_temperature" else EQUIV_ATOL,
            names=(f"F-tier {name}", f"T0 {name}"),
        )


def test_t0_ftier_forward_equivalence_over_a_window() -> None:
    # 12 steps: one full slow-physics cadence (10 steps) plus a refire.
    cfg = SCMConfig()
    composition, state, cfg = build_scm(cfg)
    reference = _t0_run(composition, state, cfg, 12)

    program = _compile(state, cfg)
    tree = program.state
    step = jax.jit(program.step_fn)
    for _ in range(12):
        tree = step(tree, program.params, program.static)
    _assert_equivalent(mapping_of(tree), reference)


def test_equivalence_from_a_prefired_cadence_phase() -> None:
    # Compile mid-run: the CallingFrequency phase + cache ride into the carry
    # through the wrapper's restart surface; both tiers continue identically.
    cfg = SCMConfig()
    composition, state, cfg = build_scm(cfg)
    midpoint = _t0_run(composition, state, cfg, 5)

    program = functional_compile(
        (composition.slow, composition.core, composition.fast),  # live, pre-fired
        midpoint,
        timestep=cfg.dtime,
    )
    reference = _t0_run(composition, midpoint, cfg, 7)  # crosses the step-10 refire
    tree = program.state
    for _ in range(7):
        tree = program.step_fn(tree, program.params, program.static)
    _assert_equivalent(mapping_of(tree), reference)


@pytest.fixture(scope="module")
def window_program() -> tuple[Any, Any]:
    _, state, cfg = build_scm(SCMConfig())
    program = _compile(state, cfg)
    window = scan_window(program.step_fn, 10, remat="per_step")
    return program, window


def _window_tangent(program: Any, rng: np.random.Generator) -> Any:
    values = {}
    for name, leaf in mapping_of(program.state).items():
        if name == "air_temperature":
            values[name] = jnp.asarray(rng.normal(size=np.shape(leaf))) * 1e-2
        elif name == "specific_humidity":
            values[name] = jnp.asarray(rng.normal(size=np.shape(leaf))) * 1e-6
        else:
            values[name] = jnp.zeros_like(jnp.asarray(leaf))
    return tree_of(program.state_type, values)


def test_taylor_jvp_decay_through_the_ten_step_window(
    window_program: tuple[Any, Any],
) -> None:
    program, window = window_program
    rng = np.random.default_rng(3)
    v = _window_tangent(program, rng)
    result = taylor_test(
        lambda s: window(s, program.params, program.static), program.state, v, h0=1e-1
    )
    assert result.slope == pytest.approx(TAYLOR_SLOPE, abs=TAYLOR_TOL), result


def test_dot_product_through_the_ten_step_window(window_program: tuple[Any, Any]) -> None:
    # The window crosses the satad IFT rule twenty times (satad twice per step).
    program, window = window_program
    rng = np.random.default_rng(5)
    v = _window_tangent(program, rng)
    w = tree_of(
        program.state_type,
        {
            name: jnp.asarray(rng.normal(size=np.shape(leaf)))
            for name, leaf in mapping_of(program.state).items()
        },
    )
    error = dot_product_test(
        lambda s: window(s, program.params, program.static), program.state, v, w
    )
    assert error <= DOT_PRODUCT_TOL


def test_donate_argnums_runs_under_jit(window_program: tuple[Any, Any]) -> None:
    program, _ = window_program
    jitted = jax.jit(program.step_fn, donate_argnums=0)
    tree = jitted(program.state, program.params, program.static)
    tree = jitted(tree, program.params, program.static)
    assert bool(jnp.all(jnp.isfinite(tree.air_temperature)))


class _OpaqueSatad(SaturationAdjustment):
    """satad with its differentiability contract demoted to `none` (acceptance 5)."""

    output_properties: ClassVar[dict[str, Any]] = {
        "air_temperature": {"dims": ("cell", "height"), "units": "K"},
        "specific_humidity": {"dims": ("cell", "height"), "units": "1"},
        "specific_cloud_content": {"dims": ("cell", "height"), "units": "1"},
    }


def _opaque_fast(cfg: Any) -> tuple[Any, dict[str, Any]]:
    from symcon.icon.grid.vertical import SleveConfig, VerticalGrid

    composition, state, _ = build_scm(cfg)
    grid = VerticalGrid.from_config(SleveConfig(num_levels=cfg.nlev))
    opaque = _OpaqueSatad(grid, cfg.satad, name="satad")
    fast = SequentialUpdateSplitting([opaque], name="opaque_fast")
    del composition
    return fast, state


def test_policy_error_raises_naming_satad() -> None:
    cfg = SCMConfig()
    fast, state = _opaque_fast(cfg)
    with pytest.raises(FunctionalCompileError, match="satad"):
        functional_compile(fast, state, timestep=cfg.dtime, policy="error")


def test_policy_stop_gradient_compiles_warns_and_stamps() -> None:
    cfg = SCMConfig()
    fast, state = _opaque_fast(cfg)
    with pytest.warns(UserWarning, match="stop_gradient.*satad"):
        program = functional_compile(fast, state, timestep=cfg.dtime, policy="stop_gradient")
    assert "stop_gradient:satad" in program.provenance

    def loss(tree: Any) -> Any:
        out = program.step_fn(tree, program.params, program.static)
        return jnp.sum(out.specific_cloud_content)

    grads = mapping_of(jax.grad(loss)(program.state))
    # Gradients through the truncated satad are zero — loudly, never silently.
    assert float(jnp.sum(jnp.abs(grads["air_temperature"]))) == 0.0


@pytest.mark.slow
def test_example_fd_cross_check() -> None:
    # SPEC acceptance 4: central difference vs the vjp gradient of the example's
    # scalar functional (accumulated precipitation w.r.t. kcau), rtol at the
    # optimal FD step.
    spec = importlib.util.spec_from_file_location("example_07_gradient_scm", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.main(n_steps=10)
    assert result["J"] > 0.0
    assert result["gradient"] != 0.0
    assert result["rel_err"] <= FD_RTOL
