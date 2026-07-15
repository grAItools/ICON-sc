# symcon vertical slice — implementation report (S01–S14)

**Period:** 2026-07-08 → 2026-07-13 · **Branch state:** all 14 step branches merged into
local `main` (nothing pushed; one-PR-per-step remains available in DAG order).
**Final smoke on `main`:** 736 passed, 1 skipped (mpi opt-in) in 12:47
(`pytest packages -m "not gpu and not slow"`).

This report is the process memory of the implementation: how each step landed, what the
reviews caught, the scientific/engineering findings worth keeping, and the ledger of
items that still need human sign-off at PR time. Detailed per-step accounts live in
`development/records/SXX_*/STATUS.md`; provenance of every consulted source is in
`development/references/lock.toml`.

---

## 1. Process

Every step ran the same loop, per the AGENTS.md working agreement:

1. **Implementer agent** — branch `step/SXX-*` from merged main; mine references first
   (append to `development/references/lock.toml` at mining time, SHAs pinned); implement against the
   SPEC's frozen interfaces exactly; acceptance tests as the definition of done; full
   gate (pytest partitions, ruff, `mypy --strict` on symcon-core, import-linter);
   STATUS.md with deviations declared.
2. **Independent skeptical reviewer agent** — re-runs the gates itself (never trusts
   reports), maps every acceptance criterion to its covering test, probes whether tests
   can actually fail (mutation/perturbation probes), re-derives tolerances from the
   pinned upstream sources, spot-checks constants against ICON Fortran/icon4py at the
   pinned SHAs, hunts for undeclared deviations. Verdict: approve / request-changes
   with findings by severity.
3. **Fix rounds** iterate implementer ↔ reviewer until approve; then merge (`--no-ff`)
   into local main.

Pinned reference pair throughout: **icon4py v0.2.0** (`28d32c45afb4…`) + **gt4py 1.1.10**
(the released, PyPI-published pair; icon4py HEAD pinned 1.1.11 at mining time — we pin
releases, not HEAD). ICON Fortran ground truth: **icon-2026.04-public** (`8597da45…`)
via the gitlab.dkrz.de mirror (gitlab.dwd.de does not resolve from this host).

## 2. Merge ledger

| Step | Merge | What landed | Review rounds |
|---|---|---|---|
| S01 scaffold | `daf9e17` | uv workspace, 3 PEP-420 packages, CI, pins, testing module | 1 fix round (mpi-marker exit-5 trap, ordering-fragile test) |
| S02 state + contracts | `bbabe07` | typing/registry/state/contracts/config/time/profiling | 1 (branch surgery — work sat on main; hypothesis flake) |
| S03 component ABI + T0 | `4a5c047` | five component kinds, wrappers, ComputeContext, toys | 1 (restart crash on empty output dicts; out= shape check; device egress) |
| S04 coupling algebra | `c233c62` | ConcurrentCoupling, stepper registries, 4 federations, bus, constraints, DynamicalCore | 1 (constraints defeated by wrapper renaming; untested exported helpers) |
| S05 vault + plan + T1 | `46090ff` | StateVault, plan compiler, T1 interpreter, guards, plan-hash | 1 (CF-under-multi-stage misleading error; plan-hash param blind spot declared) |
| S06 vertical grid + thermo | `e87307d` | ICON constants (byte-verified), thermo, VerticalGrid, registry seed | 1 (env-mutation confinement; docstring provenance) |
| S07 satad | `c1bba21` | SaturationAdjustment hosting the icon4py granule; gt4py Backend ingress | 1 (missing gtfn_gpu datatest leg + false docstring claim) |
| S08 graupel | `4773428` | Microphysics/Graupel hosting the granule; persistent gt4py build cache | 1 (cold-conservation bound violated in-domain → re-derived 1e-3 from measured 4.32e-4) |
| S09 SCM composition | `2205ad8` | SCM preset (satad→mphys→satad), slow-tendency bus, example 01 | 1 (bare assert → raise; sign-off items flagged) |
| S10 F-tier gradients | `3e2baa3` | symcon.core.functional, JAX satad/graupel cores, L8 harness, example 07 | 1 (FD-step selection circularity; carry-mechanism deviation declared) |
| S11 grid + metrics | `5809a6f` | grid reader, IconGrid, geometry, metrics/interpolation factories | 1 (6 misattributed tolerances tightened back to upstream-strict) |
| S12 nonhydro hosting | `4e6b0fb` | NonhydroSolver(DynamicalCore) hosting solve_nonhydro | 2 (IAU guard, production-path coverage → pentagon dossier; fast-tier provisional state; Δτ guard; T1 smoke) |
| S13 diffusion + JW L4 | `512ca83` | HorizontalDiffusion, JW initializer, L4 ladder, **wgtfacq root-cause fix** | 1 (9-day run executed; C5 coverage guard; pooch-swap + signature-change declarations) |
| S14 plan through dycore | `0c5b693` | substep-outer unrolling, ConcurrentCoupling publication, JW/SCM plan-hash pins, benchmark | 1 (doc fixes; gpu-leg PR note) |

## 3. Headline verification results

- **T0 ≡ T1 bitwise through the dycore (S14 exit gate):** the composed JW model
  (NonhydroSolver + HorizontalDiffusion, R02B04 × 35 levels, gtfn_cpu, fp64) advanced
  24 simulated hours (288 composed steps, 1440 dycore substeps) under the interpreted
  tier and the compiled execution plan **in lockstep, exactly equal at every step on
  every prognostic**. Zero per-step host traffic on the plan (settrace + name-map
  instrumentation); plan-hash pins tie the example scripts to their preset builders.
- **L4 (S13): symcon vs the upstream icon4py driver over 9 days is bitwise-zero at all
  37 six-hourly checkpoints**, while the ε-twin (vn +1e-13) envelope grows
  1.6e-6 → 3.8e-4 Pa — the composed model sits at the floor of the chaotic-growth
  envelope, not merely inside it. Reference/twin/symcon trajectories cached with
  sha256 manifests under `~/.cache/symcon/l4_reference/` (CI never regenerates).
- **L2 parity everywhere a granule was hosted** at the upstream tolerances verbatim
  (satad rtol 1e-12/atol 1e-13; graupel T rtol 1e-12, tracers atol 1e-12, rates
  9e-11; dycore predictor/corrector at dallclose defaults; diffusion vn 1e-8/1e-9,
  w 1e-14) — each tolerance cited to the exact upstream test at the pinned tag.
- **L8 gradients (S10):** Taylor slopes 2.000±0.005 (satad through the custom_root
  IFT, graupel, 10-step scan window); dot-product tests ≤1.4e-15 vs the 1e-10
  contract; FD cross-check on the example functional at rel. err. ~5e-10. Mutation
  probe confirmed the Taylor oracle catches a 10 % wrong tangent solve (slope 2 → 1).
- **Coupling formal orders (S04):** FC 2.03 / PS 1.03 / STS 1.00 / SUS 0.97 /
  SSUS(½) 1.99 on the ODE ladder; the same family self-converges on Burgers N=512 —
  all within the SPEC's ±0.15, with the k-ary Axpy term order pinned by
  reduction-order perturbation tests.
- **Dispatch benchmark (S14, observation):** JW per step T0 3.68 s vs T1 3.43 s
  (gtfn_cpu; −247 ms/step host-side, 6.7 % — kernel-dominated at this grid size), vs
  the kernel-free S05 toy at 64–101×. Bind cost 3.3 s once.

## 4. Findings worth remembering

### 4.1 The "pentagon-point" mystery → the wgtfacq K-domain bug (S12→S13)

S12's production path (NonhydroSolver built from an S11 file-read `IconGrid` +
factory statics) produced **rebuild-dependent, unbounded trajectory corruption**
(usually ≤2e-5, once 10 m/s on 6 % of edges; the reviewer later measured a bad
rebuild at 85 % of edges, bitwise-unequal across identical rebuilds within one
process). Initial theory — out-of-bounds reads through the 12 pentagon-point `-1`
connectivity entries icon4py deliberately retains on global grids — was
systematically falsified in S13 (cold-cache ICON-style padding did not remove it;
all solver inputs were proven bit-stable and archive-equal). Bisection isolated the
carrier to `wgtfacq_c`/`wgtfacq_e` alone: **both producers emit them as 3-level
fields on K-domain `[nlev−3, nlev)`, and the S12 static conversion rebuilt them at
`[0, 3)`** — every surface-adjacent stencil read went out of domain into heap
garbage. One-line domain-anchoring fix in the converter; the production path is now
bitwise deterministic across rebuilds and the S12 production test asserts trajectory
values. Lesson recorded: *gt4py fields carry domains, not just shapes — conversions
must preserve the K-anchor, and "nondeterministic across identical rebuilds" points
at out-of-domain reads, not at physics.*

### 4.2 Upstream icon4py findings (candidates for reports/PRs upstream)

- **Cold-glaciation water-budget leak in the graupel granule** (S08): supercooled qc
  at T≲233 K near the moist-domain top leaks a fixed absolute ~1e-3 kg/m² per column
  per Δt at the dry edge (relative worst 4.32e-4 in our test domain), suppressed by
  any coexisting ice-phase hydrometeor. Reproduced wrapper-free against the bare
  granule (committed as a tripwire test that collapses if an icon4py bump fixes it).
- **wgtfacq shifted-K-domain convention** (4.1 above) is easy to lose in conversion
  layers; upstream's serialized savepoints and factory agree with each other but the
  convention is only visible in the factory registration.
- **icon4py v0.2.0 vs ICON 2026.04 divergences** recorded at mining time: satad
  supersaturation factor + `w` input absent from icon4py (identical under default
  namelist); `SPECIFIC_HEAT_CAPACITY_ICE` 2108.0 vs ICON `ci` 2106.0 (dead code under
  `use_constant_latent_heat=True`, the default and the serialized-data config);
  upstream's multi-substep dycore test is MCH-only with a literal
  `# why is this not run for APE?` comment.

### 4.3 What the skeptical-review loop caught (the case for it)

Every step's review re-ran gates and probed tests adversarially. Genuine defects
caught before merge, per round: the CI mpi job's pytest exit-5 trap (S01); a
restart-protocol crash for components with empty output dicts (S03); ordering
constraints silently defeated by wrapper renaming (S04); a CF-under-multi-stage
compile error blaming the wrong cause (S05); a missing gpu datatest leg with a
docstring claiming it existed (S07); a conservation bound violated inside its own
hypothesis domain — latently red in CI (S08); six parity tolerances loosened and
misattributed to upstream, which actually pass at upstream-strict (S11); a false
"IAU is rejected" STATUS claim and an untested production path (S12) — the latter
escalating into the 4.1 root cause; an unexecuted 9-day acceptance criterion (S13),
resolved by actually running it. Two recurring reviewer techniques earned their
keep: *re-deriving every tolerance from the pinned upstream test* (never trusting
the implementer's citation), and *mutation-probing oracles* (would this test catch a
wrong gradient / a reordered reduction / a dropped bus application?).

### 4.4 Tolerance discipline (AGENTS.md rule 6) in practice

No SPEC tolerance was loosened anywhere. Where reality forced qualifications, they
were characterized measurements, not round-ups: S08's cold bound (measured worst
× ~2.3), S09's tracer negativity (−QMIN = −1e-15 vs observed −5.3e-23), S10's QMIN
atol floor on mixing ratios (icon4py's own L2 uses a *looser* 1e-12), S12's vn
atol 1e-11 on APE (upstream never stated an APE tolerance; measured 4.9–7.2e-12,
with a substep-boundary oracle proving the orchestration exact). Each carries a
sign-off flag (§5).

### 4.5 Infrastructure lessons

- **Persistent gt4py build cache** (`~/.cache/symcon/gt4py`, set in the core pytest
  plugin): warm-vs-cold is 18:30 vs 14:08 for the full fast gate, and ~2 min per
  graupel scan variant. The fast-gate ≤15-min acceptance holds warm, with thin
  margin dominated by three S08 embedded graupel cases — trunk candidates.
- **Chunk-resumable long runs** (S13 `make_reference.py`, S14 24 h equivalence):
  resume goes through the components' own restart protocols and was proven bitwise
  (a resumed leg landed exactly on the uninterrupted reference). Pitfall found: the
  S13 runner's `--run all` excludes the symcon leg (needs `--run symcon`) — cost one
  cycle; noted in S13 STATUS as a follow-up.
- **Reference data:** all via icon4py's datatest machinery into
  `~/.cache/symcon/icon4py-testdata` — GAUSS3D (57 MB), WK-torus (~1.6 GB), EXCLAIM
  APE R02B04 (~4 GB), JW (~14 GB), MCH (~11 GB). Nothing in git.
- **gpu-marked legs are present everywhere but have never executed** (no CUDA device
  in any implementation or review environment; all skip cleanly). First GPU-runner
  execution should be watched end-to-end.

## 5. Human sign-off ledger (blocking PR approval, per AGENTS.md)

| Step | Item | Where flagged |
|---|---|---|
| S05 | Zero-traffic acceptance operationalization (settrace can't see C-level `dict.__getitem__`; tracemalloc protocol) | S05 STATUS, deviations 4–5 banner |
| S08 | `CONSERVATION_RTOL_COLD = 1e-3` (characterized cold-glaciation leak; upstream report follow-up) | S08 STATUS |
| S09 | Tracer negativity `≥ −QMIN`; whole-run `CONSERVATION_RTOL = 1e-11` | S09 STATUS |
| S10 | QMIN atol floor on acceptances 1/7 | S10 STATUS tolerance note |
| S12 | vn `atol = 1e-11` on EXCLAIM_APE multi-substep parity (reviewer recommends granting) | S12 STATUS deviation 8 |
| S13 | `jablonowski_williamson` mandatory `static` kwarg (frozen-signature change); pooch→sha256-manifest swap | S13 STATUS deviations 6, 11 |
| S14 | "Bitwise per backend" evidence-backed for gtfn_cpu only (gpu leg never executed) | S14 STATUS review-fixes note |

## 6. Standing follow-ups (non-blocking, aggregated)

- Report the graupel cold-glaciation leak upstream; re-check the `dace` pre-release
  pin (`prerelease = "allow"`) at the next gt4py bump (S01/S08).
- Fold a component-config digest into `plan_hash` before T3 caches compiled
  artifacts by it (S05); route the CF functional carry through `functional_state()`
  or align SPEC wording (S10).
- CF under multi-stage schemes at T1 needs per-stage cache-slot aliasing (S05);
  adaptive `ratio_provider` under T1/T2 via the signature cache (S12/S14).
- CI: constraints-matrix jobs install no jax (F-tier silently skips there); dev
  environments on py≥3.11 resolve an unverified jax (S10). Fast-gate margin: move
  the three embedded graupel L2 cases to `slow` if it erodes (S14).
- Fold the symcon leg into `make_reference.py --run all` or rename the option (S13).
- `satad.py` still uses the `_i4_grid` friend access instead of S11's public
  property (cleanup); `names.py` re-assert should extend to `cf_name`/GRIB2 when
  populated (S06).

## 7. Repository state

`main` holds the complete slice; the 14 `step/SXX-*` branches are preserved for
one-PR-per-step publication. Import contracts (`core ↛ icon/bridges`,
`icon ↛ bridges`) held throughout — enforced by import-linter, never violated at
merge. `mypy --strict` clean on symcon-core (50 files) at every merge. No data
files, no dependency pin changes, no `docs/architecture/*` edits anywhere in the
series.
