# symcon: A sympl-Conformant Python Architecture for the ICON Model

**Status:** design proposal v1.3 (rev.: DaCe-free orchestration; bind-time interface specialization; Tasmania coupling algebra; differentiability contract + functional lowering) · **Scope:** global ICON-NWP atmosphere (dycore + tracer transport + full NWP physics suite), ICON-artifact ingestion, Pythonic configuration and output · **Compatibility target:** scientific equivalence with ICON (same equations, same schemes, same coupling strategy), not bitwise parity · **Out of scope for v1 (but not precluded):** nesting, ICON-LAM, ocean, AES physics, ART, data assimilation beyond IAU.

---

## 0. Executive summary

symcon is a host/orchestration layer that re-expresses ICON-NWP as a composition of sympl-style components over a zero-copy device-field protocol. The design keeps sympl's three load-bearing ideas — (1) a model *is* a state dictionary evolved by typed components, (2) components carry self-documenting property contracts (names, dims, units), (3) the run script is the single, legible source of compositional truth — and extends the taxonomy in the four places where ICON's structure cannot be expressed in vanilla sympl, plus one requirement orthogonal to ICON itself:

1. **A general dynamics–physics coupling algebra**, adopted from Ubbiali's Tasmania framework (ETH thesis no. 28022): federation classes realizing parallel splitting (PS), sequential-tendency splitting (STS), sequential-update splitting (SUS), and symmetrized/Strang splitting (SSUS); `ConcurrentCoupling` realizing (lazy) full coupling (FC/LFC); and a `DynamicalCore` base class with slow/fast/super-fast cadence tiers. ICON's operational coupling — SUS fast physics plus lazily evaluated, piecewise-constant slow tendencies fed to the core — becomes one *validated preset* in this algebra rather than hard-wired structure. (Vanilla sympl's `TendencyStepper` expresses only tendency-summing coupling; the sympl paper concedes sequential splitting needs custom machinery, and Tasmania built precisely that machinery.)
2. **Sub-cycled steppers** for the dynamics substepping (`ndyn_substeps`) and, dually, **calling-frequency policies** for slow physics (a generalization of sympl's `UpdateFrequencyWrapper`, which already has exactly the right piecewise-constant-tendency semantics ICON assumes).
3. **Explicit communication components and halo metadata** — sympl has no distributed-memory story at all; symcon makes halo validity part of the field contract and halo exchange a first-class component kind, with GHEX as the substrate.
4. **Location typing** (cell/edge/vertex) in the property contracts, because ICON's C-grid staggering on the icosahedral mesh is not expressible in sympl's dims-plus-units vocabulary.
5. **A differentiability contract and a functional lowering.** Components declare `native` / `custom` / `none` differentiability and expose tunable scheme constants as a `ParamTree`; the same negotiated composition that feeds the imperative execution tiers also compiles to a pure JAX step function (the F-tier) with explicit-carry PyTrees, `lax.scan` windows, and a transpose-rule differentiable halo exchange — making `jax.jvp`/`jax.vjp` of the composed model a supported operation rather than a rewrite (§8.5–8.7).

The compute substrate is the hybrid agreed on: the state boundary is arrays-with-metadata (xarray `DataArray` over NumPy/CuPy buffers, exchanged zero-copy via DLPack); GT4Py fields, JAX arrays, or Numba device arrays exist only *inside* components as ingress views of those buffers. ICON4Py granules are the intended implementation of the dycore, transport, and most physics components — symcon is a host layer for icon4py, not a fork of it. This is the same principle as the ICON4Py↔anemoi decision: shared abstraction lives at the state/data boundary; no attempt is made to unify compute-layer field types across frameworks.

The deliberate trade at the center of the design: **composition-time legibility, execution-time fusion.** The run script remains a readable, sympl-style description of the model. But at production step rates (milliseconds per step on GPU), a Python dict-of-arrays dispatch loop is a real ceiling, so the architecture splits a one-time *negotiation phase* (the full sympl contract machinery) from a specialized *execution phase*: at startup the validated component sequence is compiled into a static execution plan — pre-bound buffers, no dict or xarray traffic — and optionally lowered further to CUDA-graph replay per exchange-free segment, or to a generated native host driver, bypassing the Python boundary under a validated-equivalence contract. The run script then *constructs* the timestep; it no longer *dispatches* it. A fourth lowering of the same plan — a pure-functional JAX trace — makes the composed model differentiable without disturbing the production tiers.

---

## 1. Where sympl and ICON collide (design tensions)

Being explicit about the collisions up front, because each one drives a taxonomy or protocol extension below.

**T1 — Splitting semantics.** sympl's `TendencyStepper` gathers tendencies from a set of `TendencyComponent`s, *sums* them, and steps: parallel (process) splitting. ICON-NWP is the opposite on both halves: fast physics is sequential-update splitting (each process consumes the state left by the previous one and updates it in place; tutorial §3.7.2), and slow physics is parallel-split but with *piecewise-constant tendencies at per-process cadences* injected into the dynamical core mid-substep (vn, exner) and into transport (ρqx) — not summed and stepped by a generic integrator. Consequence: the composition layer adopts Tasmania's coupling algebra — `SequentialUpdateSplitting` for the fast suite, a lazy `ConcurrentCoupling` feeding the dycore's slow-tendency port for the slow suite — making ICON's operational arrangement one validated preset in a family that also contains PS, STS, and SSUS (§4.2).

**T2 — The dycore is not a component *of* the time loop; it is a time loop.** `solve_nonhydro` is a two-time-level predictor–corrector, sub-cycled `ndyn_substeps` times per Δt, with internal halo exchanges at substep boundaries, internal velocity-advection reuse between substeps, and vertically implicit sound-wave treatment. It cannot be decomposed into sympl `TendencyComponent`s without destroying it. Consequence: the dycore is *one* component — a `DynamicalCore` in Tasmania's sense, with the predictor–corrector as its stage structure and `ndyn_substeps` as its super-fast substep tier — whose interior is GT4Py programs (icon4py's `SolveNonhydro`); its double-buffering (nnow/nnew) and substep carry-over state are private, with a restart-serialization protocol (§4.5).

**T3 — Staggering and the dyn↔phy interface.** Prognostic winds live on edges (vn); physics operates on cell-center (u,v) reconstructions, and turbulence returns *increments* that are interpolated back to edges and added to vn (tutorial §3.7.3). sympl has no notion of mesh location. Consequence: property contracts gain a `location` axis; the RBF/edge2cell reconstructions and the increment-return path are explicit `DiagnosticComponent`s / component-internal steps, never hidden unit-conversion-style magic (§3.3).

**T4 — Distributed memory.** sympl's paper defers MPI entirely. ICON's step structure interleaves halo exchanges *inside* what symcon treats as single components (dycore substeps) and *between* components (after diffusion, before transport, etc.). Consequence: halo validity becomes field metadata; exchanges between components are auto-inserted or validated by a composition pass; exchanges inside components are declared (`communicates_internally=True`) and use the same GHEX patterns (§6).

**T5 — Units and dims coercion vs. zero-copy.** sympl's ergonomic superpower — silent unit conversion and dim reordering at component ingress — is a performance landmine on GPU. Consequence: canonical-units registry + strict mode: in production, any ingress that would allocate (unit conversion, transpose, host↔device) is an *error*, not a convenience (§2.4).

**T6 — Naming.** CF standard names are adopted where CF defines them, but ICON's internal quantities (exner, vn, θv, ddt_* tendency slots, interface-level variants) are largely outside CF scope — deliberately so, since CF avoids encoding solver-internal temporal/staging distinctions. Consequence: a variable registry with an `icon:` namespace, CF aliases where they exist, and sympl's `_on_interface_levels` suffix convention retained (§2.5).

**T7 — Mutation and privacy vs. functional purity.** ICON's sequential-update physics, the vault's in-place/slot-swap execution model, and §4.5's component-private state are all mutation-shaped; `jax.jvp`/`jax.vjp` require a pure function over explicit PyTrees. Consequence: differentiability is a *lowering*, not a rewrite — the same negotiated composition compiles to a pure step function (F-tier, §8.5) in which in-place updates become functional updates recovered by XLA buffer donation, and component-private state is surfaced as explicit carry; privacy is demoted to an imperative-tier convenience.

---

## 2. Layer 0 — State, fields, and the zero-copy protocol

### 2.1 The state dictionary

Exactly sympl's model: `state: dict[str, DataArray]` plus the required `time` key (`datetime`/`cftime`). One logical time level is exposed; multi-time-level schemes own their history privately (T2). The state is the *only* channel between components; components never share Python object references behind the state's back.

### 2.2 The field boundary type

State values are `xarray.DataArray`s whose `.data` is any object satisfying a minimal buffer protocol:

```python
@runtime_checkable
class FieldBuffer(Protocol):
    def __dlpack__(self, *, stream: int | None = None): ...
    def __dlpack_device__(self) -> tuple[int, int]: ...
    shape: tuple[int, ...]
    dtype: Any
```

In practice: `numpy.ndarray` (CPU) or `cupy.ndarray` (CUDA/HIP). JAX arrays are permitted as boundary buffers only in single-framework configurations (their immutability breaks the in-place-update contract that ICON's sequential physics relies on; see §8.4 — the functional lowering of §8.5 instead replaces that contract wholesale). The DataArray layer carries, in `dims`/`attrs`:

| metadata | values | consumed by |
|---|---|---|
| `dims` | `('cell'\|'edge'\|'vertex', 'height'\|'height_interface', …)` | ingress adapters, contract checks |
| `attrs['units']` | canonical unit string | contract checks (no-op in production) |
| `attrs['location']` | `cell` / `edge` / `vertex` (redundant with dims, kept explicit for scalars/sparse fields) | location typing |
| `attrs['halo']` | `VALID` / `DIRTY` | halo validator pass |
| `attrs['grid_uuid']` | uuidOfHGrid | provenance check: refuse to mix fields from different grids |

Horizontal layout is **flat unstructured** `(horizontal, vertical)` in row-major order, matching icon4py — ICON-Fortran's `nproma`/jb-jc blocking is deliberately *not* adopted; it is a CPU-cache artifact that GT4Py backends re-derive per target as a schedule decision, which is the whole point of separating algorithm from schedule.

### 2.3 Ingress adapters (zero-copy views)

Each compute framework gets a cached adapter that turns a boundary buffer into its native field type without copying:

- **GT4Py:** `gtx.as_field(domain, buffer)` with the domain derived from `dims` + the grid object's sizes; offset providers come from the grid (§3), never from the state.
- **JAX:** `jax.dlpack.from_dlpack(buffer)` for inputs; outputs are written back via a preallocated output buffer (donation is not relied on).
- **Numba/CuPy:** direct via `__cuda_array_interface__`.

Adapters are constructed once per (component, state-schema) pair at bind time — under the execution plan (§8.2) ingress is fully pre-resolved into bound argument packs, so per-step ingress cost is zero; in the interpreted tier it degrades gracefully to one dictionary lookup.

### 2.4 Contracts, canonical units, strict mode

Components keep sympl's `input_properties` / `tendency_properties` / `diagnostic_properties` / `output_properties`, extended with `location` and `halo`:

```python
class TurbulentDiffusion(Stepper):
    input_properties = {
        "air_temperature": {
            "dims": ["cell", "height"], "units": "K",
            "halo": "owned",           # computes on owned points only
        },
        "icon:normal_wind": {
            "dims": ["edge", "height"], "units": "m s-1", "halo": "required",
        },
        ...
    }
    output_properties = {
        "icon:normal_wind": {"dims": ["edge", "height"], "units": "m s-1",
                              "halo": "invalidated"},   # dirties the halo
        ...
    }
```

A **canonical-units registry** fixes one unit per variable name; components are required to declare canonical units, so sympl's Pint conversion path exists but compiles to a no-op. `ComputeContext(strict=True)` (default for production) turns any ingress that would allocate — unit conversion, dim transpose, dtype cast, host↔device transfer — into an exception with a diagnostic naming the offending component and field. `strict=False` restores full sympl ergonomics for interactive/educational use, which is a first-class use case, not a degraded mode.

### 2.5 Naming

CF standard names where CF has them (`air_temperature`, `air_pressure`, `specific_humidity`, …); `icon:`-namespaced names for solver-internal quantities (`icon:exner_function`, `icon:normal_wind`, `icon:virtual_potential_temperature`, `icon:ddt_vn_phy`, …); sympl's `_on_interface_levels` suffix for the `height_interface` dim variants. The registry is one Python module mapping canonical name ↔ ICON Fortran short name ↔ CF name (if any) ↔ GRIB2 discipline/category/parameter — the last column exists purely to make GRIB2 *ingestion* (§7.2) table-driven, not to promise GRIB2 output parity.

---

## 3. Layer 1 — Grid, geometry, metrics

### 3.1 `IconGrid`

One immutable object per horizontal domain, constructed by reading an ICON grid NetCDF file (the same files Zonda / the DWD grid generator produce), keyed by `uuidOfHGrid`:

```python
grid = icon_grid.from_file("icon_grid_0026_R03B07_G.nc", ctx)
grid.n_cells, grid.n_edges, grid.n_vertices        # local sizes (owned + halo when distributed)
grid.connectivities["C2E"], ["E2V"], ["C2E2C"], ["E2C2V"], ["V2E"], ...
grid.refin_ctrl                                     # retained even without nesting (future LAM/nests)
grid.geometry                                       # edge lengths, dual lengths, areas, orientation, coriolis
```

Connectivities are exposed in two forms from one storage: raw index arrays (for JAX segment-sum patterns and NumPy reference components) and GT4Py offset providers (for icon4py granules). The grid, not the state, owns topology — components receive the grid at *construction* time; the state stays pure data. This mirrors the Atlas-vs-GT4Py decomposition finding: mesh location, memory layout, and communication are orthogonal concerns, not bundled into one FunctionSpace-like object.

### 3.2 Vertical grid and derived fields

`VerticalGrid` holds `vct_a/vct_b`, nlev, flat/rayleigh levels, and the SLEVE or Gal-Chen decay parameters. Two factories — `MetricsFactory` and `InterpolationFactory` (directly the icon4py `metrics`/`interpolation` field factories) — compute the 3D metric terms (`ddqz_z_*`, `wgtfac_*`, reference-state fields) and interpolation coefficients (RBF vectors, cell→edge/edge→cell weights, nudging coefficients) once at startup. Their outputs are ordinary DataArrays stored in a read-only `static_state` dict that components may request in `input_properties` like any other field; being static, they are exempt from halo tracking.

### 3.3 Staggering as API, not convention

Because `location` is contract-checked, the dyn↔phy reconstruction becomes visible architecture instead of buried convention: a `WindReconstruction` `DiagnosticComponent` (edges→cells, RBF) runs before the physics suite; the turbulence component's edge-located output is the *increment path* (cell-center increments interpolated back to edges inside the component, per tutorial §3.7.3), declared in its output properties. Nothing in the framework silently regrids between locations.

---

## 4. Layer 2 — Component taxonomy

### 4.1 Preserved sympl kinds

`DiagnosticComponent`, `TendencyComponent`, `ImplicitTendencyComponent`, `Stepper`, `Monitor`, and the wrapper concept survive unchanged in semantics (property contracts, `array_call`-style core methods, first-class usability outside any model — the ability to call `SaturationAdjustment()(state)` interactively is retained and is a genuine research affordance, as the sympl paper argues).

### 4.2 The coupling algebra (after Tasmania)

Rather than inventing ad hoc containers for ICON's two coupling styles, symcon adopts — with attribution — the composition layer of Ubbiali's Tasmania framework, which extended sympl with exactly the general machinery this layer needs: a family of *federation classes*, each realizing one of the six coupling strategies whose truncation-error and stability properties the thesis analyzes under weak assumptions (independent of the governing equations, the number of parameterizations, and the internals of the time-steppers). Adopting the algebra buys two things at once: ICON's operational coupling stops being hard-wired structure and becomes one *validated preset*, and every other point of the algebra becomes available for the coupling-scheme experimentation that production codes structurally cannot do — which was Tasmania's raison d'être.

**The operator vocabulary.** All operators consume the same property-contracted components of §4.1 and are themselves components (they compose):

- **`ConcurrentCoupling(comps)`** — Tasmania's heterogeneous composite over `TendencyComponent`s and `DiagnosticComponent`s: sums tendency contributions, unions diagnostics in declared order. It is the building block of full coupling (FC: evaluate at every integrator stage) and lazy full coupling (LFC: evaluate once per step and hold constant — COSMO's operational choice, and, when the "hold" is stretched over N steps by `CallingFrequency`, ICON's slow-physics choice).
- **`TendencyStepper`** — kept in its Tasmania form: a *registry-based* integrator family (`"forward_euler"`, `"rk2"`, `"rk3ws"`, …; name-keyed `Factory`/`MetaFactory` registration, so user-defined steppers are first-class citizens of any downstream federation) wrapping a `ConcurrentCoupling` or bare `TendencyComponent`. Its sibling **`SequentialTendencyStepper`** implements the two-input-state signature `E(ψⁿ, Δt; P + (ψ_prov − ψⁿ)/Δt)` that makes STS expressible — the accumulated provisional tendency of upstream processes enters as a constant forcing.
- **`ParallelSplitting(sections)`** — each section integrated independently from ψⁿ; the recombination ψⁿ⁺¹ = Σₗ ψₗⁿ⁺¹ − L·ψⁿ (Tasmania's `DataArrayDictOperator` step) compiles, in the execution plan, to a single fused multi-axpy vault op.
- **`SequentialTendencySplitting(sections)`** — the STS chain of `SequentialTendencyStepper`s, dynamics first, then physics ideally ordered slowest→fastest (Beljaars' constant-forcing argument, with the thesis's caveat that ranking atmospheric time scales is genuinely hard).
- **`SequentialUpdateSplitting(sections)`** — the SUS chain: each process corrects the state left by its predecessor. Sections may be bare `Stepper`s (adjustment-type components like saturation adjustment enter directly) or `(TendencyComponent, stepper_name)` pairs resolved through the registry. Ordering is explicit and validated against declared `must_follow`/`must_precede` constraints; ICON's fixed fast-physics order ships as `NWP_FAST_ORDER`, including the surface-transfer-at-end time-level optimization documented in the tutorial.
- **`SSUS(sections, core, lam=0.5, pre_steppers=None)`** — the symmetrized/Strang composition: sections traversed in reverse over λΔt, the core over Δt, sections forward over (1−λ)Δt, with per-side stepper choice (Eₗ* ≠ Eₗ is legal, per thesis §2.3.5). λ = ½ is the only choice with second-order coupling error regardless of problem structure; the operator exists because symcon should be able to *measure* what that costs and buys on a real dycore.
- **`DynamicalCore`** — Tasmania's base class for two-time-level, multi-stage cores, with three cadence tiers whose terminology Tasmania itself borrowed from ICON: a **slow-tendency input port** (tendencies computed outside, consumed inside at the point the core's numerics dictate); an optional per-stage **fast-tendency `ConcurrentCoupling`** (FC *within* the core, invoked at every stage); and a **super-fast substep tier** with its own hook. `NonhydroSolver` derives from it: the predictor–corrector is the stage structure; `ndyn_substeps` (with the CFL-adaptive ratio provider, escalation bounded at 12) is the super-fast tier; the per-stage fast slot is *empty in the ICON preset* but is the natural experiment port (e.g., per-substep saturation adjustment or microphysics — precisely the kind of question the coupling literature keeps open). The generic `Subcycle` combinator survives for uses outside the core (tracer-transport call-frequency reduction); the dycore's own substepping now lives inside its `DynamicalCore` structure.

**The bus, reframed.** The v1.0 `SlowTendencyBus` survives unchanged in mechanics but is now recognized as the naming-and-checking convention for the `DynamicalCore` slow-tendency port: slow processes publish piecewise-constant tendencies into `icon:ddt_*` slots under `CallingFrequency` (LFC's lazy evaluation stretched over N steps), the dycore and transport declare those slots as inputs, and the composition-time check that every published tendency has exactly one consumer is retained verbatim.

**The ICON-NWP preset, in algebra terms:** per Δt — dyn→phy diagnostics; `ConcurrentCoupling` of `CallingFrequency`-wrapped slow processes publishing to the bus; `NonhydroSolver(DynamicalCore)` consuming the bus in its substeps; horizontal diffusion; tracer transport consuming the ρqₓ bus slots; `SequentialUpdateSplitting(NWP_FAST_ORDER)`. Presets carry a **validated / experimental** label; only validated presets inherit the scientific-equivalence claim of §9.

**Adopted sympl-fork engineering.** Ubbiali's fork of sympl contributed several mechanisms that symcon adopts outright — two of which v1.1 of this document had independently reinvented, which is worth flagging as convergent evidence:

- The **object-oriented component ABI**: `__call__(state, *, out=None)` with caller-provided output DataArrays, `array_call(inputs, outputs)` receiving both input *and output* raw buffers, and `allocate_*` hooks for framework-side allocation. Caller-provided outputs are exactly what the execution plan's preallocated buffers and slot-swap machinery require, so T0 and T1–T3 share one ABI instead of the plan bolting a second calling convention onto sympl components.
- The **Checker/Operator decomposition** with *static* variants (component-definition information only) and *dynamic* variants (crossing definitions with actual data): this is the internal structure of symcon's negotiation phase — static checkers at composition time, dynamic checkers and operators at bind time, neither on the step path. Ubbiali's "disable runtime checks" switch is subsumed by the tier system.
- **`Factory`/`MetaFactory` name-keyed registries** (subclasses self-register on import): used for tendency steppers, physics-scheme selection, and backends, so configuration strings resolve declaratively through registries rather than if-ladders.
- **Avoidance of axis permutations that coerce duck arrays** to `numpy.ndarray` — subsumed by, and one of the original motivations validated by, strict mode (§2.4).

**Not adopted:** Tasmania's Cartesian spatial-domain machinery (`HorizontalBoundary`, `Topography` registries) — the ICON grid layer (§3) owns that ground on the icosahedron — and Tasmania's multi-backend stencil-dispatch infrastructure, which symcon replaces with the `ComputeContext`/ingress-adapter design of §2 and §5.2.

### 4.3 The ICON-NWP → symcon mapping

| ICON process | symcon class | cadence | implementation source | notes |
|---|---|---|---|---|
| `solve_nonhydro` (predictor–corrector, vertically implicit) | `NonhydroSolver(DynamicalCore)`; substep tier = `ndyn_substeps` (CFL-adaptive) | Δτ | icon4py `solve_nonhydro` | consumes `icon:ddt_vn_phy`, `icon:ddt_exner_phy` via the slow port; `communicates_internally=True`; private nnow/nnew + velocity-advection carry-over; per-stage fast slot empty in preset |
| horizontal diffusion | `HorizontalDiffusion(Stepper)` | Δt | icon4py `diffusion` | Smagorinsky + background 4th-order |
| tracer transport (FFSL horiz. + PPM vert., directional split) | `TracerTransport(Stepper)` | Δt | icon4py `advection` | applies `icon:ddt_qx_phy` post-horizontal-transport; per-tracer scheme config; reduced calling frequency (§3.6.4) via `Subcycle` inverse (substep_ratio) |
| saturation adjustment (×2) | `SaturationAdjustment(Stepper)` | Δt | icon4py / port | appears twice in `NWP_FAST_ORDER` |
| TERRA (land), FLake, sea ice | each a `Stepper` | Δt | port from ICON Fortran | tiled surface; old-time-level input semantics honored by suite ordering |
| turbulent diffusion (turbdiff) | `TurbulentDiffusion(Stepper)` | Δt | port | implicit vertical solve; increment path back to edges |
| microphysics (one-moment graupel) | `Microphysics(Stepper)` | Δt | muphys-cpp bindings or GT4Py port | scheme-selectable |
| surface transfer | `SurfaceTransfer(Stepper)` | Δt | port | called last (tutorial note), consistent time levels |
| convection (Tiedtke–Bechtold) | `ImplicitTendencyComponent` under `CallingFrequency(dt_conv)` | dt_conv | port (large) | publishes to tendency bus |
| cloud cover | `DiagnosticComponent` under `CallingFrequency(dt_conv)` | dt_conv | port | diagnostic cloud fields for radiation |
| radiation | `TendencyComponent` under `CallingFrequency(dt_rad)` + `ReducedGridWrapper` | dt_rad | **pyRTE-RRTMGP (primary, GPU-capable)**; ecRad via CFFI as validation reference | fluxes → heating at constant volume (c_v) |
| non-orographic GWD | `TendencyComponent` under `CallingFrequency(dt_gwd)` | dt_gwd | port | tendency bus |
| SSO drag (Lott–Miller) | `TendencyComponent` under `CallingFrequency(dt_sso)` | dt_sso | port | tendency bus |
| p, T diagnosis (hydrostatic pressure integration) | `HydrostaticPressureDiagnostics(DiagnosticComponent)` | Δt | port of §3.7.3 recipe | the dyn→phy interface, explicit |
| wind reconstruction edges→cells | `WindReconstruction(DiagnosticComponent)` | Δt | icon4py interpolation | RBF |
| IAU | `IncrementalAnalysisUpdate(TendencyComponent)` | Δt within window | new | weighted increments; iterative IAU is a driver recipe (re-run loop), not v1 |

The isochoric (constant-volume) coupling convention — heating rates converted with c_v, hydrostatically integrated pressure for physics — is a stated *suite-wide contract* documented on the tendency bus slots, since it is exactly the kind of invisible convention that corrupts ported schemes inherited from constant-pressure hosts.

### 4.4 What is deliberately *not* decomposed

Inside `NonhydroSolver`, the ~50 stencil programs of the predictor/corrector are GT4Py programs (icon4py's existing granule structure, including its hand-fused program variants where launch count matters), not symcon components. The component boundary is drawn where scientific recomposition is plausible (swap a microphysics scheme, reorder physics, disable convection) — not at the stencil level, where recomposition is a performance/correctness hazard and GT4Py already provides the right abstraction. This two-granularity picture (component = scheme at the composition layer; stencil = unit of scheduling below it) matches the cross-model finding that modern rewrites moved the unit of *optimization* to the stencil while the unit of *composition* stays the scheme.

### 4.5 Component-private state and restart

Components may hold private persistent fields (dycore time levels and substep carry-overs, turbulence TKE history if configured, radiation's stored fluxes between calls, `CallingFrequency`'s cached tendencies and phase). The contract: implement `restart_state() -> dict[str, DataArray]` and `load_restart_state(d)`. `RestartMonitor` serializes the public state + every component's private state + full config + grid UUIDs; restart reproducibility (same trajectory across a restart, ICON's standard requirement) is a CI-enforced property.

---

## 5. Layer 3 — Composition and the time loop

### 5.1 The canonical run script

The primary UX is a legible run script, per sympl. The complete global NWP configuration:

```python
from symcon import (ComputeContext, ConcurrentCoupling, SequentialUpdateSplitting,
                    CallingFrequency, ReducedGridWrapper)
from symcon.grid import icon_grid, vertical_grid, extpar
from symcon.init import from_dwd_analysis
from symcon.components import *          # the table in §4.3
from symcon.io import ZarrMonitor, RestartMonitor

ctx   = ComputeContext(backend="gtfn_gpu", comm=MPI.COMM_WORLD,
                       io_ranks=4, strict=True)
grid  = icon_grid.from_file("icon_grid_0026_R03B07_G.nc", ctx)        # decomposes if comm.size > 1
vgrid = vertical_grid.sleve(nlev=90, ...)
static = extpar.load("extpar_0026_R03B07_G.nc", grid) | metrics(grid, vgrid) | interpolation(grid)

cfg   = NWPConfig(dtime=timedelta(seconds=180), ndyn_substeps=5,
                  dt_rad="1h", dt_conv="9min", dt_gwd="9min", dt_sso="9min")

state = from_dwd_analysis(fg="fc_R03B07+0000.grb", an="an_R03B07.grb",
                          grid=grid, vgrid=vgrid, ctx=ctx, mode="iau")

dycore    = NonhydroSolver(grid, vgrid, static, cfg.dynamics, ctx,
                           substeps=cfl_adaptive(base=cfg.ndyn_substeps, max_ratio=12))
diffusion = HorizontalDiffusion(grid, static, cfg.diffusion, ctx)
transport = TracerTransport(grid, static, cfg.transport, ctx)

fast = SequentialUpdateSplitting(NWP_FAST_ORDER, dict(
          satad=SaturationAdjustment(...), land=Terra(...), lake=FLake(...),
          seaice=SeaIce(...), turb=TurbulentDiffusion(...),
          mphys=Microphysics(scheme="graupel", ...), sfc=SurfaceTransfer(...)), ctx)

slow = ConcurrentCoupling(
        CallingFrequency(Convection(grid, ...), cfg.dt_conv),
        CallingFrequency(CloudCover(grid, ...), cfg.dt_conv),
        CallingFrequency(ReducedGridWrapper(Radiation(rte_rrtmgp_cfg), rrg_pair(grid)), cfg.dt_rad),
        CallingFrequency(NonOrographicGWD(...), cfg.dt_gwd),
        CallingFrequency(SSODrag(...), cfg.dt_sso))

iau     = IncrementalAnalysisUpdate(window="3h", increments=state.pop_increments())
diag_pT = HydrostaticPressureDiagnostics(grid, vgrid)
recon   = WindReconstruction(grid, static)

monitor = ZarrMonitor("run.zarr", every="1h", variables=OUTPUT_SET, ctx=ctx)
restart = RestartMonitor("restart/", every="12h", ctx=ctx)

with ctx.timeloop(state, until=cfg.run_length) as loop:
    for dt in loop:
        state.update(diag_pT(state))                 # dyn→phy diagnostics
        state.update(recon(state))                   # vn → (u,v) at cells
        tend, diag = slow(state, dt)                 # lazy, piecewise-constant → icon:ddt_* bus
        state.update(diag); state.update(tend)
        state.update(iau(state, dt))
        state = dycore(state, dt)                    # consumes vn/exner bus slots; internal halos
        state = diffusion(state, dt)
        state = transport(state, dt)                 # consumes ρqx bus slots post-advection
        state = fast(state, dt)                      # sequential updates
        monitor.store(state); restart.store(state)
        state["time"] += dt
```

Every claim the sympl paper makes about legibility survives: which schemes, what order, what cadences, where output happens — all in one screen. (`Model`/`Federation`-style convenience wrappers exist for education, assembling exactly this loop from `cfg`; they add nothing architecturally.)

The coupling algebra makes scheme experiments equally legible. Swapping the fast-physics coupling from operational SUS to Strang splitting around the dry step is a three-line change, not a fork:

```python
dry  = chain(dycore, diffusion, transport)                      # E0 in thesis notation
step = SSUS(sections=fast.sections, core=dry, lam=0.5)          # E*_l over λΔt, reversed; E0; E_l over (1-λ)Δt
# loop body: bus publication as before, then `state = step(state, dt)`
```

Composition-time constraint checking (§4.2, risk 7 of §11) decides whether such a composite is merely *structurally* legal or also scientifically admissible; experimental composites never inherit the validated-preset label.

### 5.2 `ComputeContext`

The one object threaded through construction: array namespace + allocator (numpy/cupy, pooled), GT4Py backend selection (`gtfn_cpu`, `gtfn_gpu`, `embedded` for debugging), MPI communicators (compute / I/O split, §6.4), decomposition handle, strict-mode flag, execution tier (`interpret` / `plan` / `graph` / `native`, §8.3), and the plan compiler (§8.2). Components allocate their private fields through it; the state initializer allocates public fields through it. Nothing else in the system touches devices or communicators directly.

### 5.3 Configuration

Typed, layered, Pythonic: frozen dataclasses per component (`DiffusionConfig`, `TransportConfig(tracer_schemes={"qv": "ffsl_miura", ...})`, …) composed into `NWPConfig`; YAML/TOML ingestion is a thin loader into the same dataclasses; validation at construction (ranges, cross-field constraints like the dt_rad/dt_conv multiple rule). No namelist emulation layer in v1 — but the registry (§2.5) plus per-config `icon_namelist_origin` annotations document, field by field, which ICON namelist variable each option corresponds to, so a future `from_namelist()` adapter is a table walk, not archaeology. Full config + grid UUIDs + package versions + git SHAs are stamped into every output artifact (the reproducibility story sympl promises, made enforceable).

---

## 6. Layer 4 — Distributed execution

### 6.1 Decomposition

`decompose(grid, comm)` partitions cells (METIS or ICON's geometric decomposition — pluggable), derives edge/vertex ownership by the usual adjacency rules, and builds `DecompositionInfo`: owned/halo index sets per location type, halo levels (two cell rows, matching ICON's stencil depth requirements), and global↔local index maps. The result is a *local* `IconGrid` (local connectivity tables with halo entries) plus exchange metadata — components are SPMD and see only local grids; nothing in any component's numerics is decomposition-aware.

### 6.2 GHEX substrate and `CommunicationComponent`

One GHEX unstructured domain descriptor and pattern per location type (cell/edge/vertex) and halo depth, built once from `DecompositionInfo` and cached on the context. `HaloExchange(fields=[...])` is a component: input properties = the fields with `halo: DIRTY`, output = same fields `halo: VALID`; its `array_call` posts one fused GHEX exchange for all listed fields (message aggregation matters at scale). GPU-aware MPI is assumed available and verified at startup; the fallback path stages through pinned host buffers with an explicit startup warning.

### 6.3 The halo validator pass

At composition time (`ctx.timeloop(...)` entry), symcon walks the loop's component sequence symbolically: each component's declared `halo: required` inputs are checked against the running validity map produced by predecessors' `halo: invalidated`/`valid` outputs. Two modes: `halos="auto"` inserts minimal `HaloExchange` components at the latest valid point (and reports the inserted schedule); `halos="manual"` (production default) only *verifies* hand-placed exchanges and fails loudly on a gap or a redundant exchange. Components with `communicates_internally=True` (the dycore) assert their own postconditions. This pass is the single most valuable safety net the architecture adds over hand-rolled MPI hosts: halo staleness bugs become composition-time errors.

### 6.4 I/O and restart ranks

ICON's worker/output-server split is reproduced as communicator topology, not process zoo: `ComputeContext` splits `comm` into a compute communicator and an I/O communicator (`io_ranks`). Monitors run a nonblocking gather-or-forward: on `store()`, compute ranks post sends of their owned slices (with global index maps) to I/O ranks and return immediately; I/O ranks assemble and write NetCDF or Zarr (region-writes with a global chunk map — Zarr makes the parallel-write path far simpler than NetCDF and is the recommended default). `RestartMonitor` uses the same machinery on its own cadence (the `num_restart_procs` analog). Asynchrony is bounded by a two-deep buffer; backpressure blocks the loop rather than exhausting memory.

---

## 7. Layer 5 — Ingestion, initialization, output

### 7.1 What is ingested vs. what is emitted

Per the agreed reconciliation: symcon *reads* ICON's artifact ecosystem — grid NetCDF (§3.1), ExtPar NetCDF (topography incl. SSO fields, land-use tiles, soil, climatologies), DWD analysis/first-guess and IFS initial data in GRIB2 — and *writes* Pythonic artifacts (Zarr/NetCDF with CF-compliant metadata where applicable). No GRIB2 output, no namelist reading in v1.

### 7.2 GRIB2 ingestion

A thin `eccodes`-based reader driven by the variable registry's GRIB2 columns: shortName/level-type → canonical name + vertical placement; fields land directly in device-resident DataArrays via the context allocator. Horizontal remapping from IFS grids is **out of scope** (external preprocessing with `iconremap`/`earthkit-regrid` documented as the supported path); ingestion assumes data already on the target ICON grid, exactly like ICON itself after remap.

### 7.3 Initialization modes

`from_dwd_analysis(mode="uninitialized" | "iau" | "initialized")` and `from_ifs_analysis(...)` reproduce tutorial ch. 5's start modes: construct the prognostic set (vn from u/v via edge projection where needed, exner/θv from p/T, hydrostatic balancing of the reference state), stash IAU increments when `mode="iau"` for the `IncrementalAnalysisUpdate` component. Idealized initializers (Jablonowski–Williamson, Straka) are `DiagnosticComponent`-shaped functions used by the validation ladder (§9).

### 7.4 Monitors

`ZarrMonitor` (default; anemoi-conformant layout available as a flag — this is the cheap end of the ICON4Py↔anemoi roadmap and falls out of the design nearly for free), `NetCDFMonitor` (CF-ish, xarray-written), `RestartMonitor`, and a `PlotMonitor` for education. Output-set definitions are named variable lists with optional on-the-fly derived diagnostics (declared as `DiagnosticComponent`s evaluated on I/O ranks when their inputs are cell-located and local, else on compute ranks).

---

## 8. Execution architecture: performance tiers and differentiability

### 8.1 The honest problem statement

The sympl boundary (dict lookups, DataArray attribute traffic, per-call contract matching, wrapper hops, Python control flow) costs microseconds per component call — and inside components, per-stencil Python launches cost more. At climate-toy scale that is invisible; at production ICON scale on GPUs — where a full Δt step is tens of milliseconds and a dycore substep is single-digit milliseconds — interpreted per-step dispatch of ~20 components plus halo logic plus hundreds of kernel launches is a hard ceiling on strong scaling. Two orthogonal observations structure the solution: (a) *nothing about the interfaces changes during execution* — the state schema, buffer set, component sequence, ingress plans, and halo schedule are all fixed at composition time, so every lookup performed in the loop is recomputing an invariant; (b) once (a) is exploited, the residual cost is pure dispatch — Python function calls and kernel-launch latency — which is a runtime problem (graph replay, native driver), not a compiler problem. Neither requires whole-program dataflow compilation, which is why no DaCe-style SDFG orchestration appears anywhere in this design.

### 8.2 Bind-time specialization: negotiation vs. execution phases

The full sympl machinery — name resolution, dims/units matching, Pint no-op verification, location and halo checks, xarray wrapping — runs exactly once, at **bind time** (entry of `ctx.timeloop(...)`), against the composed sequence and a schema-representative state. Its product is a frozen **execution plan**; nothing sympl-shaped executes per step.

**`StateVault`.** The state's execution-phase form is a dense, slotted container: a flat `list` of raw buffers plus an interned `name → index` map consulted only at bind time. Fields are referenced by handles:

```python
@dataclass(frozen=True, slots=True)
class FieldHandle:
    idx: int
    name: str          # debug/repr only

class StateVault:
    __slots__ = ("buffers", "names", "schema_hash", "epoch")
```

The public dict-of-DataArrays view still exists — as a lazily materialized façade over the vault (DataArray wrappers cached per slot, reconstructed only on epoch change) — so monitors, interactive inspection, and the interpreted tier see unmodified sympl semantics. xarray is thereby confined to negotiation, monitoring, and debugging; it never appears on the step path.

**Bound calls.** For each component, bind time produces a specialized entry: the ingress adapters of §2.3 are resolved to concrete zero-copy views, argument order is fixed, and the result is a plain tuple pack — deliberately a `tuple`/`NamedTuple` rather than anything richer, because tuple indexing is the cheapest structured access CPython offers and the pack is built once:

```python
class BoundCall(NamedTuple):
    fn: Callable            # the component's raw kernel entry (array_call specialized)
    args: tuple             # pre-resolved buffers / gt4py fields / scalars
    tag: str                # profiling/debug label
```

**Buffer identity and the "new state" problem.** sympl `Stepper`s notionally return fresh dicts; a zero-lookup plan requires stable buffer identities. The plan therefore pre-allocates all component outputs — delivered through the `__call__(state, out=...)` / `array_call(inputs, outputs)` ABI adopted from Ubbiali's sympl fork (§4.2) — and encodes state evolution as either in-place updates (the common case under ICON's sequential-update physics) or **slot swaps**. Swaps are not indirected at runtime: for every ping-pong pair the compiler emits **even/odd plan variants** with references pre-bound, and the interpreter alternates variants — zero per-step indirection, at the cost of 2× plan memory (kilobytes).

**Wrapper and federation compilation.** Wrappers that are pure control flow dissolve into the plan: `CallingFrequency` becomes a per-step **cadence mask** (the plan precomputes, from the lcm structure of Δt/dt_conv/dt_rad/dt_gwd/dt_sso, the small set of distinct *step signatures* and the op list active under each); `Subcycle` and the `DynamicalCore` substep tier unroll or loop with pre-bound dt/n; scaling-type wrappers fold into bound constants. The federation classes of §4.2 dissolve identically, being pure control flow over their sections: `SequentialUpdateSplitting` flattens into the op list; `ParallelSplitting`'s recombination ψⁿ⁺¹ = Σψₗ − L·ψⁿ compiles to one fused multi-axpy vault op over the affected slots; `SequentialTendencySplitting`'s provisional-tendency forcings become dedicated vault slots plus a diff-and-scale op feeding each `SequentialTendencyStepper`; `SSUS` simply doubles the op list with reversed section order and λ-scaled dt constants. Wrappers that do real compute (`ReducedGridWrapper`) remain ordinary bound calls. `HaloExchange` components bind to pre-built GHEX bulk-exchange handles (pattern + field set frozen), so an exchange is one FFI call.

**Why not a dataclass state?** The schema is configuration-dependent (the tracer set alone varies), so no static dataclass can be the public state type. Where typed attribute access is genuinely wanted — component-internal views, tests — the bind phase can emit a generated slotted dataclass (`dataclasses.make_dataclass(..., slots=True)`) over vault slots; but inside the plan, handles and tuples beat slot-descriptor access anyway, so this is an ergonomic option, not the mechanism. For scale: a dict lookup is ~40–60 ns and slotted attribute access ~20–40 ns, but those were never the real cost — the µs-scale per-field DataArray construction, attrs traffic, and sympl match/convert logic are, and phase separation removes them categorically rather than shaving constants.

**Staleness guards.** The plan is valid for one (composition, schema, decomposition) triple, enforced by `schema_hash` + an epoch counter bumped by any out-of-band state mutation through the façade; a stale plan raises at the next step rather than silently binding dead buffers. Debug builds re-run negotiation every N steps and diff against the plan.

### 8.3 Execution tiers (DaCe-free orchestration)

Four tiers over one composition model, ordered by implementation cost; all share the plan from §8.2, and CI enforces cross-tier agreement to validation tolerances on the idealized suite.

**T0 — interpreted sympl dispatch.** Full per-call contract machinery, dict/DataArray semantics. Reference behavior; education and component development.

**T1 — plan interpreter.** A Python loop over `tuple[BoundCall, ...]` per step signature. No dict, no xarray, no contract logic; per-component overhead drops to one Python call + tuple splat (order 1 µs), i.e. tens of µs per Δt step for the component layer. This is the default production tier on CPU and the development tier on GPU.

**T2 — graph replay.** On CUDA/HIP, the plan interpreter is run once per step signature under stream capture (CuPy exposes `begin_capture`/`end_capture`); each **exchange-free segment** of the plan becomes a captured graph, replayed thereafter with a single launch (µs-scale, independent of interior kernel count). Segments are delimited by GHEX exchanges, Fortran bridge calls, and framework seams, because host-side MPI cannot sit inside a capture; the per-step Python cost collapses to (number of segments) × (one graph launch + one exchange call). The adaptive `ndyn_substeps` escalation and slow-physics cadences are handled by the signature cache — the signature set is small and bounded (substep ratio ∈ [5..12] × cadence phases), so graphs are captured lazily and reused. Requirements this imposes, checked at bind: static shapes, stable buffer pointers (guaranteed by the vault), no data-dependent host branching inside segments (the CFL decision reads back one scalar per step, *between* segments). HIP graph support via CuPy is flagged experimental — verified at startup, with T1 fallback.

**T3 — generated native host driver.** For the last factor — removing Python from the step entirely, and serving CPU targets where graphs don't apply — the bind phase can emit a small C++ translation unit that sequences the step directly: GTFN-compiled programs are C++ entry points in shared objects (the Python bindings are a convenience layer, not the interface), GHEX is native C++, and Fortran bridges have C ABI. The generated driver is a few hundred lines of calls with baked-in pointers, strides, cadence branches (`if (step % k == 0)`), and the even/odd swap logic; it is compiled once at bind (cached by plan hash) and exposed as one symbol: `step(vault, step_index)`. Python then makes one FFI call per Δt — or per output interval. ML/JAX components and any Python-only component return control to Python at their seam, segmenting the driver exactly as they segment T2 graphs. T3 is an escalation path, not a prerequisite: T2 is expected to reach within noise of a native driver on GPU, so T3 is built only if profiling of T1/T2 says so, and its scope can stay limited to the hottest region (the sub-cycled dycore + diffusion + transport block).

**The fusion question, answered without DaCe.** What SDFG orchestration would have bought beyond dispatch removal is *inter-kernel* fusion across stencil boundaries. That lever is retained at the code level rather than the compiler level: gt4py programs may contain multiple field operators, and icon4py already maintains hand-fused program variants for launch-bound regions of solve_nonhydro; coarsening granule programs is the sanctioned way to cut kernel count. The residual loss — automatic cross-component fusion — is accepted and quantified: with T2/T3 the cost of an unfused boundary is one kernel launch (~5 µs amortized to ~0 under graph replay) plus a possible missed memory-locality win; the latter is real but second-order next to the halo-exchange and dycore-interior costs that dominate ICON's step, and it can be recovered case-by-case by fusing at the gt4py program level where profiles justify it.

**A note on precompiled gt4py entry points.** Both T1 (call overhead) and T3 (C++ linkage) lean on gt4py.next's compiled-program path — pinning offset providers, shapes, and scalar-vs-field argument status at compile time so the per-call marshalling disappears. That API surface has been evolving (compile-time connectivities, static-args variants); the design treats it as a bind-time detail behind the ingress adapter, but the exact pinning mechanism should be re-verified against the current gt4py.next release before implementation — sketch-status, not pinned.

### 8.4 Multi-framework components

The boundary protocol admits JAX or Numba components (e.g., an ML parameterization replacing convection — the anemoi-adjacent use case). Rules: DLPack ingress is zero-copy but read-only-by-convention; JAX components must be functional at the boundary (inputs → new output buffers written back by the adapter into pre-registered vault slots), never in-place; a framework seam is a segment boundary in T2/T3 (graphs and the native driver stop and resume around it); stream/queue synchronization at seams is the adapter's job (DLPack stream argument, external-stream interop). Inside its segment a JAX component is free to be one jitted function — its own internal fusion story — which composes cleanly with this tiering. These rules are the state/data-boundary principle applied inside a single model; a JAX component honoring them is automatically `differentiable: "native"` under the §8.6 contract.

### 8.5 The functional lowering (F-tier)

`ctx.functional(composition, window=...)` is a fourth consumer of the §8.2 negotiation. Instead of an imperative op list it emits a pure JAX function over explicit PyTrees:

```python
step_fn: (StateTree, ParamTree, StaticArgs) -> StateTree          # one Δt, traced
window  = scan_window(step_fn, n_steps, remat="per_step")          # lax.scan + jax.checkpoint policy
loss_grads = jax.vjp(lambda p: J(window(state0, p)), params)       # or jax.jvp for tangent-linear
```

`StateTree` is a generated frozen-dataclass PyTree derived from the vault schema (one leaf per slot), extended with **explicit carry**: every leaf a component declared in `functional_state()` — dycore time levels and velocity-advection carry-over, `CallingFrequency` tendency caches, turbulence history — is surfaced into the tree (tension T7: §4.5's privacy is an imperative-tier convenience, demoted here by contract). The semantic mapping from the plan is mechanical: in-place updates become functional updates whose memory cost `donate_argnums` recovers under `jit`; even/odd slot swaps become tuple rebinding with zero post-trace cost; cadence masks become per-step boolean masks with `jnp.where` selecting cached-vs-recomputed slow tendencies (the cache being carry), which keeps the trace static across step signatures. Two declared freezes: the CFL-adaptive substep ratio is pinned to a static value in F-tier configurations (differentiating through discrete ratio switching is ill-posed, and the freeze is recorded in provenance, never silent), and monitors/restart are outside the trace (`io_callback` permitted only outside differentiated regions).

A pleasant inversion: under `jit`, XLA performs precisely the cross-component fusion the imperative tiers renounce (§8.3) — the differentiable path is incidentally the most aggressively fused one, paid for in XLA compile times and in XLA's weaker fit to icosahedral indirect addressing, where the required idiom is flatten + `segment_ids` + padded neighborhoods for the connectivity gathers.

### 8.6 The differentiability contract

Property contracts gain two axes: `differentiable: "native" | "custom" | "none"`, and a `params` declaration exposing tunable scheme constants (entrainment coefficients, autoconversion thresholds, …) as a `ParamTree` distinct from state — parameter estimation and gradient-based calibration never smuggle constants through state fields.

- **`native`** — the component provides a pure `functional_call(inputs, params) -> outputs` co-located with its imperative kernel, both drawing on one shared scheme-constants module (single source of numerical truth; CI holds the pair together with the same ladder-level-2 tolerances as the kernel itself). Traced directly; `jvp`/`vjp` for free. A JAX component under the §8.4 seam rules is automatically `native`.
- **`custom`** — the primal stays GT4Py: the gtfn kernel is registered as an XLA FFI target (`jax.ffi.ffi_call`; young API, pinned under §8.3's discipline) and paired via `jax.custom_vjp`/`jax.custom_jvp` with hand-written tangent/adjoint GT4Py programs. This is the classical adjoint-stencil route of operational 4D-Var, made per-component and composable. Implicit structure gets implicit-function-theorem treatment rather than unrolling: the adjoint of the turbulence vertical implicit solve is the transposed tridiagonal solve; saturation adjustment's fixed point differentiates through `lax.custom_root`-style rules, not through recorded Newton iterations — which also sidesteps `while_loop`'s reverse-mode prohibition.
- **`none`** — bridges and unported schemes. Per differentiated region, composition-time policy is `error` (default) or `stop_gradient` — explicit, warned, and stamped into provenance. Gradient truncation is never silent.

Numerical guidance ships as documentation-with-tests: `where`-branching and thresholds yield subgradients (legitimate, but characterized in L8); hard positivity clips truncate sensitivities and differentiable configurations should prefer smooth clamps; fp64 is the default for gradient work.

### 8.7 Differentiable distributed execution

Halo exchange is linear in the field values, which settles both directions at once: the **JVP** of an exchange is the same exchange applied to tangents; the **VJP** is the *transpose*, not the exchange run backward — cotangents accumulated on ghost points scatter-**add** onto the owning ranks' interior points, after which the ghost region of the cotangent is zeroed. Both rules derive mechanically from `DecompositionInfo` (swap the send/recv index sets; switch the write mode to accumulate) and are registered via `custom_vjp`/`custom_jvp` on a `DifferentiableHaloExchange`, which the F-tier substitutes at every point the halo validator would place a `HaloExchange`. Implementation path: mpi4jax point-to-point first (existing jit/token integration), GHEX behind `jax.ffi` with stream-correct custom calls when performance demands it — closing the known gap that GHEX has no JAX/XLA autodiff integration. Execution stays SPMD: one `jit` per rank over the local domain, MPI underneath; no single-controller `shard_map` construction is attempted for the unstructured pattern. Reverse-mode memory over a window is managed by the `lax.scan` + per-step `jax.checkpoint` policy (≈ one extra forward), and the adjoint test in L8 runs *through* the exchange, since the transpose rule is exactly the part hand-rolled adjoint models historically get wrong.

### 8.8 What is *not* attempted

No cross-framework compute unification (no GT4Py-Field-in-JAX-trace heroics — the `custom` route crosses an FFI boundary, it does not trace GT4Py); no source-transformation AD of gtfn-generated kernels (Enzyme-JAX over the generated LLVM/MLIR is noted as exploratory, nothing more); no whole-program dataflow compilation in the imperative tiers (§8.3 accepts and bounds that loss; the F-tier gets XLA fusion as a side effect); no nproma emulation; no attempt to make T0/T1 competitive with Fortran ICON — T2/T3 vs. icon4py-standalone remains the meaningful forward-performance benchmark, while F-tier performance is measured against NeuralGCM-class JAX models, not against the imperative tiers.

---

## 9. Validation ladder (what "scientific equivalence" means operationally)

1. **Stencil parity** — inherited from icon4py: granule outputs vs. serialized ICON reference data (Serialbox datasets), tolerance-based.
2. **Component parity** — single-column and single-process tests against ICON offline drivers/SCM: satad, graupel, turbdiff, TERRA on fixed forcing; radiation vs. ecRad reference (the CFFI-wrapped ecRad exists for exactly this).
3. **Suite behavior** — fast-physics `SequentialUpdateSplitting` vs. ICON column output over multi-day SCM integrations; slow-tendency cadence semantics (piecewise constancy, phase after restart) verified analytically.
4. **Idealized dynamics** — Jablonowski–Williamson baroclinic wave and Straka density current per tutorial ch. 4, compared against published/ICON-generated references (norms, growth rates, structure).
5. **Global real-data** — R2B4→R2B6 forecasts from DWD analysis; probtest-style ensemble-tolerance comparison against ICON (perturbed-IC ensembles define the equivalence band; symcon must fall inside it), plus standard skill scores vs. analysis.
6. **Invariants in CI** — restart reproducibility, run-to-run determinism per backend, tracer mass conservation, dry-mass conservation drift bounds, cross-tier agreement (T0 interpreted vs. T1 plan vs. T2/T3 lowered execution).
7. **Coupling-algebra self-convergence** — the federation classes themselves are validated by the thesis's grid-refinement methodology: self-convergence tests (a Burgers-type problem, then the level-4 idealized cases) verifying that each operator attains its formal order around symcon components — with the documented caveat, directly relevant to the ICON preset where saturation adjustment appears twice per step, that satad caps coupling-error convergence at first order unless a prognostic condensation formulation is substituted (thesis §2.5/App. 2.B).
8. **Gradient verification** — for every `native`/`custom` component and for composed windows: Taylor-remainder tests for `jvp` (correct first- and second-order decay), adjoint consistency ⟨Jv, w⟩ = ⟨v, Jᵀw⟩ to fp64 tolerances (the dot-product test, per component and through multi-step `scan` windows *including the halo-exchange transpose*), and finite-difference cross-checks on scalar functionals. Long-window gradient growth is characterized, not gated — sensitivity blow-up over chaotic horizons is physics, not a defect.

Explicitly not claimed: bitwise cross-platform reproducibility (that is the grid-generator problem's territory — libm/correct-rounding — and out of scope for a model targeting scientific equivalence).

---

## 10. Future-proofing and extension points

**Coupling-scheme research (new headline payoff).** Because the ICON preset is one point in the federation algebra, symcon supports exactly the class of experiments that motivated Tasmania and that production codes structurally cannot host: swapping SUS ↔ STS ↔ SSUS around an operational-grade dycore and physics suite, λ-sweeps, ordering studies, per-stage (FC) physics through the `DynamicalCore` fast-tendency port, and per-substep physics through its super-fast port — all under composition-time constraint validation and the cross-tier equivalence machinery, at kilometer-scale-capable performance rather than on idealized slice models. This closes the gap the thesis names explicitly: coupling research done on bespoke toys because flexible production code didn't exist.

**Data assimilation and hybrid-ML training.** The F-tier turns the composed model into what variational DA and differentiable-hybrid research need: `jax.vjp` of a forecast window for 4D-Var-style adjoint experiments; `ParamTree` gradients for scheme calibration against observations or reference simulations; and end-to-end training of an ML component (§8.4) *inside* the physical model — which upgrades the anemoi coupling below from offline adaptation to online differentiable coupling, the NeuralGCM pattern with an ICON dycore. The differentiability contract keeps this honest: any `none`-labeled component in the window is a composition-time decision (`error` or explicit `stop_gradient`), so a truncated gradient is always a documented choice.

**Nesting / LAM (the known v1 exclusions).** Three provisions keep them cheap later: (i) `refin_ctrl` and grid-hierarchy metadata are read and retained; (ii) the driver holds `state_per_domain: dict[DomainId, State]` internally even when its length is 1 — no flat-single-state assumption is baked in; (iii) parent↔child feedback and lateral-boundary nudging are shaped as paired `CouplingComponent`s (a communication-component subtype) plus a per-domain loop nesting in the driver — the tutorial's processing sequence (§3.9.2) maps onto nested `Subcycle`s. The LAM prefetch PE becomes another async role on the I/O communicator.

**anemoi / ML coupling.** ZarrMonitor's anemoi layout + a `PrognosticState↔anemoi.State` adapter component realize the previously scoped roadmap stages 1–3 inside this architecture; an ML emulator replacing a physics component is just a JAX/Torch component under §8.4 rules.

**Other physics suites.** The AES package's dyn2phy/phy2dyn transposition layer maps naturally onto explicit `DiagnosticComponent` pairs; nothing in the taxonomy is NWP-specific except `NWP_FAST_ORDER`.

**Ocean.** Out of scope, but the taxonomy is location-typed and grid-parameterized, and YAC-style coupling would enter as `CouplingComponent`s between two symcon models with distinct grids.

---

## 11. Risks and open questions

1. **Porting mass.** Tiedtke–Bechtold convection, TERRA (tiles), and turbdiff are large, gnarly Fortran bodies with decades of accumulated fixes. Mitigation: CFFI-wrapped Fortran as *bridge components* (CPU-only, segmenting T2/T3) so the model is whole early, with GT4Py ports replacing bridges scheme by scheme against ladder-level-2 tests. The architecture explicitly tolerates permanently-bridged components at the cost of T2/T3 segmentation.
2. **Radiation choice.** pyRTE-RRTMGP (GPU, maintained, Python-first) is not ecRad; scientific equivalence at suite level requires either an ecRad port (expensive) or accepting RRTMGP-vs-ecRad as a documented scheme substitution validated at ladder level 5. Decision needed early; the architecture is agnostic but the *equivalence claim* is not.
3. **Two-time-level privacy vs. introspection.** Hiding nnow/nnew inside the dycore is clean but makes some ICON diagnostics (which peek at both levels) awkward; escape hatch is the `restart_state()` surface, which doubles as an introspection API — acceptable, slightly ugly.
4. **Graph-capture and native-driver constraints.** T2 requires static shapes, stable buffer pointers, and no host-side data-dependent branching inside segments; the adaptive `ndyn_substeps` and slow-physics cadences are absorbed by the bounded step-signature cache, but any future component with in-segment host control flow forces a split. HIP graph support through CuPy is markedly less mature than CUDA's. T3's generated driver trades Python overhead for a build-and-debug surface (a compiler at bind time, symbol/ABI hygiene across gtfn shared objects, GHEX linkage). Both T1 and T3 lean on gt4py.next's still-evolving precompiled-program / static-args API — verify and pin before implementation. Build T2 incrementally (dycore segment first, widen outward); treat T3 strictly as profiling-driven escalation.
5. **Plan staleness and dual-semantics drift.** Bind-time specialization creates two representations of one model (T0 semantics vs. the frozen plan). The schema-hash/epoch guards catch out-of-band structural mutation, but *semantic* drift — a wrapper that turns out not to be pure control flow, a component mutating an input it declared read-only, an aliasing assumption violated by a swap — is the bug class to design tests around. CI's cross-tier agreement checks and the debug-mode periodic renegotiation-and-diff exist for exactly this; treat any T0/T1 divergence as a release blocker, never a tolerance to widen.
6. **GHEX Python bindings + GPU-aware MPI on target machines** (Alps-class) need early smoke-testing; the pinned-host fallback protects correctness, not scalability.
7. **Coupling swaps are structurally easy and scientifically treacherous.** ICON's physics carries implicit contracts that hold only under the operational arrangement: the surface-transfer-at-end time-level optimization, satad's placement (twice per step) and its convergence-capping behavior, turbulence's old-time-level input semantics, the isochoric heating convention on the bus. A federation swap that violates any of these is legal code and wrong science — and the thesis's own results (ordering sensitivity, scheme-dependent convergence of moist variables) show the differences are not academic. Mitigation: components declare `coupling_constraints` (must_follow/must_precede, required time-level semantics, admissible operator families) checked at composition; presets carry the validated/experimental label; experimental composites never inherit the scientific-equivalence claim; and the level-7 self-convergence tests exist to characterize, not merely permit, non-preset composites.
8. **Dual-implementation and adjoint drift.** `native` components carry two implementations of one scheme (gtfn kernel + JAX functional core); `custom` components carry a primal and a hand-written adjoint. Both pairs drift silently under maintenance unless held together mechanically: shared scheme-constants modules (one source of numerical truth), ladder-level-2 tolerances applied to functional cores against the same serialized references as the kernels, and level-8 adjoint tests in CI so an un-updated adjoint fails the dot-product test on the next run. Two further accepted realities: `jax.ffi` and mpi4jax are young surfaces, pinned under the `constraints/` discipline like gt4py's; and reverse-mode memory at production resolution is real even with per-step remat — long differentiation windows belong to coarse configurations and SCM columns, which is where the actual use cases (parameter estimation, hybrid training, 4D-Var research) live.

---

## 12. Summary of the extension delta over sympl

Everything sympl provides is kept. The complete list of additions: `location` + `halo` axes in property contracts; canonical-units registry + strict mode; `FieldBuffer` DLPack boundary + cached ingress adapters; `IconGrid`/`VerticalGrid`/static-state; the Tasmania coupling algebra (`ConcurrentCoupling`, registry-based `TendencyStepper`/`SequentialTendencyStepper`, `ParallelSplitting`/`SequentialTendencySplitting`/`SequentialUpdateSplitting`/`SSUS` federations, `DynamicalCore` with slow/fast/super-fast tiers, the `out=`/`array_call(inputs, outputs)` ABI, Checker/Operator-structured negotiation, `Factory` registries) with `coupling_constraints` validation added on top; `Subcycle`, `CallingFrequency` (generalized), `ReducedGridWrapper`, `SlowTendencyBus` convention + checker, `CommunicationComponent`; halo validator pass; `ComputeContext`; component-private restart protocol; the negotiation/execution phase split (`StateVault`, execution plans with even/odd swap variants and cadence masks) with its optional graph-replay and generated-native-host-driver lowerings; and the differentiability layer — the `differentiable` contract axis with `ParamTree` parameters, the F-tier functional lowering with explicit-carry PyTrees and `scan`/remat windows, and the transpose-rule `DifferentiableHaloExchange`. Each addition traces to a tension in §1 or to a Tasmania mechanism adopted in §4.2 — nothing else about sympl needed to change to host a production-structured NWP model, which is a nontrivial validation of the sympl thesis and of Ubbiali's extension of it: between them, the two lineages had already built most of the composition layer a production model needs; what symcon adds is the device-field boundary, the distributed-memory story, and the execution tiers that make the composition affordable at scale.
