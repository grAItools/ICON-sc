# Glossary

Software terms used by the tutorials, defined from the science in. One
paragraph each; tutorials link here on first use. (Terms for the planned
pages T3–T8 are added when those pages land.)

## CI (continuous integration)

An automated referee that re-runs every check on every proposed change to the
code: the full test suite — from stencil-level comparisons against ICON
reference data up to multi-hour model integrations — plus the documentation
build, executed by machines before any change is accepted. When a tutorial
says a script is "CI-tested", it means exactly that: the code you are reading
is re-run automatically on every change, so it cannot silently rot the way a
paper's code appendix can.

## state dictionary

The model state as one Python dictionary: each entry maps a field name
(`"air_temperature"`, `"icon:normal_wind"`, …) to an array carrying its own
units and grid location, plus a `"time"` entry. It is the same collection of
prognostic and diagnostic fields a model description paper tabulates — held
in one place, and the *only* channel through which processes see each other's
work. Components never share data behind the state's back.

## component

One process of the model — saturation adjustment, graupel microphysics, the
dynamical core — as a self-describing object: it declares which fields it
reads and which it writes (with units and grid location), and when called
with a state it returns its updates. A parameterization you can call, by
itself, on a column state; the composition machinery checks its declarations
against everything else's before a run starts.

## run script

The single, legible source of compositional truth: one short Python script
that says which schemes run, in what order, at what cadences, and where
output goes. It carries the same information as an ICON namelist plus the
calling-order knowledge otherwise buried in the interface code — but it is
readable top to bottom, and every claim in it is machine-checked at startup.

## property contract

The component's published list of what fields it reads and writes, with units
and mesh location — the machine-checked version of the interface table in a
model description paper. If a scheme asks for temperature in K on cell
centers and the state holds something else, the mismatch is an error message
naming the component and field, not a silent wrong answer.

## canonical units

One fixed unit per field name, registry-enforced (`air_temperature` is always
K, `air_pressure` always Pa). Components declare their contracts in canonical
units, so no unit conversion ever needs to happen between processes — the
convenience of automatic conversion exists for interactive use, but in
production any conversion that would silently allocate and copy is an error.

## staggering as API

On ICON's triangular C-grid the normal wind lives on cell *edges* while
temperature and moisture live at cell *centers* — mixing them up is a physics
error, not a formatting one. symcon makes the mesh location (cell / edge /
vertex) part of every field's contract, so the machinery catches location
mismatches, and any reconstruction between locations (e.g. edge winds to
cell-center u, v for physics) is a visible, named step — never a hidden
convenience.

## preset

A named, pre-built composition whose scientific behaviour has been validated
against a reference — e.g. the single-column preset: ICON's fast-physics
subset in its operational calling order, with the tutorial's ordering rules
attached as machine-checked constraints. You can build compositions the
preset would forbid (that is the point of a research framework), but only the
preset carries the *validated* label.

## slow-tendency bus

How slow physics hands its heating and momentum rates to the dynamical core —
ICON's operational arrangement. Slow processes run at their own cadence and
*publish* piecewise-constant tendencies to named slots
(`icon:ddt_temperature_slow`, …); the core *consumes* those slots every fast
step. The bus is the bookkeeping for those slots: every slot must have
exactly one consumer, checked when the composition is built, so a forcing
that nobody applies refuses to build instead of silently vanishing.
