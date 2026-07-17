# T0 — What ICON-sc is: a weather model as a run script

**The science question first.** During one timestep Δt of ICON-NWP, which
processes act on the atmosphere, in what order, and how often? You can answer
that question from the ICON documentation — but not from any single place in
the model's configuration. The namelists say which schemes are switched on
and at what cadences; the calling *order* lives in the interface code; the
coupling strategy (who sees whose update within the step) is documented prose.
The experiment you are actually running is spread across three places, only
one of which you edit.

ICON-sc re-expresses ICON-NWP so that this answer is one readable object. The
premise, inherited from the [sympl](https://sympl.readthedocs.io) framework
family, is that an atmospheric model is two things:

- a [state dictionary](../glossary.md#state-dictionary) — every
  prognostic and diagnostic field of the model in one collection, each field
  carrying its own name, units, and grid location, plus the model time;
- a set of [components](../glossary.md#component) — one per process:
  saturation adjustment, graupel microphysics, turbulence, radiation, the
  dynamical core. Each declares what it reads and writes, and evolves the
  state when called.

Everything else — which schemes, what order, what cadences, where output
goes — lives in one short [run script](../glossary.md#run-script) that
you read top to bottom. It carries the same information a namelist holds,
plus the ordering and coupling knowledge the namelist doesn't, and every
claim in it is checked by machine before the first step runs.

## What that looks like

Here is the heart of the smallest real ICON-sc model — the single-column
experiment you will run yourself in
[T2](02_first_run_scm.md), taken verbatim from the tested script
`examples/01_scm_column.py`:

```{literalinclude} ../../examples/01_scm_column.py
:language: python
:pyobject: main
```

Even before the tutorials define every name here, the shape is legible:
build a model composition and an initial state, attach a NetCDF output
monitor, loop over timesteps for an hour. The full global NWP configuration
has exactly the same shape, just with more components — the architecture
document shows it in
[§5.1, "The canonical run script"](../architecture/icon-sc_architecture.md):
dycore, diffusion, tracer transport, the fast-physics sequence, and the slow
processes each at their own calling period, all on one screen.

## Why re-express ICON in Python at all?

The heavy numerics do not move to Python. ICON-sc is a *host* layer: inside
the components run [icon4py](https://github.com/C2SM/icon4py) granules —
GT4Py stencils compiled for CPU or GPU, the same code paths the ICON
modernization effort itself builds on. What ICON-sc adds is the layer where
science mistakes actually happen and where experiments are actually
expressed:

- **The composition is checkable.** Each component's declared inputs and
  outputs — with units and grid location — are verified against the state
  and against each other before a run starts. Wrong units, a field on the
  wrong mesh location, a forcing nobody consumes: composition-time errors
  with a component named in the message, not silent wrong answers.
- **The composition is editable.** Swapping the process coupling, changing a
  calling period, or replacing one scheme with another is an edit to the run
  script — visible in full in a code review or a paper's supplement.
- **The result is still fast, and provably the same.** After all checks pass
  once at startup, the composition is frozen into an execution plan that runs
  without per-step bookkeeping — verified bit-for-bit against the checked
  version (tutorial T7 covers this).

**Everything here runs.** The code shown above is included directly from the
[CI-tested](../glossary.md#ci-continuous-integration) example file. Run it yourself from a repository checkout (about a
minute on a laptop CPU):

```bash
uv run python examples/01_scm_column.py --hours 1 --output scm_column.nc
```

*New terms introduced on this page:*
[state dictionary](../glossary.md#state-dictionary),
[component](../glossary.md#component),
[run script](../glossary.md#run-script).

**Next:** [T1 — The model state: fields, units, and where they live on the
grid](01_state_fields_grids.md).
