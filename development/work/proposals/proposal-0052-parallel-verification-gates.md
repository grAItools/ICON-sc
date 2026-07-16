**Status:** graduated → spec 0052 (`development/work/specs/spec-0052-parallel-verification-gates.md` + `development/work/plans/plan-0052-parallel-verification-gates.md`); CI half is a follow-up taking the next free number when assigned.

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
| fast | `not gpu and not slow` | 740 | ~13–15 min | gt4py compile / CPU, low RAM |
| slow, no data | `slow and not gpu and not data` | 31 | ~5–13 min | 3 convergence modules (compile/CPU) |
| data, not slow | `data and not slow and not gpu` | 43 | ~7 min | reference loads (RAM/IO) |
| **data + slow** | `data and slow and not gpu` | 77 | **~32 min** | **55-test `test_static_fields_datatest.py`** |

Total ≈ 57–67 min of pytest. Two structural facts drive the design:

1. **The `data+slow` partition is 55 of 77 tests in one module.**
   `test_static_fields_datatest.py` holds 55 parametrized metrics/interpolation-parity
   tests, all on the `EXCLAIM_APE` reference (~8.7 GB extracted), each re-running the gt4py
   metrics/interpolation factories. Independent, compute-heavy, sharing a **read-only**
   reference — the case for spreading across workers, *but* every worker touching the module
   reloads the reference, so RAM caps the worker count.
2. **Data-marked tests only run where the 36 GB corpus lives** (`DATATEST_AVAILABLE` /
   `skipif`, `symcon-icon[datatest]`). GitHub-hosted CI runners can't hold it, so the data
   partitions are a **local-machine** problem; CI's realistic long pole is the compute
   partitions.

## Approach — two-layer parallelism on one shared partition scheme

Keep the four existing marker partitions as the single unit of work for local and CI. Add
parallelism inside and across them, a compile warm-up, and correctness guardrails.

### Per-partition scheduling policy (core decision)

`--dist` mode and worker cap are chosen **per partition** by resource profile; a global
setting would either serialize the 55-test module or OOM the box.

| Partition | `--dist` | `-n` (start target*) | Rationale |
|---|---|---|---|
| fast | `loadscope` | 12 | 40+ module groups fill workers; `loadscope` preserves the many `scope="module"` fixtures |
| slow, no data | `load` | 8 | ~7 module groups only; `load` splits the 9-test order-convergence modules; their module fixtures are cheap grids |
| data, not slow | `loadscope` | 3–4 | RAM-bounded; keep each module's savepoints on one worker |
| **data + slow** | **`load`** | **2–3** | Must split the 55-test module; each worker reloads `EXCLAIM_APE`, so RAM caps the count |

*Every `-n` is a **starting target the calibration below confirms or lowers** (the two data
caps especially). Chosen caps and their measured RSS ceiling get recorded in
`policies/verification-gates.md` in the executing PR (keep-current rule).

### gt4py compile warm-up (pre-step)

Concurrent xdist workers first-compiling the *same* gtfn variant into the shared persistent
cache (`~/.cache/symcon/gt4py`) can race or redundantly compile. A short compile-only warm-up
runs **before** the timed partitions, populating the cache and removing both the race and the
compile *variance* from the measured gate. Idempotent; cheap on a warm cache. Never points at
a cold cache (verification-gates.md "Caches" rule).

### Local driver — `tools/run_gate.py`

A Python script (fits the repo `tools/` dir; expresses waves, RSS calibration, and verbatim
log capture) orchestrates: (1) lint battery (ruff/mypy/lint-imports) first as cheap
fail-fast; (2) the warm-up; (3) **Wave 1** — `fast` (`-n 10`, compute) concurrently with
`data+slow` (`-n 2`, memory), complementary profiles ≈ 12 cores / ≈ 14 GB; (4) **Wave 2** —
`slow-no-data` (`-n 6`) concurrently with `data-not-slow` (`-n 3`); (5) aggregate exit codes,
**any** non-zero fails the gate, each partition's full output preserved **verbatim** (the
report-failures-verbatim rule). **OOM guard:** never two memory-heavy data partitions in one
wave. The driver shells out to the **exact** existing marker commands, adding only
`-n`/`--dist`; it **never** injects `-x`/`-k`/`--ignore` or marker edits, and it does not
touch test internals.

## In scope (WU 0052 — local parallel gate; graduates to spec-0052)

- Add `pytest-xdist` (+ `execnet`) to the `dev` group and `constraints/cpu-ci.txt`; regenerate
  `uv.lock`. The **one new dev dependency** — not a gt4py/icon4py pin bump, but trunk-visible:
  raised as a `TD-PENDING` in the report and a decision row in `REGISTRY.md §3`.
- `tools/run_gate.py` implementing the per-partition policy, warm-up, and waves above.
- Calibration: measure peak RSS of `data+slow` and `data-not-slow` at `-n 1..4`; set each cap
  to the largest `-n` under ~75 % of 31 GB; record the caps **and** the measured RSS ceiling
  in `policies/verification-gates.md`.
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

1. All eight gate commands in `policies/verification-gates.md` remain green when driven by
   `tools/run_gate.py`, with **identical `passed`/`skipped`/`deselected` counts** to the serial
   baseline. Allowed skips unchanged: the 1 mpi opt-in, gpu-no-device, the 1 upstream MCH
   diffusion skip — any new skip is a finding to explain.
2. **Independence gate:** each partition run serially and in parallel yields identical
   counts; the parallel run repeated twice shows no order-flakiness. A parallel/serial
   divergence is root-caused and the offending test fixed — never masked or reordered-to-hide.
3. Peak RSS during the parallel gate stays under ~75 % of 31 GB (no OOM); the calibrated caps
   and measured ceiling are recorded in `policies/verification-gates.md`.
4. The baseline table and (if counts change) file-count/count rows are updated in the same PR.
5. The new dev dep is recorded as a decision row; `uv.lock` and `constraints/cpu-ci.txt`
   updated coherently; `uv sync --locked` / the constraints path still resolve.

**Expected outcome:** ~57–67 min → **~18–22 min** target (dominated by the `data+slow` cap;
lower if calibration permits `-n 4` there). ≈ 3× wall-time reduction.

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
