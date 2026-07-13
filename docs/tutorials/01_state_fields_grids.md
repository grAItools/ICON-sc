# T1 — The model state: fields, units, and where they live on the grid

**The science question first.** On ICON's triangular C-grid, the prognostic
wind is not $(u, v)$ at cell centers — it is the edge-normal component
$v_n = \mathbf{v} \cdot \mathbf{n}_e$, stored on cell *edges*, while
temperature, pressure, and moisture live at cell *centers* and some
quantities (vorticity) at *vertices*. Physics schemes want cell-center
winds; the dycore wants edge winds back. Every coupling between them is a
reconstruction with scientific content. So: when a field sits in the model
state, what must it carry with it so that handing it to the wrong scheme, in
the wrong units, at the wrong grid location, is an *error message* rather
than a wrong forecast?

symcon's answer: every field in the
[state dictionary](../glossary.md#state-dictionary) is an array plus
three pieces of metadata the machinery enforces — a canonical name, canonical
units, and a mesh location.

## Look at a real state

Build the single-column model's initial state (this is the same preset T2
runs) and inspect one field. Start `uv run python` in a repository checkout
and paste:

```pycon
>>> from symcon.icon.presets import SCMConfig, build_scm
>>> composition, state, cfg = build_scm(SCMConfig())
>>> t = state["air_temperature"]
>>> t.dims
('cell', 'height')
>>> t.attrs["units"]
'K'
>>> t.attrs["location"]
<Location.CELL: 'cell'>
```

That last value is stored as an *enumeration* — a type that admits exactly
three values (cell, edge, vertex), so a misspelled location cannot exist in
the state at all; its printed form names both the type and the value,
`'cell'`.

Fields are `xarray.DataArray`s: the `data` inside is an ordinary NumPy (or,
on GPU, CuPy) array, and the wrapper carries the metadata. Three conventions
give the metadata its teeth:

**Names.** CF standard names are used wherever CF defines them
(`air_temperature`, `specific_humidity`, …). Solver-internal quantities that
CF deliberately does not name — the Exner function, the edge-normal wind,
tendency staging slots — live in an `icon:` namespace
(`icon:exner_function`, `icon:normal_wind`, `icon:ddt_temperature_slow`).
The full mapping between canonical names, ICON Fortran short names, and CF is
one table: the [variable registry](../names_registry.md).

**[Canonical units](../glossary.md#canonical-units).** One fixed unit
per name, registry-enforced: temperature is always K, pressure always Pa, a
temperature tendency always K s⁻¹ — so $\partial_t T$ published by a slow
process and consumed by the core needs no conversion, ever. This is a
deliberate break with frameworks that convert units silently at every
component boundary: convenient interactively, but on a GPU a hidden
conversion is a hidden allocation and copy. In symcon's strict (production)
mode, any ingress that would allocate — a unit conversion, a dimension
transpose, a host↔device transfer — raises an error naming the component and
the field.

**[Staggering as API](../glossary.md#staggering-as-api).** The mesh
location — `cell`, `edge`, or `vertex` — is part of every field's
declaration, visible above in both `dims` and
`attrs["location"]`. A component that asks for
`icon:normal_wind` on `('edge', 'height')` in m s⁻¹ will never be handed a
cell-center reconstruction by accident: location mismatches are contract
errors. And because nothing regrids silently, the edge→cell wind
reconstruction the physics needs is a visible, named step in the
composition — architecture
[§3.3, "Staggering as API, not convention"](../architecture/symcon_architecture.md).

## The contract that ties it together

What a component publishes about itself is its
[property contract](../glossary.md#property-contract): the list of
fields it reads and writes, each with dims, units, and location — the
machine-checked version of the interface table in a model description paper.
When a composition is built, every contract is checked against the state and
against the other components; the checks run once, at startup, and then get
out of the way (T7 explains how).

Two further attributes ride along for the distributed and provenance stories,
introduced properly in later tutorials: `attrs["halo"]` — "are my neighbor
points up to date after the last exchange" (`valid` in the single-column
state above, since a column has no neighbors) — and, on real horizontal
grids, the grid file's UUID, so fields from different grids refuse to mix.

**Everything here runs.** The transcript above is reproducible exactly:

```bash
uv run python
# then paste the >>> lines from this page
```

*New terms introduced on this page:*
[property contract](../glossary.md#property-contract),
[canonical units](../glossary.md#canonical-units),
[staggering as API](../glossary.md#staggering-as-api).

**Next:** [T2 — Your first run: a single-column model](02_first_run_scm.md).
