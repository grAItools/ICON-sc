# T2 — Your first run: a single-column model

**The science question first.** Take one atmospheric column whose lower
troposphere starts supersaturated, and let ICON's fast moist physics act on
it: what rains out, and how fast? A single-column model (SCM) is the
smallest experiment that exercises real parameterizations in their real
calling order — and it is small enough to run in under a minute on a laptop.

This page walks `examples/01_scm_column.py` end to end. All code shown is
included directly from that CI-tested file; nothing is copied by hand.

**Everything here runs.** From a repository checkout:

```bash
uv run python examples/01_scm_column.py --hours 1 --output scm_column.nc
```

## What the script says it does

```{literalinclude} ../../examples/01_scm_column.py
:language: python
:lines: 1-14
```

Unpacking that: the composition is a
[preset](../glossary.md#preset) — a pre-built, validated arrangement of
components, in this case the SCM subset of ICON's fast-physics calling
sequence. Saturation adjustment runs *before and after* graupel
microphysics ("to ensure that vapor and liquid phase are in equilibrium
before entering the slow physics parameterizations", in the ICON tutorial's
words), and each process consumes the state left by the previous one —
sequential-update splitting, exactly ICON's operational fast-physics
coupling. That ordering rule is not a comment: it is attached to the preset
as a machine-checked constraint, and a composition that violates it refuses
to build.

On top of the fast suite there is one slow process — a prescribed cooling
standing in for radiation. It runs every 300 s (ten fast steps), and between
calls its heating rate is held piecewise-constant on the
[slow-tendency bus](../glossary.md#slow-tendency-bus): it *publishes*
to the named slot `icon:ddt_temperature_slow`, and a consumer component
(standing in for the dycore's slow-tendency port) integrates that slot every
fast step. This is ICON's operational arrangement for slow physics, at
column scale. The bus is checked when the model is built: a published slot
with no consumer — a forcing that would silently vanish — is a build error.

## The model

```{literalinclude} ../../examples/01_scm_column.py
:language: python
:pyobject: build_model
```

One call builds everything: the components, their coupling, the constraint
and bus checks, and the initial column — a decaying-isothermal reference
atmosphere whose humidity is scaled so the lower troposphere starts
supersaturated (so condensation and precipitation begin immediately). The
default configuration is a frozen dataclass; here it is, from the preset
module itself:

```{literalinclude} ../../packages/symcon-icon/src/symcon/icon/presets/scm.py
:language: python
:pyobject: SCMConfig
```

## Output selection and the run

```{literalinclude} ../../examples/01_scm_column.py
:language: python
:lines: 29-44
```

```{literalinclude} ../../examples/01_scm_column.py
:language: python
:pyobject: main
```

`timeloop` drives the composition's `step` for the requested duration, and
the monitor writes the selected fields to NetCDF at every step. The run
prints a summary; with the defaults (`--hours 1`) you should see the column
warm as latent heat is released and rain reach the surface:

```text
SCM run complete: 1.0 h at dt=30 s
  surface temperature      :   296.307 K
  max surface rain rate    : 6.718e-04 kg m-2 s-1
  output                   : scm_column.nc
```

The output file is ordinary CF-style NetCDF; open it with whatever you
already use (xarray, ncview, cdo). For a quick look with xarray and
matplotlib:

```bash
uv run python -c "
import xarray as xr
ds = xr.open_dataset('scm_column.nc')
ds['icon:rain_gsp_rate'].isel(cell=0).plot()
import matplotlib.pyplot as plt; plt.savefig('rain.png')
"
```

## Now change something

The point of a preset is that the *validated* arrangement is one object, and
your experiment is a visible edit against it. Halve the initial
supersaturation by editing the config value in `build_model`:

```python
return build_scm(SCMConfig(qv_scale=1.5))  # default: 2.0
```

and rerun. Less initial vapor excess means less condensate and weaker rain —
check `icon:rain_gsp_rate` in the output. Any config field in `SCMConfig`
above can be changed the same way (the slow-physics cadence
`slow_timestep`, the timestep `dtime`, the number of levels `nlev`, …), and
anything the configuration cannot express — reordering processes, removing
the consumer of a published tendency — is exactly what the constraint and
bus checks are there to catch: try
`build_scm(SCMConfig(), fast_order=("mphys", "satad"))` and read the error.

*New terms introduced on this page:*
[preset](../glossary.md#preset),
[slow-tendency bus](../glossary.md#slow-tendency-bus).

**Next (planned):** T3 — Processes as components: calling saturation
adjustment by hand. See the [curriculum](index.md).
