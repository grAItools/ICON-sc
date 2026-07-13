# symcon

symcon re-expresses the ICON-NWP atmosphere model as a composition of
self-describing components in Python. The model is a set of fields (the
*state*) evolved by processes (*components*), and one legible run script says
which schemes run, in what order, at what cadences, and where output goes —
the same information a namelist holds, but readable, checkable by machine,
and safe to recompose. The heavy numerics stay compiled: symcon is a host
layer for [icon4py](https://github.com/C2SM/icon4py) granules (GT4Py
stencils), not a NumPy rewrite of ICON.

Three properties carry the design (the architecture document linked below is
canonical):

- **Contracts.** Every component publishes what it reads and writes — names,
  units, and mesh location (cell/edge/vertex) — and the machinery checks the
  composition against those declarations before anything runs.
- **A coupling algebra.** Sequential-update splitting, parallel splitting,
  Strang splitting, calling-frequency tiers: ICON's operational arrangement is
  one *validated preset* in a family of scientifically meaningful
  compositions, not hard-wired structure.
- **Frozen execution plans.** All checks run once at startup; then a frozen
  plan executes the identical arithmetic without per-step bookkeeping —
  verified bit-for-bit against the checked interpreter, and lowerable further
  (graph replay, native driver, a differentiable JAX trace).

## Install

symcon is developed as a [uv](https://docs.astral.sh/uv/) workspace and is not
yet published to PyPI. From a clone:

```bash
git clone <repository-url> symcon && cd symcon
uv sync            # resolves the pinned working set from uv.lock
uv run python examples/01_scm_column.py --hours 1 --output scm_column.nc
```

Python 3.10–3.14 on Linux/macOS; everything in the tutorials runs on a CPU
laptop.

## Where to go

- New here? Start with the [tutorials](tutorials/index.md) — written for
  weather and climate scientists, software concepts introduced only as needed.
- Looking up a class or function? The [API reference](api/index.md).
- The full design, with every tension and decision recorded: the
  [architecture document](architecture/symcon_architecture.md) (v1.3,
  canonical) and the [repository layout](architecture/symcon_repo_layout.md).
- Software terms defined science-in: the [glossary](glossary.md).
- Contributing or running the implementation plan? See `AGENTS.md` and
  `development/` in the repository — developer process documents are deliberately
  not reworked as user docs.

```{toctree}
:hidden:
:caption: Tutorials

tutorials/index
```

```{toctree}
:hidden:
:caption: API reference

api/index
```

```{toctree}
:hidden:
:caption: Architecture

architecture/symcon_architecture
architecture/symcon_repo_layout
```

```{toctree}
:hidden:
:caption: Reference

glossary
names_registry
```
