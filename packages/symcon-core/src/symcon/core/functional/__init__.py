"""The §8.5-8.6 functional lowering (F-tier), proven at column scale (SPEC S10).

Layout (architecture §8.5; jax-touching core code lives here and nowhere else in
``symcon.core`` — importing :mod:`symcon.core` itself never imports jax):

- :mod:`symcon.core.functional.pytree` — generated frozen-dataclass PyTrees:
  ``StateTree`` from the state/vault schema plus explicit carry, ``ParamTree``
  from the components' ``params`` declarations.
- :mod:`symcon.core.functional.compile` — composition → pure
  ``step_fn(StateTree, ParamTree, StaticArgs) -> StateTree`` and the
  ``scan_window`` (``lax.scan`` + per-step ``jax.checkpoint``) window builder.
- :mod:`symcon.core.functional.rules` — implicit-function-theorem helpers for
  fixed points (``lax.custom_root`` wrappers; the §8.6 ``custom`` route).

fp64 is the default for gradient work (§8.6): the compile entry point warns when
jax runs in fp32 (``jax.config.update("jax_enable_x64", True)``).
"""

from symcon.core.functional.compile import (
    FunctionalCompileError,
    FunctionalProgram,
    StaticArgs,
    functional_compile,
    scan_window,
)
from symcon.core.functional.pytree import (
    build_param_tree,
    build_state_tree,
    make_pytree_type,
    mapping_of,
    tree_of,
)
from symcon.core.functional.rules import implicit_fixed_point, masked_newton_solve

__all__ = [
    "FunctionalCompileError",
    "FunctionalProgram",
    "StaticArgs",
    "build_param_tree",
    "build_state_tree",
    "functional_compile",
    "implicit_fixed_point",
    "make_pytree_type",
    "mapping_of",
    "masked_newton_solve",
    "scan_window",
    "tree_of",
]
