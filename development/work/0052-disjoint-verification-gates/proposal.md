**Status:** graduated → spec 0052 (`development/work/specs/spec-0052-disjoint-verification-gates.md` + `development/work/plans/plan-0052-disjoint-verification-gates.md`); CI half is a follow-up taking the next free number when assigned. **On any detail, the spec governs** — review corrected this proposal's partition analysis and worker counts before graduation; the corrections are folded in below rather than left as a misleading account.

# 0052 — Parallel verification gates (bounded two-layer test parallelism)
**After:** 0051 · **Architecture:** n/a (tooling; no `symcon.*` source change) · **Policies:** `policies/verification-gates.md`, `policies/agent-workflow.md`

## Goal

Cut the wall-time of the verification-gate battery (`policies/verification-gates.md`)
**without removing any test or relaxing any acceptance criterion** — no tolerance creep,
no reduction-order change, no marker edits, no `-x`/`-k`/`--ignore`. Parallelism changes
*scheduling only*, never *what runs*. Machine of record: 16 cores, 31 GB RAM (the gate host).

## Problem

The gate runs **fully serially** — `pytest-xdist` is not installed — so the cores idle.
Measured serial baseline (warm caches, per the current baseline table):

| Partition | Marker expr | Tests | Time | Bottleneck |
|---|---|---|---|---|
| fast | `not gpu and not slow` | 740 | ~13–15 min | gt4py compile / CPU — **and 43 reference-loading `data` tests, see fact 1** |
| slow, no data | `slow and not gpu and not data` | 31 | ~5–13 min | 3 convergence modules (compile/CPU) |
| data, not slow | `data and not slow and not gpu` | 43 | ~7 min | reference loads (RAM/IO) |
| **data + slow** | `data and slow and not gpu` | 77 | **~32 min** | **55-test `test_static_fields_datatest.py`** |

Total ≈ 57–67 min of pytest, but the partitions **overlap**: naive sum 891, true union 848.
Three structural facts drive the design:

1. **The `data+slow` partition is 55 of 77 tests in one module.**
   `test_static_fields_datatest.py` holds 55 parametrized metrics/interpolation-parity
   tests, all on the `EXCLAIM_APE` reference (~8.7 GB extracted), each re-running the gt4py
   metrics/interpolation factories. Independent, compute-heavy, sharing a **read-only**
   reference — the case for spreading across workers, *but* every worker touching the module
   reloads the reference, so RAM caps the worker count.
2. **The partitions are not disjoint: `fast` contains `data, not slow`.** `not gpu and not
   slow` never excludes `data`, so all 43 reference-loading `data, not slow` tests run inside
   `fast` *and again* in their own partition (verified: 43/43 inside, 0 outside; union 848 vs
   naive sum 891). This falsifies the obvious design — `fast` is **not** a low-RAM partition,
   so pairing it with `data+slow` for "complementary profiles" would stack reference loads,
   and an OOM guard phrased over marker *names* would assert something untrue about what the
   markers *select*. Fixing the boundary (`fast` → `not gpu and not slow and not data`) makes
   the partitions disjoint and removes ~7 min of duplicated work, with the union unchanged at
   848 — a partition-boundary change, not a coverage change.
3. **Data-marked tests only run where the 36 GB corpus lives** (`DATATEST_AVAILABLE` /
   `skipif`, `symcon-icon[datatest]`). GitHub-hosted CI runners can't hold it, so the data
   partitions are a **local-machine** problem; CI's realistic long pole is the compute
   partitions.

## Approach — two-layer parallelism on a disjoint partition scheme

Make the four marker partitions disjoint (fact 2), then add parallelism inside and across
them, plus correctness guardrails.

### Per-partition scheduling policy (core decision)

`--dist` mode and worker cap are chosen **per partition** by resource profile; a global
setting would either serialize the 55-test module or OOM the box. **The spec's table is
authoritative** — reproduced here only as the rationale record:

| Partition | `--dist` | `-n` | Rationale |
|---|---|---|---|
| fast (`…and not data`) | `load` | 10 | Reference loaders gone (fact 2) → genuinely low RAM. `load` spreads the 89-test `test_scheme_constants.py` group that `loadscope` would pin to one worker; only ~56/697 tests use module-scoped fixtures, which under `load` simply re-run per worker — `loadscope` is a performance choice, not a correctness one |
| slow, no data | `load` | 6 | ~7 module groups only; `load` splits the 9-test order-convergence modules; their module fixtures are cheap grids |
| data, not slow | `loadscope` | 3 | RAM-bounded; keep each module's savepoints on one worker |
| **data + slow** | **`load`** | **2** | Must split the 55-test module; each worker reloads `EXCLAIM_APE`, so RAM caps the count |

The two data caps are **starting targets that calibration confirms or lowers**, measured on
the *waves as run* — a cap safe for a partition alone can still OOM once the paired partition
is layered on. Chosen caps and the measured per-wave RSS ceiling get recorded in
`policies/verification-gates.md` in the executing PR (keep-current rule).

### The gt4py compile-race question (deliberately unanswered here)

Concurrent xdist workers first-compiling the *same* gtfn variant into the shared persistent
cache (`~/.cache/symcon/gt4py`) *may* race or redundantly compile — but that is an assumption,
and the gate baseline is warm caches, so a warm-up's value is unproven. The spec therefore
asks the work unit to **establish whether gt4py's cache is concurrency-safe and act on the
answer**, rather than building a mitigation blind. (An earlier draft proposed a
"compile-only pass" warm-up; `--collect-only` executes no test body and so compiles nothing —
it would have been a no-op shipped as a safeguard.)

### Local driver — `tools/run_gate.py`

A Python script (fits the repo `tools/` dir; expresses waves, RSS calibration, and verbatim
log capture) orchestrates: (1) lint battery (ruff/mypy/lint-imports) first as cheap
fail-fast; (2) **Wave 1** — `fast` (`-n 10`) concurrently with `data+slow` (`-n 2`); (3)
**Wave 2** — `slow-no-data` (`-n 6`) concurrently with `data-not-slow` (`-n 3`); (4) aggregate
exit codes, **any** non-zero fails the gate, each partition's full output preserved
**verbatim** (the report-failures-verbatim rule). **OOM guard:** one reference-loading
partition per wave — which only becomes true once fact 2's boundary fix lands; stated over
marker names alone it would be false, since today's `fast` carries 43 reference loaders of its
own. The driver shells out to the marker commands, adding only `-n`/`--dist`; it **never**
injects `-x`/`-k`/`--ignore` or marker edits, and it does not touch test internals.

## In scope (WU 0052 — local parallel gate; graduates to spec-0052)

- Make the four partitions disjoint: `fast` → `not gpu and not slow and not data` (fact 2),
  with the union (848) unchanged as the proof that no coverage moved.
- Add `pytest-xdist` to the `dev` group as a lower-bound declaration; regenerate `uv.lock`.
  **`constraints/cpu-ci.txt` is not touched**: it pins no pytest plugin at all (`pytest`,
  `pytest-cov`, `pytest-mpi`, `ruff`, `mypy`, `hypothesis` are all absent), so xdist does not
  belong there — now or in the CI follow-up. The **one new dev dependency** is not a
  gt4py/icon4py pin bump, but is trunk-visible: raised as a `TD-PENDING` in the report and a
  decision row in `REGISTRY.md §3`.
- `tools/run_gate.py` implementing the per-partition policy and waves above.
- Calibration: measure peak RSS **of each wave as it actually runs** (including `fast`'s own
  contribution) while sweeping the data caps `-n 1..4`; set each cap to the largest `-n` whose
  *wave* peak stays under ~75 % of 31 GB; record the caps **and** the measured per-wave RSS
  ceiling in `policies/verification-gates.md`.
- Answer the gt4py concurrent-compile question with evidence and act on it.
- Update `policies/verification-gates.md`: present the parallel driver as the canonical gate,
  **keep the serial marker commands documented as the fallback / baseline oracle** (they are
  what the independence gate validates against), and update the baseline table with parallel
  wall-times.

## Out of scope

- Changing what any test asserts, its tolerances, its markers, or its reduction order.
- Refactoring `_get_static` / the static-fields factory recomputation across the 55 tests (a
  possible future efficiency win, but it alters test structure — not a scheduling change).
- Dependency-pin bumps (gt4py/icon4py) — a trunk decision, untouched.
- GPU/MPI gate timing.
- **CI parallelism** — deferred to the follow-up work unit below.

## Frozen interfaces

None for the local gate: `tools/run_gate.py` is a new orchestrator over the existing marker
commands and adds no importable API; no `symcon.*` source or public interface changes; no new
cross-boundary imports (import-linter contracts stay `2 kept, 0 broken`). (The mandatory
frozen-interface section is restated at spec time.)

## Acceptance criteria

(Superseded in detail by the spec's acceptance criteria; kept as the scope record.)

1. **Coverage invariance:** the union across the four partitions is 848 before and after the
   `fast` boundary change, and `fast ∩ data-noslow = ∅`. This is what distinguishes a
   partition-boundary change from a silent coverage loss, and it gates the whole item.
2. All gate commands remain green when driven by `tools/run_gate.py`, with **identical
   `passed`/`skipped` counts** to the serial baseline on the same expressions. Allowed skips
   unchanged: the 1 mpi opt-in, gpu-no-device, the 1 upstream MCH diffusion skip — any new
   skip is a finding to explain.
3. **Independence gate:** each partition run serially and in parallel yields identical counts;
   the parallel run repeated twice shows no order-flakiness. A parallel/serial divergence is
   root-caused and the offending test fixed — never masked or reordered-to-hide.
4. Peak RSS **of each wave as run** stays under ~75 % of 31 GB (no OOM); the calibrated caps
   and measured per-wave ceiling are recorded in `policies/verification-gates.md`.
5. The baseline table is updated in the same PR, `fast`'s count drop attributed line-by-line
   to the boundary change with the union as evidence.
6. The new dev dep is recorded as a decision row; `uv.lock` regenerated; `uv sync --locked`
   still resolves; `constraints/cpu-ci.txt` untouched (it pins no pytest plugin).

**Expected outcome:** ~57–67 min → **~18–22 min** target, dominated by the `data+slow` cap and
now also helped by the ~7 min of duplicated `data, not slow` work leaving the battery. The
target rests on an assumption worth naming: near-linear speedup of the 55-test module at
`-n 2` despite each worker reloading 8.7 GB. Calibration measures it rather than assuming it.

## Follow-up work unit (CI parallelism — next free number at assignment)

Not allocated here (register rule: allocate at assignment). Scope when assigned:
- Cache `~/.cache/symcon/gt4py` in CI via `actions/cache` (keyed on lockfile + source hash) —
  CI compiles cold today; likely the single biggest CI win.
- Split the serial `test-cpu.yml` CPU job into a marker matrix (`fast`, `slow-no-data`) as
  parallel jobs, each `-n auto` (2-core runner → `-n 2`).
- **Investigate first:** whether `serialbox4py` installs in the locked CI env. If not, the
  data tests already `skipif`-skip and CI is unaffected; if it does, confirm current behavior
  before changing anything. Do not assume the 36 GB corpus is fetchable on a 14 GB-disk runner.

## Residual risk

- *Hidden inter-test dependency* surfaced by parallel → mitigated by acceptance #2; fixing it
  is a real improvement.
- *OOM* if peak RSS exceeds a warm-load estimate → mitigated by the calibration safety
  fraction and the single-memory-partition-per-wave guard.
- *gt4py cache races* → mitigated by the warm-up pre-step.
