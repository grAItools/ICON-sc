# S10 — Plan
1. `pytree.py` first: `dataclasses.make_dataclass(..., frozen=True)` + `jax.tree_util.register_dataclass`; carry surfaced by walking `functional_state()` of every component in the composition (CallingFrequency caches included — S03 prepared this).
2. `compile.py`: reuse S05's composition-walk protocol; target pure functions instead of ops. Cadence: carry the cached slow tendency + `jnp.where(mask[step], recompute, cached)` with masks precomputed per window (static under scan via `xs`).
3. Graupel JAX core: port from the gtfn stencil definitions (same control structure; `jnp.where` for branches; sedimentation as `lax.scan` over levels top-down — mirrors ICON's level loop). Constants from `_constants.py` only.
4. Satad IFT: solve the fixed point with a bounded `lax.while_loop`-free Newton (fixed iteration count, tolerance-asserted) wrapped in `jax.lax.custom_root` (or hand `custom_vjp` with the linearized-residual solve) so reverse mode goes through the implicit function, not the iterations. Read `mo_satad` once more for the exact residual.
5. L8 harness in `icon_sc/core/testing`: `taylor_test(f, x, v)`, `dot_product_test(f, x, v, w)` — generic, reused in P6.
6. Example + validation seeding; fp64 via `jax.config.update("jax_enable_x64", True)` in test conftest.
**Pitfalls:** carry ordering must be deterministic (sort leaves by name at generation); mask arrays must be step-indexed `xs`, not Python ints, or scan retraces; keep the functional path free of any `icon_sc.core.state.dataarray` import (trace purity).
