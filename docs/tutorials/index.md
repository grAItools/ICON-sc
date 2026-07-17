# Tutorials

Written for weather and climate scientists and students: you know what
saturation adjustment, a dycore, and a parameterization are; you should not
need to know what an API or a design pattern is before starting. Every page
opens with a science question, introduces at most two or three software terms
(each defined in the [glossary](../glossary.md)), and builds on runnable,
[CI-tested](../glossary.md#ci-continuous-integration) scripts from the
repository's `examples/` directory — the code you see is included from the
tested files, never copied by hand.

## Available now

```{toctree}
:maxdepth: 1

00_what_is_icon-sc
01_state_fields_grids
02_first_run_scm
```

## Planned

The remaining curriculum is fixed so the navigation is stable; these pages are
authored in later iterations.

**T3 — Processes as components: calling saturation adjustment by hand.**
A parameterization is an object you can call interactively on a column state.
Shows the component's declared inputs/outputs (dims, units, location), what
happens when you hand it the wrong units in strict vs interactive mode, and
why "components never share data behind the state's back" is the property
that makes recomposition safe. *Introduces: strict mode, interactive mode.*

**T4 — Process coupling and ordering: why the order matters.**
Sequential-update vs parallel splitting vs Strang, fast vs slow physics with
calling frequencies — the coupling algebra as the space of scientifically
meaningful experiments, with ICON's operational arrangement as one validated
preset and the machinery (`must_follow`/`must_precede`, the
validated/experimental label) that keeps "legal code" from being mistaken for
"right science". *Introduces: federation/coupling operator, validated preset.*

**T5 — The dynamical core and a global test: the baroclinic wave.**
The dycore is not decomposed into per-tendency pieces — it *is* a time loop
(predictor–corrector, `ndyn_substeps`), hosted as one component with a
slow-tendency input port. Walk of `examples/02_jw_baroclinic.py`: the
Jablonowski–Williamson wave on the global R02B04 grid, 35 levels, and how to
look at surface pressure at day 9. *Introduces: substepping tier,
component-private state.*

**T6 — Trusting the results: the validation ladder and reproducibility.**
What "scientific equivalence with ICON" means operationally: the L2→L8 ladder
from stencil parity to gradient verification; the ε-twin chaotic-growth
envelope (why bitwise comparison of 9-day forecasts is the wrong question and
what the right one is); restart reproducibility; provenance stamping (config
+ grid UUIDs + versions in every output). *Introduces: tolerance as
contract.*

**T7 — The same model, faster: plans and execution tiers.**
Why a Python loop over components is fine for a column and a ceiling for a
global GPU run; the negotiation/execution split told science-in: all checks
run once at startup, then a frozen plan executes the identical arithmetic —
and the claim is not rhetoric, it is a CI-enforced bitwise T0≡T1 gate (24
simulated hours through the dycore, exactly equal at every step on every
prognostic). *Introduces: bind time, execution plan, tier.*

**T8 — Asking the model "what if": gradients, sensitivities, parameter
estimation.**
Walk of `examples/07_gradient_scm.py`: the derivative of accumulated surface
rain with respect to the autoconversion coefficient, over a multi-step
window, checked against a finite difference — the atomic operation of
parameter estimation and variational data assimilation, framed via
adjoint/tangent-linear language you already have. *Introduces:
differentiability contract, ParamTree.*
