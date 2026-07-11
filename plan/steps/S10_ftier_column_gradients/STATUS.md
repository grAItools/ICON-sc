# S10 — STATUS

## What was built

**Core (`symcon.core.functional`, new; jax touches core code here and nowhere
else — `symcon.core` itself still imports without jax):**

- `pytree.py` — generated frozen-dataclass PyTrees via
  `dataclasses.make_dataclass` + `jax.tree_util.register_dataclass`: `StateTree`
  from the state schema (one leaf per slot, `time` outside the trace) extended
  with explicit carry; `ParamTree` from the components' `params` declarations.
  Leaves sorted by canonical name at type generation (PLAN pitfall:
  deterministic carry ordering); canonical→attribute map kept on the class
  (`__symcon_leaves__`), `tree_of`/`mapping_of` accessors.
- `compile.py` — `functional_compile(composition, state, timestep=..., policy=...)
  -> FunctionalProgram` with pure
  `step_fn: (StateTree, ParamTree, StaticArgs) -> StateTree`, walking the same
  `visit(plan_builder)` protocol as the S05 plan compiler. Lowers: plain
  components (via their §8.6 `functional_call(inputs, params, dt=...)` cores),
  `ConcurrentCoupling` (serial policy, tendency accumulation),
  `SequentialUpdateSplitting` of bare Steppers (functional chaining),
  `CallingFrequency` (cache + last-fire phase as carry, recompute-vs-cached
  selected by `jnp.where` on a carried step counter — static trace across step
  signatures; live phase/cache restored through the wrapper's restart surface).
  `policy="error"` (default) raises `FunctionalCompileError` naming any
  `differentiable: none` component; `policy="stop_gradient"` compiles, warns,
  and stamps `stop_gradient:<name>` into `FunctionalProgram.provenance` (§8.6:
  never silent). `scan_window(step_fn, n, remat="per_step", ys_of=...)` =
  `lax.scan` + per-step `jax.checkpoint`.
- `rules.py` — `implicit_fixed_point` (`lax.custom_root` with the linear
  elementwise `tangent_solve`; both AD modes verified on the pinned jax) and
  `masked_newton_solve` (granule-style per-point-freeze Newton in a bounded
  `lax.while_loop`, primal-only).
- `testing/gradients.py` — the L8 harness: `taylor_test(f, x, v)` (remainder
  slope fit + slope-1 increments control), `dot_product_test(f, x, v, w)`,
  pytree-generic; deliberately outside `testing/__init__` so the testing
  package stays numpy-only.

**Icon (`symcon-icon`):**

- `graupel_constants.py` grew the **full** transcription of icon4py's
  `MicrophysicsConstants` graupel subset (values + derivation expressions
  op-for-op, incl. `CCS*`, `NIMIX`, `PVSW0`, `CPI`); `satad_constants.py` new
  (Tetens water + `TETENS_DER` + Kirchhoff `CP_V = 1850.0` + `ZQWMIN`). Bitwise
  equality against a live icon4py import gated in `test_scheme_constants.py`
  (§11.8: one source of numerical truth per scheme, held mechanically).
- `microphysics.py` — `_graupel_functional`: line-by-line `lax.scan` port of
  the granule's 26-slot sedimentation scan + the at-ground flux program
  (REFERENCES.lock `icon4py-graupel-stencils`), with the double-where guard
  discipline on every branch-guarded `log`/division (NaN-free primal *and*
  gradients). Coefficients the granule precomputes with `math.gamma` are
  re-derived **in-trace** via `gammaln` from the ParamTree so parameter
  gradients are real. `Graupel.functional_call` + `functional_params`
  (`kcau`/`kcac` scheme constants + the `GraupelConfig` tuning knobs:
  `ice_stickeff_min`, `snow2graupel_riming_coeff`, ice/snow fall-speed
  coefficients, `icesedi_exp`, `rain_mu`, `rain_n0`); `params: ("kcau",
  "kcac")` declared on the rain output contract.
- `satad.py` — `_satad_functional`: subsaturated shortcut + the saturation
  fixed point solved by the granule's own masked Newton and differentiated
  through `implicit_fixed_point` (IFT/`custom_root`; adjoint of the solve, not
  the iterations). `SaturationAdjustment.functional_call` (no tunable params —
  `max_iter`/`tolerance` are solver controls, not physics).
- `idealized.py` — native functional cores for `PrescribedCooling` (reuses the
  array-namespace-generic `reference_temperature` — one shared formula for
  both tiers) and `ApplySlowTendencies`; both now declare
  `differentiable: "native"` (additive contract key).
- `examples/07_gradient_scm.py` — vjp of accumulated surface precipitation
  over a 10-step window w.r.t. `kcau`, FD cross-check (measured rel. err.
  2.7e-10).
- `validation/L8_gradients/` seeded: README + `run_l8.py` (prints the
  Taylor/dot-product table, writes remainder-decay plots to the gitignored
  `artifacts/`).

**Dependencies:** dev group gains CPU `jax` (resolved 0.6.2, recorded in
`constraints/cpu-ci.txt`; the `[jax]` extra's `jax>=0.6.0` lower bound from S01
is unchanged — no pin bumps). `mpi4jax` (the rest of the extra) deliberately
not installed: it would drag an MPI build toolchain into the CPU gate and
belongs to the distributed F-tier step (§8.7).

## Acceptance criteria — results

1. **Functional-core parity (L2 restated)** — `test_graupel_functional_datatest.py`
   (marker `data`): JAX core vs the **gtfn_cpu** kernel on the WK-torus
   savepoints (3 dates), fp64, `rtol=1e-10` — **passed locally** (see tolerance
   note below for the QMIN atol floor). Always-on guard without data:
   `test_graupel_functional.py` parity battery vs the embedded granule on
   synthetic hydrometeor columns (observed max abs ≈ 1e-18).
2. **Taylor tests** — slope 2.0±0.1 over 6 halvings: satad 2.0007, graupel
   1.9999, 10-step `scan_window` 1.996 (gated in the three `test_*_functional`
   suites; plots via `validation/L8_gradients/run_l8.py`).
3. **Dot-product tests** — ≤ 1e-10 fp64: satad-through-IFT ≈ 8e-16, graupel
   ≈ 6e-16, 10-step window (satad IFT crossed 20×) ≈ 1.4e-15.
4. **FD cross-check** — example-07 scalar functional (accumulated precip vs
   `kcau`): vjp 1.0562825825e-2 vs central FD 1.0562825822e-2 at h=1e-4,
   rel. err. 2.7e-10 ≤ 1e-6 (`test_scm_functional.py::test_example_fd_cross_check`,
   `slow`-marked).
5. **stop_gradient policy** — a `none`-marked satad raises
   `FunctionalCompileError` naming `satad` under `policy="error"`; under
   `policy="stop_gradient"` it compiles, warns (`UserWarning`), stamps
   `stop_gradient:satad` into provenance, and the truncated gradients are
   exactly zero. (Also covered at toy scale in core.)
6. **donate_argnums** — `jax.jit(step_fn, donate_argnums=0)` runs (SCM and toy
   compositions); functionality only, memory not asserted, per SPEC.
7. **T0 ↔ F-tier forward equivalence** — 12 steps of the SCM preset (one full
   slow cadence + refire) and a mid-run compile from a pre-fired
   `CallingFrequency` phase: `rtol=1e-10` (observed ≈ 4e-15 on all fields at
   meaningful magnitudes; see tolerance note).

## Tolerance note (flag for human sign-off)

Acceptances 1 and 7 state bare `rtol ≤ 1e-10`. The comparisons pass that
relative contract everywhere the compared values are physically meaningful, but
mixing-ratio-valued fields contain points at ~1e-18…1e-22 kg/kg (residuals of
the `max(tend, -q/dt)` clip), where a last-ulp difference between XLA and
gtfn/numpy arithmetic is *relatively* unbounded. The tests therefore assert
`rtol=1e-10` **plus an absolute floor `atol = GRAUPEL_QMIN = 1e-15`** on
mixing-ratio-valued fields (temperature keeps `atol=0`). Justification: QMIN is
the scheme's own "threshold for lowest detectable mixing ratios" — every branch
of the granule treats values below it as zero — and icon4py's own L2 tests use
a *looser* `atol=1e-12` on the same fields (S08 provenance). This is an
absolute-floor qualification of the stated relative contract, not a relaxation
of it; flagged here per AGENTS.md for sign-off in the PR.

## Deviations

- **Cadence mask mechanism:** PLAN item 2 suggested per-window mask arrays
  passed as scan `xs`; implemented instead as a carried step counter + carried
  last-fire phase with `jnp.where` (the PLAN's stated pitfall — "masks must be
  step-indexed xs, not Python ints, or scan retraces" — is equally avoided:
  the counter is traced, the trace is static). This also makes `step_fn`
  self-contained (usable outside `scan_window`) and lets a live wrapper's
  phase/cache ride in via its restart surface. Equivalence gated in tests.
- **satad convergence bound:** the T0 granule raises `ConvergenceError` past
  `max_iter`; a data-dependent raise is not expressible under `jit`, so the
  F-tier Newton is bounded at `max_iter` sweeps and proceeds with the last
  iterate (`masked_newton_solve` docstring). All gated regimes converge well
  inside the bound.
- **`is_surface` quirk replicated:** the granule compares the scan-relative
  `k_lev` against the absolute `ground_level = nlev-1`, so the surface
  minimum-fall-speed clamps only ever fire when `kstart_moist == 0` (true for
  the WK data; not for the S06 column grid, where `kstart_moist = 2`).
  Replicated verbatim for parity; upstream icon4py quirk, not fixed locally.
- **`_initialize_configurable_parameters` re-derivation:** the granule's
  `math.gamma` coefficient expressions are evaluated in-trace as
  `exp(gammaln(·))` so ParamTree gradients flow through them; at default
  parameters this agrees with the granule's values to ~1e-15 relative
  (absorbed by the acceptance-1 margin — observed end-to-end parity ~1e-13
  worst-case relative at meaningful magnitudes).
- **`none`-component axis inference:** a component's differentiability axis is
  the strongest `differentiable` declared across its output specs (undeclared
  entries — e.g. the gsp-rate diagnostics — default to `none` without demoting
  a component that declares `native` elsewhere).
- **Sequence-of-nodes compile entry:** `SCMComposition.step` is a plain Python
  method (S09), so `functional_compile` accepts an ordered sequence of
  composition nodes (`(slow, core, fast)`) — the §5.1 loop-body order — rather
  than inventing a wrapper type around the frozen S09 dataclass.

## Follow-ups

- `jax.ffi` registration of gtfn kernels as XLA custom calls (the *other* half
  of the §8.6 `custom` route — S10 satisfies `custom` via a pure-JAX primal +
  IFT rule; an FFI primal becomes interesting when a scheme has no cheap JAX
  forward).
- `DifferentiableHaloExchange` + mpi4jax (§8.7) — distributed F-tier step;
  add `mpi4jax` to the environment there.
- The functional compiler covers the S10 slice (components, CC, SUS,
  CallingFrequency); Subcycle/schemes/dycore lowering arrives with the dycore
  F-tier work.
- `test_scm_functional.py` reaches into `SaturationAdjustment._i4_vertical`
  (the S07 friend-access pattern); the public `kstart_moist` exposure proposed
  in S07 STATUS would clean up `functional_call` implementations too.
- Long-window gradient growth characterization (L8 "characterized, not gated")
  deferred to the P6 ladder wiring; `run_l8.py` is the seed.

## Artifacts

- `validation/L8_gradients/artifacts/taylor_scm_step.png`,
  `taylor_scm_window_10.png` (gitignored; regenerate with
  `uv run python validation/L8_gradients/run_l8.py`).

## Gate

- `uv run pytest packages -m "not gpu and not slow" -q` — see PR checklist
  (filled at gate time below).
- `uv run pytest packages -m "slow and not gpu" -q` — idem.
- `uv run ruff check .` / `uv run ruff format --check .` — clean.
- `uv run mypy --strict -p symcon.core` — clean (50 files).
- `uv run lint-imports` — 2 contracts kept.
- data-marked: `test_graupel_functional_datatest.py` 3/3 passed locally
  (cached WK archive); gpu-marked tests skip without a device.
