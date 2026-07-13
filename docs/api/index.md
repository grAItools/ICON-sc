# API reference

Generated with Sphinx autodoc from the installed, typed sources. This is a
*curated* reference: the modules a model builder or tutorial reader touches.
Internal helpers, the optional `symcon.bridges` toolchain, and test-support
modules are deliberately not listed here — see the source tree for those.

Most classes and functions re-exported at package level (e.g.
`symcon.core.SequentialUpdateSplitting`) are documented under their defining
module below.

## symcon.core — the model-agnostic framework

```{toctree}
:maxdepth: 1

core
core_state
core_contracts
core_components
core_coupling
core_plan
core_functional
core_io
```

## symcon.icon — ICON hosted on symcon.core

```{toctree}
:maxdepth: 1

icon_names
icon_thermo
icon_grid
icon_components
icon_presets
```
