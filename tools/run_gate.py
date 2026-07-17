#!/usr/bin/env python3
"""Run the verification-gate battery (`development/policies/verification-gates.md`).

An accelerated *executor* of the gate, never a redefinition of it: every pytest invocation
below is the policy's marker command **verbatim**, with no flags added at all. The marker
expressions in the policy remain the canonical statement of what the gate runs.

**The speed-up is not parallelism.** It is Item A: the `fast` expression did not exclude
`data`, so the 43 `data, not slow` tests ran inside `fast` *and again* in their own partition.
Removing them takes `fast` from ~13-15 min to ~2:28 and the battery from ~62 to ~50 min. That
result rests on set arithmetic (union 848 before and after, intersection empty), not on
timing, so no measurement noise can touch it.

**Everything else was tried and measured to fail** (0052 Amendments 4-5). This driver is
therefore sequential, and deliberately so:

- **pytest-xdist: rejected** (TD-52.1). Run-to-run variance here is +/-15%, worse on the
  `data` partitions, which are page-cache bound (EXCLAIM APE is 8.7 GB extracted against ~10
  GB of cache) — their timings track cache warmth, not scheduling. Every apparent xdist gain
  sat inside that noise: `fast` is 2:28 serial vs 2:43 at `-n 10` (means of 4 and 3 samples,
  serial *ahead*), and `data-noslow`'s 19% gain did not reproduce (6:38 -> >10:00, same
  config, idle host).
- **Concurrent partitions: rejected** (Amendment 5). Two concurrent lanes measured 51.1 min
  vs 51.9 sequential — nothing — while each partition slowed 1.5-3.2x and total wall-time was
  conserved.

**What is measured, and what is not.** Measured: a single pytest process uses ~1.1 of 16 cores
with the host 90% idle and `wa=0` (neither CPU- nor IO-bound), yet running two partitions
concurrently slows each by 1.5-3.2x and conserves total wall-time. Something serializes them.

**The mechanism is NOT identified** — do not repeat this work unit's mistake of asserting one.
An earlier draft blamed gt4py's build-cache lock; that was checked against the source and is
wrong as stated: `compiler.py:73` locks `cache.get_cache_folder(inp, ...)`, i.e. the
*per-program* directory (490 lock files across 218 dirs — a global lock would be one), and a
`workflow.CachedStep` in-memory dict sits above the `Compiler`, so warm in-process lookups
never reach it at all. A briefly-held per-program lock cannot plausibly account for a 3.2x
stretch. Candidates worth profiling: memory bandwidth, page-cache eviction between partitions
that each want 8.7 GB of references, or same-program lock contention. Nobody has profiled it.

Sequential is therefore justified by the *measurements*, which stand on their own, not by any
mechanism. The remaining floor is one unsplittable 1519 s test
(`test_jw_t0_t1_bitwise_24h[gtfn_cpu]`, 75% of `data-slow`).

Before adding any parallelism back, benchmark it properly: multiple samples per configuration,
controlled page cache, one variable at a time. Single-sample comparisons on this battery
measure the page cache.

Modes:
  (default)            lint battery, then every partition in sequence
  --serial             accepted as an explicit alias of the default (the spec's frozen CLI)
  --partition <name>   one partition alone
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import subprocess
import sys
import threading
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
_MiB = 1024 * 1024

#: 75% of the 31 GB gate host (spec-0052 acceptance 4). Measured, never assumed: the sampler
#: below reports the real peak of the run and `main` fails the gate if it is exceeded.
RSS_BUDGET_MIB = 23 * 1024


@dataclasses.dataclass(frozen=True)
class Partition:
    """One gate partition. `marker` is the policy's expression, used verbatim."""

    name: str
    marker: str
    ram_heavy: bool
    expected: str


#: The four partitions, disjoint since 0052 Item A. No worker counts, no `--dist`: every
#: partition runs in a single process (0052 Amendment 4).
PARTITIONS: dict[str, Partition] = {
    "fast": Partition("fast", "not gpu and not slow and not data", False, "696p/1s"),
    "slow-nodata": Partition("slow-nodata", "slow and not gpu and not data", False, "31p"),
    "data-noslow": Partition("data-noslow", "data and not slow and not gpu", True, "43p"),
    "data-slow": Partition("data-slow", "data and slow and not gpu", True, "76p/1s"),
}

#: Execution order. **Sequential, by measurement** (0052 Amendment 5): concurrency was tried
#: and does not work on this battery. Running the partitions in two concurrent lanes measured
#: 51.1 min against 51.9 min sequential — a 1.5% difference against a +/-15% noise floor, i.e.
#: nothing — while every partition slowed 1.5-3.2x (data-slow 33:04 -> 50:06, slow-nodata
#: 7:39 -> 19:50). Total wall-time was conserved: the classic signature of a shared
#: serializing resource, not of parallel work.
#:
#: What serializes them is NOT known (see the module docstring): the gate is neither CPU- nor
#: IO-bound (~1.1 of 16 cores, host 90% idle, wa=0), and the gt4py-lock explanation an earlier
#: draft asserted does not survive reading the source. The decision rests on the measurements,
#: which need no mechanism to be valid.
#:
#: The gate's actual win is Item A (disjointness), which needs no concurrency at all.
ORDER: tuple[str, ...] = ("fast", "slow-nodata", "data-noslow", "data-slow")

#: (log name, command). Names must be distinct — they name the log file, and two commands
#: sharing one would silently overwrite each other's verbatim output.
LINT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff-check", ("uv", "run", "ruff", "check", ".")),
    ("ruff-format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "mypy", "--strict", "-p", "symcon.core")),
    ("lint-imports", ("uv", "run", "lint-imports")),
)


def _check_order() -> None:
    """Every partition scheduled exactly once."""
    if sorted(ORDER) != sorted(PARTITIONS):
        raise SystemExit(f"schedule drifted: {sorted(ORDER)} != {sorted(PARTITIONS)}")


def _pytest_cmd(part: Partition) -> list[str]:
    """The policy's marker command. Nothing added, ever."""
    cmd = ["uv", "run", "pytest", "packages", "-m", part.marker, "-q"]
    _assert_no_selection_flags(cmd)
    return cmd


_FORBIDDEN = ("-x", "--exitfirst", "-k", "--ignore", "--deselect", "-p")


def _assert_no_selection_flags(cmd: list[str]) -> None:
    """Guard the 'scheduling only' contract: the driver never changes *what* is selected.

    A tripwire for future edits, not a live check: today's caller passes a list literal built
    two lines above, so this cannot fire. It fires the moment someone adds a flag there.
    """
    for flag in _FORBIDDEN:
        if flag in cmd:
            raise SystemExit(f"refusing to run: {flag!r} changes selection ({' '.join(cmd)})")


# ---------------------------------------------------------------------------- memory sampling


def _descendants(root: int) -> list[int]:
    """PIDs of `root` and everything under it, via /proc (no psutil dependency)."""
    children: dict[int, list[int]] = {}
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(ppid, []).append(int(entry.name))
    out, stack = [], [root]
    while stack:
        pid = stack.pop()
        out.append(pid)
        stack.extend(children.get(pid, []))
    return out


def _tree_rss_mib(root: int) -> int:
    total = 0
    for pid in _descendants(root):
        try:
            for line in (pathlib.Path("/proc") / str(pid) / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError):
            continue
    return total // _MiB


class _RssSampler(threading.Thread):
    """Peak RSS of this process tree while the gate runs."""

    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(daemon=True)
        self.peak_mib = 0
        # NOT `_stop`: threading.Thread._stop() is a real private method that join()
        # calls internally, and shadowing it with an Event makes join() raise
        # "TypeError: 'Event' object is not callable".
        self._done = threading.Event()
        self._interval = interval

    def run(self) -> None:
        while not self._done.is_set():
            self.peak_mib = max(self.peak_mib, _tree_rss_mib(os.getpid()))
            self._done.wait(self._interval)

    def stop(self) -> int:
        self._done.set()
        self.join(timeout=5)
        return self.peak_mib


# ---------------------------------------------------------------------------- execution


@dataclasses.dataclass
class Result:
    name: str
    rc: int
    seconds: float
    log: pathlib.Path


def _run(name: str, cmd: list[str], logdir: pathlib.Path) -> Result:
    log = logdir / f"{name}.log"
    start = time.monotonic()
    with log.open("wb") as fh:
        fh.write(f"$ {' '.join(cmd)}\n\n".encode())
        fh.flush()
        rc = subprocess.Popen(cmd, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT).wait()
    return Result(name, rc, time.monotonic() - start, log)


def _emit(res: Result) -> None:
    tail = res.log.read_text(errors="replace").strip().splitlines()
    summary = tail[-1] if tail else "(no output)"
    status = "ok " if res.rc == 0 else "FAIL"
    print(f"  [{status}] {res.name:12s} {res.seconds / 60:5.1f} min  {summary}", flush=True)


def _report_failures(results: list[Result]) -> None:
    """Verbatim, per verification-gates.md — never a summary."""
    for res in (r for r in results if r.rc != 0):
        print(f"\n{'=' * 78}\nFAILED: {res.name}  (exit {res.rc})  — full output below, verbatim")
        print(f"{'=' * 78}\n{res.log.read_text(errors='replace')}")


def _run_partitions(logdir: pathlib.Path) -> list[Result]:
    """Run every partition in sequence. A failure never skips the rest: the gate reports
    every partition's outcome, and a skipped partition is a hidden one."""
    results = []
    for name in ORDER:
        res = _run(name, _pytest_cmd(PARTITIONS[name]), logdir)
        _emit(res)
        results.append(res)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--serial",
        action="store_true",
        help="explicit alias of the default (kept: the spec's frozen CLI names it)",
    )
    mode.add_argument("--partition", choices=sorted(PARTITIONS), help="run one partition alone")
    ap.add_argument("--no-lint", action="store_true", help="skip the lint battery")
    ap.add_argument("--logdir", type=pathlib.Path, help="default: /tmp/symcon-gate-<pid>")
    args = ap.parse_args()

    _check_order()
    logdir = args.logdir or pathlib.Path(f"/tmp/symcon-gate-{os.getpid()}")
    logdir.mkdir(parents=True, exist_ok=True)
    print(f"logs: {logdir}", flush=True)

    started = time.monotonic()
    results: list[Result] = []
    sampler = _RssSampler()
    sampler.start()

    if args.partition:
        results.append(_run(args.partition, _pytest_cmd(PARTITIONS[args.partition]), logdir))
        _emit(results[-1])
    else:
        if not args.no_lint:
            print("lint battery (cheap fail-fast):", flush=True)
            for name, cmd in LINT:
                results.append(_run(name, list(cmd), logdir))
                _emit(results[-1])
            if any(r.rc for r in results):
                sampler.stop()
                _report_failures(results)
                return 1
        print(f"partitions (sequential): {' -> '.join(ORDER)}", flush=True)
        results += _run_partitions(logdir)

    peak = sampler.stop()
    failed = [r for r in results if r.rc != 0]
    _report_failures(results)

    over = peak > RSS_BUDGET_MIB
    print(f"\npeak RSS: {peak / 1024:.1f} GiB  (budget {RSS_BUDGET_MIB / 1024:.0f} GiB)")
    if over:
        print("GATE: FAILED — peak RSS exceeded the budget")
    print(f"wall-time: {(time.monotonic() - started) / 60:.1f} min")
    print("GATE: " + ("FAILED — " + ", ".join(r.name for r in failed) if failed else "green"))
    return 1 if (failed or over) else 0


if __name__ == "__main__":
    sys.exit(main())
