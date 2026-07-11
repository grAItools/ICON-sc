"""L8 gradient-verification battery at column scale (architecture §9; seeded S10).

Runs the Taylor-remainder, dot-product and FD checks over the S10 functional
surface — satad (IFT rule), graupel (scan core) and the composed 10-step SCM
window — printing the table and writing remainder-decay plots to
``validation/L8_gradients/artifacts/`` (gitignored).

Usage::

    uv run python validation/L8_gradients/run_l8.py [--no-plots]
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import jax

jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402

from symcon.core.functional import functional_compile, scan_window  # noqa: E402
from symcon.core.functional.pytree import mapping_of, tree_of  # noqa: E402
from symcon.core.testing.gradients import (  # noqa: E402
    TaylorResult,
    dot_product_test,
    taylor_test,
)
from symcon.icon.presets import SCMConfig, build_scm  # noqa: E402

ARTIFACTS = Path(__file__).parent / "artifacts"


def _scm_window(n_steps: int = 10) -> tuple[Any, Any, Any, Any]:
    composition, state, cfg = build_scm(SCMConfig())
    program = functional_compile(
        (composition.slow, composition.core, composition.fast), state, timestep=cfg.dtime
    )
    window = scan_window(program.step_fn, n_steps, remat="per_step")
    return program, window, composition, cfg


def _tangent(program: Any, rng: np.random.Generator) -> Any:
    values = {}
    for name, leaf in mapping_of(program.state).items():
        if name == "air_temperature":
            values[name] = jnp.asarray(rng.normal(size=np.shape(leaf))) * 1e-2
        elif name == "specific_humidity":
            values[name] = jnp.asarray(rng.normal(size=np.shape(leaf))) * 1e-6
        else:
            values[name] = jnp.zeros_like(jnp.asarray(leaf))
    return tree_of(program.state_type, values)


def _cotangent(program: Any, rng: np.random.Generator) -> Any:
    values = {
        name: jnp.asarray(rng.normal(size=np.shape(leaf)))
        for name, leaf in mapping_of(program.state).items()
    }
    return tree_of(program.state_type, values)


def _plot(name: str, result: TaylorResult) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ARTIFACTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.loglog(result.steps, result.remainders, "o-", label="‖f(x+hv) - f(x) - h·Jv‖")
    href = np.asarray(result.steps)
    ax.loglog(
        href,
        result.remainders[0] * (href / href[0]) ** 2,
        "k--",
        label="slope-2 reference",
    )
    ax.set_xlabel("h")
    ax.set_ylabel("Taylor remainder")
    ax.set_title(f"{name}: slope {result.slope:.3f}")
    ax.legend()
    fig.tight_layout()
    path = ARTIFACTS / f"taylor_{name}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"    plot -> {path}")


def main(plots: bool = True) -> None:
    rng = np.random.default_rng(2026)
    program, window, _, _ = _scm_window(10)

    print("L8 gradient battery (S10 slice: satad IFT, graupel scan, 10-step SCM window)")

    def step_f(s: Any) -> Any:
        return program.step_fn(s, program.params, program.static)

    def window_f(s: Any) -> Any:
        return window(s, program.params, program.static)

    for name, fn, h0 in (("scm_step", step_f, 1e-2), ("scm_window_10", window_f, 1e-1)):
        v = _tangent(program, rng)
        w = _cotangent(program, rng)
        taylor = taylor_test(fn, program.state, v, h0=h0, n_halvings=6)
        dot = dot_product_test(fn, program.state, v, w)
        print(f"  {name:16s} taylor slope {taylor.slope:6.3f}   dot-product {dot:.3e}")
        if plots:
            _plot(name, taylor)

    print("(component-level batteries gate in packages/*/tests/test_*_functional.py)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    main(plots=not args.no_plots)
