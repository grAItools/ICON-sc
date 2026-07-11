"""symcon example 07 — gradients through the SCM window (the §8.5–8.6 F-tier).

The S09 single-column composition, lowered to a pure JAX function and
differentiated end-to-end: ``jax.vjp`` of the **accumulated surface rain**
over a multi-step window with respect to the Seifert–Beheng autoconversion
kernel coefficient ``kcau`` in the ParamTree (parameter estimation's atomic
operation), cross-checked against a central finite difference — the SPEC S10
acceptance-4 scalar functional.

The window runs satad → graupel → satad per step (SUS), the graupel JAX core
scanning the sedimentation column, satad differentiating through its saturation
fixed point via the implicit-function rule, and the slow-cooling cadence riding
in the carry — reverse-mode memory managed by per-step rematerialization.

Run (CPU, fp64; < 60 s)::

    uv run python examples/07_gradient_scm.py --steps 10
"""

from __future__ import annotations

import argparse
from typing import Any

import jax

jax.config.update("jax_enable_x64", True)  # fp64 is the contract for gradient work (§8.6)

import jax.numpy as jnp  # noqa: E402

from symcon.core.functional import functional_compile, scan_window  # noqa: E402
from symcon.core.functional.pytree import mapping_of, tree_of  # noqa: E402
from symcon.icon.presets import SCMConfig, build_scm  # noqa: E402

#: The ParamTree leaf the example differentiates (§8.6 params declaration of the
#: graupel scheme: the Seifert–Beheng autoconversion kernel coefficient).
PARAM = "mphys/kcau"


def main(n_steps: int = 10) -> dict[str, Any]:
    """vjp of accumulated precipitation w.r.t. ``kcau`` + FD cross-check."""
    composition, state, cfg = build_scm(SCMConfig())
    program = functional_compile(
        (composition.slow, composition.core, composition.fast), state, timestep=cfg.dtime
    )
    window = scan_window(
        program.step_fn,
        n_steps,
        remat="per_step",
        ys_of=lambda s: jnp.sum(s.icon_rain_gsp_rate),  # kg m-2 s-1, summed over cells
    )

    kcau0 = float(mapping_of(program.params)[PARAM])

    def accumulated_precipitation(scale: Any) -> Any:
        """J(scale) = Σ_steps rain_rate · Δt with kcau = scale · kcau0 [kg m-2]."""
        values = dict(mapping_of(program.params))
        values[PARAM] = scale * values[PARAM]
        params = tree_of(program.param_type, values)
        _, rates = window(program.state, params, program.static)
        return jnp.sum(rates) * program.static.dt

    j0, vjp_fn = jax.vjp(accumulated_precipitation, jnp.asarray(1.0))
    (gradient,) = vjp_fn(jnp.asarray(1.0))
    gradient = float(gradient)  # dJ/dscale = kcau0 * dJ/dkcau

    # Central-difference cross-check on the same scalar functional, scanning a
    # small step ladder; the best step is the acceptance-4 "optimal FD step".
    fd_by_step: dict[float, float] = {}
    for h in (1e-4, 1e-5, 1e-6):
        plus = float(accumulated_precipitation(jnp.asarray(1.0 + h)))
        minus = float(accumulated_precipitation(jnp.asarray(1.0 - h)))
        fd_by_step[h] = (plus - minus) / (2.0 * h)
    best_h, fd = min(fd_by_step.items(), key=lambda kv: abs(kv[1] - gradient))
    rel_err = abs(fd - gradient) / abs(gradient)

    print(f"accumulated precipitation over {n_steps} steps : {float(j0):.6e} kg m-2")
    print(f"vjp  dJ/dkcau (scaled by kcau0={kcau0:.3e})     : {gradient:.10e}")
    print(f"FD   central difference (h={best_h:g})          : {fd:.10e}")
    print(f"relative error                                  : {rel_err:.3e}")
    return {
        "J": float(j0),
        "gradient": gradient,
        "fd": fd,
        "fd_by_step": fd_by_step,
        "rel_err": rel_err,
        "kcau0": kcau0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=10, help="window length in Δt")
    args = parser.parse_args()
    main(n_steps=args.steps)
