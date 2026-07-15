# repo-layout — the repository layout, packaging boundaries, and layout conventions

Scope: the monorepo tree, the three-distribution packaging and import-boundary
structure, and the layout conventions that carry architectural weight. Section
references (§) point into `docs/architecture/symcon_architecture.md` (v1.3).
Formerly `docs/architecture/symcon_repo_layout.md` (moved and made a living policy in
work unit 035, TD-35.2).

## 0. Top-level decisions

**One monorepo, three distributions.** Framework and components co-evolve too tightly in the early phase for separate repos, but the architecture's central structural claim — the composition layer is model-agnostic; ICON is a client of it — must be enforced by packaging, not convention. Hence a single repo shipping three PEP 420 namespace distributions:

| distribution | import root | contents | may import |
|---|---|---|---|
| `symcon-core` | `symcon.core` | state/vault/plan, contracts, coupling algebra, comm, context, driver, generic I/O | gt4py, ghex, xarray, cupy/jax (optional) — **never** `symcon.icon` |
| `symcon-icon` | `symcon.icon` | ICON grid stack, all ICON components, presets, ingestion, variable registry | `symcon.core`, icon4py, eccodes, pyRTE-RRTMGP |
| `symcon-bridges` | `symcon.bridges` | CFFI-wrapped Fortran bridge components (ecRad reference, Tiedtke–Bechtold, TERRA during porting) | `symcon.core`; needs Fortran toolchain — isolated so nothing else does |

The `core ↛ icon` boundary is enforced in CI by [import-linter](https://import-linter.readthedocs.io) contracts, making "Tasmania-lineage layer stays generic" a build failure rather than a review comment. `symcon-bridges` exists so that the default install is pure-Python-plus-wheels; anyone not validating against Fortran reference schemes never touches a compiler.

**External, not vendored:** `gt4py`, `icon4py` (granules), `ghex`, `pyRTE-RRTMGP` are dependencies. Their fast-moving APIs (§8.3 sketch-status note) are managed through a `constraints/` directory of pinned lockfiles per target environment, icon4py-style — the repo pins, the packages only lower-bound.

**Workspace tooling:** `uv` workspace at the root (one lock, three members); `pixi.toml`/Spack environment specs under `envs/` for HPC targets where MPI/CUDA/eccodes come from the system.

```
symcon/                                  # monorepo root
├── pyproject.toml                       # uv workspace root (members = packages/*)
├── uv.lock
├── README.md
├── LICENSE                              # BSD-3-Clause (matches ICON, icon4py, gt4py)
├── .pre-commit-config.yaml              # ruff, ruff-format, mypy hook, REUSE headers
├── .importlinter                        # layer contracts: core ↛ icon, icon ↛ bridges (registry only)
├── constraints/                         # pinned dep sets per environment (gt4py, icon4py, jax/mpi4jax)
│   ├── cpu-ci.txt
│   ├── gpu-cuda12.txt
│   ├── alps-gh200.txt                   # GPU-aware MPI + GHEX + cupy pins for Alps-class
│   └── jax-interop.txt
├── envs/
│   ├── pixi.toml                        # local/laptop dev
│   └── spack/                           # HPC site environments (MPI, eccodes, ghex deps)
├── packages/
│   ├── symcon-core/
│   ├── symcon-icon/
│   └── symcon-bridges/
├── examples/                            # legible run scripts — the §5.1 UX, kept executable
├── validation/                          # the §9 ladder as a runnable tree (integration tier)
├── benchmarks/
├── tools/
├── docs/
└── .github/workflows/
```

---

## 1. `packages/symcon-core/` — the framework (§2, §4.1–4.2, §5, §6, §8)

```
packages/symcon-core/
├── pyproject.toml                       # extras: [gpu] cupy, [jax] jax+mpi4jax, [mpi] mpi4py+ghex, [native] cffi+cmake
├── src/symcon/core/
│   ├── __init__.py                      # curated public API re-exports; py.typed
│   │
│   ├── typing.py                        # FieldBuffer protocol (§2.2), Location/HaloState enums, dtypes
│   ├── registry.py                      # Factory / MetaFactory name-keyed registries (§4.2, Ubbiali)
│   ├── time.py                          # datetime/cftime handling, cadence arithmetic (lcm, phases)
│   ├── profiling.py                     # Timer with labelled nested sections, device sync (Ubbiali)
│   │
│   ├── state/
│   │   ├── names.py                     # canonical-name registry machinery + `_on_interface_levels` (§2.5)
│   │   ├── units.py                     # canonical-units registry; no-op-conversion verifier (§2.4)
│   │   ├── dataarray.py                 # boundary DataArray construction, attrs schema (§2.2)
│   │   ├── vault.py                     # StateVault, FieldHandle, schema_hash, epoch (§8.2)
│   │   └── facade.py                    # lazy dict-of-DataArrays view over the vault (§8.2)
│   │
│   ├── contracts/
│   │   ├── properties.py                # property-dict schema: dims/units/location/halo/alias
│   │   │                                #   + differentiable axis and params declaration (§2.4, §8.6)
│   │   ├── checkers.py                  # static + dynamic Checkers (§4.2 ← Ubbiali fork)
│   │   └── operators.py                 # dynamic Operators: ingress/egress plans, conversions (§4.2)
│   │
│   ├── components/
│   │   ├── base.py                      # DiagnosticComponent, TendencyComponent, Implicit…,
│   │   │                                #   Stepper, Monitor — out=/array_call(inputs, outputs) ABI,
│   │   │                                #   allocate_* hooks, restart_state()/load_restart_state() (§4.1, §4.5)
│   │   ├── wrappers.py                  # CallingFrequency, Subcycle, ScalingWrapper (§4.2)
│   │   ├── reduced_grid.py              # ReducedGridWrapper: grid-pair + up/down contract (§4.2; interp impl is model-side)
│   │   └── dycore.py                    # DynamicalCore base: slow port, per-stage fast slot,
│   │                                    #   super-fast substep tier, stage/substep hooks (§4.2 ← Tasmania)
│   │
│   ├── coupling/
│   │   ├── concurrent.py                # ConcurrentCoupling (tendency sum, diagnostics union)
│   │   ├── steppers.py                  # TendencyStepper registry ("forward_euler","rk2","rk3ws",…)
│   │   │                                #   + SequentialTendencyStepper (two-state signature)
│   │   ├── federations.py               # ParallelSplitting, SequentialTendencySplitting,
│   │   │                                #   SequentialUpdateSplitting, SSUS(lam, pre_steppers)
│   │   ├── bus.py                       # tendency-slot declaration + single-consumer checker (§4.2)
│   │   └── constraints.py               # must_follow/must_precede, coupling_constraints validation (§11.7)
│   │
│   ├── ingress/
│   │   ├── base.py                      # adapter registry keyed by framework; bind-time resolution (§2.3)
│   │   ├── gt4py.py                     # as_field views; precompiled-program pinning shim (§8.3 note)
│   │   ├── cupy.py                      # trivial (native FieldBuffer)
│   │   ├── jax.py                       # dlpack in, write-back out, stream sync (§8.4)
│   │   └── numba.py
│   │
│   ├── plan/
│   │   ├── ops.py                       # op algebra: BoundCall, Swap, Axpy(k-ary), DiffScale,
│   │   │                                #   Exchange, SegmentMarker, CadenceMask (§8.2)
│   │   ├── bind.py                      # negotiation → ExecutionPlan compiler; federation/wrapper
│   │   │                                #   dissolution; even/odd variant emission (§8.2)
│   │   ├── interpreter.py               # T1 (§8.3)
│   │   ├── graphs.py                    # T2: capture per exchange-free segment, signature cache (§8.3)
│   │   ├── native/
│   │   │   ├── emit.py                  # T3 C++ TU emission from the plan (§8.3)
│   │   │   ├── templates/               # driver skeleton, gtfn/ghex call shims
│   │   │   └── build.py                 # cached compile keyed by plan hash; ABI checks
│   │   └── guards.py                    # schema hash, epoch, debug renegotiate-and-diff (§8.2, §11.5)
│   │
│   ├── functional/                      # the F-tier: fourth lowering of the same negotiation (§8.5–8.6)
│   │   ├── pytree.py                    # StateTree/ParamTree schemas generated from the vault schema;
│   │   │                                #   explicit-carry surfacing of component functional_state() (T7)
│   │   ├── compile.py                   # negotiated composition → pure step_fn; scan windows,
│   │   │                                #   remat policies, cadence masks as carry + jnp.where
│   │   ├── rules.py                     # custom_jvp/custom_vjp registration helpers; custom_root/IFT
│   │   │                                #   patterns for implicit solves (tridiagonal transpose, satad)
│   │   └── ffi.py                       # gtfn kernels as XLA FFI targets for the "custom" route
│   │
│   ├── comm/
│   │   ├── decomposition.py             # DecompositionInfo, partitioner registry (metis + pluggable) (§6.1)
│   │   ├── ghex.py                      # per-location pattern cache, bulk-exchange handles,
│   │   │                                #   HaloExchange component, GPU-aware-MPI probe + fallback (§6.2)
│   │   ├── jax_halo.py                  # DifferentiableHaloExchange: custom_vjp = transpose
│   │   │                                #   (scatter-add onto owners, zero ghosts), custom_jvp = same
│   │   │                                #   exchange; mpi4jax first, ghex-via-jax.ffi later (§8.7)
│   │   └── validator.py                 # halo validity walk; auto-insert / manual-verify modes (§6.3)
│   │
│   ├── context.py                       # ComputeContext: backend, allocator pools, comms split,
│   │                                    #   strict flag, tier selection, timeloop() entry (§5.2)
│   ├── driver/
│   │   ├── timeloop.py                  # loop object; state_per_domain internally (§10 nesting provision)
│   │   └── model.py                     # Federation-style convenience assembly (§5.1, educational)
│   │
│   ├── config.py                        # frozen dataclass config base, provenance stamping (§5.3)
│   └── io/
│       ├── monitor.py                   # async gather/forward machinery, io-rank protocol, backpressure (§6.4)
│       ├── zarr.py                      # region-writes w/ global chunk map; anemoi layout flag (§7.4)
│       ├── netcdf.py
│       ├── restart.py                   # public state + component restart_state + config + RNG (§4.5)
│       └── plot.py
│
└── tests/                               # fast unit tier (no MPI, no GPU required; markers for both)
    ├── state/  contracts/  coupling/  plan/  functional/  comm/  io/
    ├── test_coupling_orders.py          # federation formal-order checks on scalar ODEs (thesis §2.4 analytically)
    ├── test_plan_equivalence.py         # T0 vs T1 on toy components — the §11.5 release blocker in miniature
    └── test_halo_transpose.py           # ⟨Jv,w⟩ = ⟨v,Jᵀw⟩ through the exchange on toy decompositions (§8.7)
```

Notes: `plan/ops.py` is deliberately the smallest vocabulary that §8.2 needs — resisting op-algebra growth is a design goal, since every new op type is something T2 capture and T3 emission must both support. `ingress/gt4py.py` is the single quarantine point for the evolving precompiled-program API (§8.3): when gt4py.next changes its static-args mechanism, one file moves.

---

## 2. `packages/symcon-icon/` — the ICON model (§3, §4.3, §7)

```
packages/symcon-icon/
├── pyproject.toml                       # deps: symcon-core, icon4py-* granule packages, eccodes,
│                                        #   pyRTE-RRTMGP; extras: [ingest-grib], [anemoi]
├── src/symcon/icon/
│   ├── __init__.py
│   │
│   ├── names.py                         # THE variable registry table: canonical ↔ ICON short name
│   │                                    #   ↔ CF standard name ↔ GRIB2 triplet (§2.5, §7.2);
│   │                                    #   icon: namespace lives here
│   │
│   ├── grid/
│   │   ├── reader.py                    # ICON grid NetCDF ingestion, uuidOfHGrid keying (§3.1)
│   │   ├── grid.py                      # IconGrid: sizes, connectivities (raw + offset-provider views),
│   │   │                                #   geometry, refin_ctrl retained (§3.1, §10)
│   │   ├── vertical.py                  # VerticalGrid: vct_a/b, SLEVE/Gal-Chen (§3.2)
│   │   ├── metrics.py                   # MetricsFactory → static_state fields (wraps icon4py) (§3.2)
│   │   ├── interpolation.py             # InterpolationFactory: RBF, c2e/e2c, nudging coeffs (§3.2)
│   │   ├── decomposition.py             # ICON geometric partitioner plugin for core partitioner registry
│   │   └── reduced.py                   # radiation reduced-grid pair + up/downscale stencils (§4.2)
│   │
│   ├── components/
│   │   ├── dycore.py                    # NonhydroSolver(DynamicalCore): stages = predictor/corrector,
│   │   │                                #   substep tier = ndyn_substeps + cfl_adaptive, slow-port
│   │   │                                #   consumption, communicates_internally, private time levels (§4.3)
│   │   ├── diffusion.py                 # HorizontalDiffusion (icon4py diffusion)
│   │   ├── transport.py                 # TracerTransport: FFSL + PPM, per-tracer config, ρqx bus slots
│   │   ├── diagnostics.py               # HydrostaticPressureDiagnostics, WindReconstruction (§3.3)
│   │   ├── iau.py                       # IncrementalAnalysisUpdate (windowed) (§4.3)
│   │   ├── adjoints/                    # hand-written tangent/adjoint GT4Py programs for the
│   │   │                                #   "custom" route, paired 1:1 with primal granules (§8.6)
│   │   ├── fast/
│   │   │   ├── satad.py  turbulence.py  microphysics.py
│   │   │   ├── terra.py  flake.py  seaice.py  surface_transfer.py
│   │   │   └── order.py                 # NWP_FAST_ORDER + its coupling_constraints declarations (§4.2, §11.7)
│   │   └── slow/
│   │       ├── convection.py  cloud_cover.py  gwd.py  sso.py
│   │       └── radiation.py             # pyRTE-RRTMGP primary; ecRad bridge selected via registry (§11.2)
│   │
│   ├── presets/
│   │   ├── nwp.py                       # ICON_NWP preset builder: the §5.1 composition as a function;
│   │   │                                #   validated-label registry; experiment presets marked experimental
│   │   └── config.py                    # NWPConfig + per-component config dataclasses,
│   │                                    #   icon_namelist_origin annotations (§5.3)
│   │
│   ├── ingest/
│   │   ├── extpar.py                    # ExtPar NetCDF → static_state (§7.1)
│   │   ├── grib2.py                     # eccodes reader driven by names.py GRIB2 columns (§7.2)
│   │   ├── initial.py                   # from_dwd_analysis / from_ifs_analysis; prognostic-set
│   │   │                                #   construction (vn projection, exner/θv, IAU increments) (§7.3)
│   │   └── idealized.py                 # Jablonowski–Williamson, Straka initializers (§7.3, ladder L4)
│   │
│   └── anemoi.py                        # PrognosticState ↔ anemoi State adapters (§10)
│
└── tests/
    ├── grid/  ingest/  components/
    ├── data/manifest.toml               # pooch/DVC manifests — serialized reference data never in git
    └── test_preset_composition.py       # ICON_NWP composes, halo-validates, bus single-consumer holds
```

Notes: `presets/nwp.py` is the module the run scripts in `examples/` are *checked against* — the preset builder and the hand-written §5.1 script must produce identical plans (a test asserts plan-hash equality), keeping the "legible run script" and the "validated preset" from drifting apart. `fast/order.py` is where the tutorial §3.7.2 semantics (surface-transfer-at-end, satad twice, old-time-level turbulence inputs) live as machine-checkable `coupling_constraints`, not folklore.

---

## 3. `packages/symcon-bridges/` — Fortran bridge components (§11.1)

```
packages/symcon-bridges/
├── pyproject.toml                       # build-system: scikit-build-core + CMake + Fortran; CFFI
├── CMakeLists.txt
├── src/symcon/bridges/
│   ├── _ffi/                            # cdef headers, thin C shims around Fortran modules
│   ├── ecrad.py                         # EcradRadiation(TendencyComponent) — validation reference (§11.2)
│   ├── tiedtke.py                       # bridge until the GT4Py port passes ladder L2
│   └── terra.py                         # idem
├── third_party/                         # git submodules or FetchContent pins of Fortran sources
└── tests/                               # column-level parity vs. vendor reference outputs
```

Bridges declare `framework="cffi"` in their contracts, which automatically makes them T2/T3 segment boundaries (§8.3–8.4) and CPU-resident (ingress adapter stages device↔host explicitly). The package is optional by design: the model composes without it, at the cost of scheme substitutions flagged at composition time.

---

## 4. Repo-level trees

```
examples/                                # every file runs; CI smoke-tests them at toy resolution
├── 01_scm_column.py                     # single-column fast suite — first thing that works end-to-end
├── 02_jw_baroclinic.py                  # dry dycore + diffusion, idealized (L4)
├── 03_global_nwp_r2b4.py                # the §5.1 script, verbatim
├── 04_coupling_ssus.py                  # the §5.1 SSUS experiment snippet, runnable
├── 05_interactive_radiation.ipynb       # sympl's educational affordance, preserved
├── 06_ml_convection_stub.py             # JAX component at a framework seam (§8.4)
├── 07_gradient_scm.py                   # jax.vjp through an SCM window; ParamTree gradients (F-tier)
└── 08_online_hybrid_training.py         # ML convection trained inside the physical column (§10)

validation/                              # the §9 ladder, one directory per level
├── conftest.py                          # markers: gpu, mpi(n), slow, data; tier fixture (T0/T1/T2/T3)
├── L2_components/                       # column parity vs. serialized ICON / SCM references
├── L3_suite/                            # multi-day SCM vs. ICON column output; cadence semantics
├── L4_idealized/                        # JW, Straka vs. references; norms and growth rates
├── L5_realdata/                         # R2B4→R2B6 probtest-style ensemble-band comparison
├── L6_invariants/                       # restart repro, determinism, mass conservation, cross-tier
├── L7_coupling/                         # federation self-convergence (Burgers + idealized); satad caveat
├── L8_gradients/                        # Taylor/jvp decay, dot-product adjoint tests (incl. exchange
│                                        #   transpose), FD cross-checks; fp64; long-window growth reports
└── data/                                # pooch registries + fetch tooling only (L1 lives in icon4py CI)

benchmarks/
├── dispatch_overhead/                   # T0/T1/T2/T3 per-step cost vs. component count; launch counts
├── halo/                                # GHEX bulk vs. per-field; GPU-aware vs. staged
├── step_r2b4_gpu.py                     # headline: vs. icon4py-standalone (§8.8 target)
└── asv.conf.json                        # airspeed-velocity for regression tracking

tools/
├── plan_inspect.py                      # dump op list, segments, halo schedule, signatures for a preset
├── grid_partition.py                    # offline partitioning + decomposition file writer
├── names_audit.py                       # registry ↔ CF table ↔ GRIB2 consistency checks
└── constraints_update.py                # regenerate constraints/ lockfiles against fresh gt4py/icon4py

development/                             # repo-internal process memory — never a Sphinx source (TD-33.1)
├── README.md                            # map of the tree
├── REGISTRY.md                          # living registry: work ids (4-digit), remap tables, trunk decisions
├── policies/                            # living rules: workflow, naming, kinds, gates, mining, review, docs boundary, repo layout
├── ADRs/                                # architecture decision records (NNNN-<kebab-title>.md, own sequence from 0000)
├── work/
│   ├── proposals/                       # future proposals; phase outlines P2–P7 (proposal-NNNN-<kebab>.md)
│   ├── specs/                           # frozen work-unit contracts (spec-NNNN-<kebab>.md)
│   ├── plans/                           # frozen work-unit plans (plan-NNNN-<kebab>.md)
│   └── reports/                         # outcome documents frozen at merge (report-NNNN-<kebab>.md + sibling artifacts folders)
├── archive/                             # dead documents of any kind
└── references/                          # per-source reference cards + lock.toml (machine ledger) + local/ (gitignored)

docs/
├── architecture/symcon_architecture.md  # the v1.2 document, canonical
├── coupling.md                          # operator semantics, preset catalogue, validated/experimental
├── porting_guide.md                     # bridge → GT4Py port workflow against ladder L2
└── api/                                 # sphinx + autodoc from py.typed sources

.github/workflows/
├── lint.yml                             # ruff, mypy --strict on core, import-linter contracts
├── test-cpu.yml                         # unit tests + examples smoke + L2/L7-cheap, matrix over constraints/
├── test-mpi.yml                         # comm/, validator, restart repro at np=4 (pytest-mpi)
├── test-gpu.yml                         # self-hosted: T1/T2 equivalence, ingress zero-copy asserts, bench smoke
└── nightly.yml                          # L4/L6 full, cross-tier agreement, plan-hash stability report
```

---

## 5. Conventions that carry architectural weight

- **`py.typed` everywhere; `mypy --strict` on `symcon-core`.** The property contracts are runtime-checked, but the plan/ops layer is exactly the kind of code where static typing pays.
- **Import-linter contracts** (`.importlinter`): `core` independent; `icon` may not import `bridges` directly (bridge components arrive via the component registry, so radiation-scheme selection is a config string, not an import).
- **No data in git.** Serialized reference data, grids, ExtPar, analysis files come through `pooch` manifests with checksums; `validation/data/` holds registries only.
- **Plan artifacts are cache, not source.** T3-generated TUs and compiled objects live under `$XDG_CACHE_HOME/symcon/plans/<plan-hash>/`; the repo ships only `plan/native/templates/`.
- **One scheme-constants module per scheme.** `native` components ship a gtfn kernel and a JAX functional core; both import their numerical constants from a single `_constants.py` per scheme, and CI applies the same L2 reference tolerances to both paths — the §11.8 drift risk is contained structurally, not by review.
- **Version pinning discipline** (§8.3): packages declare lower bounds; `constraints/` pins exact working sets per environment; `tools/constraints_update.py` + a scheduled CI job surface upstream breakage as a PR, not a user bug report.
- **Suggested build order** (mirrors the ladder): `core.state` + `contracts` + `components.base` → SCM column with two toy processes (T0) → `coupling` federations + L7 on Burgers → `plan` T1 → ICON grid stack + satad/microphysics (L2) → functional cores for those same two schemes + `functional/` + L8 on the column (gradients proven before the dycore exists) → dycore hosting + L4 → `comm` + validator (L6 restart/repro) → slow suite + preset (L3, L5) → T2 → T3 only if profiles demand.
