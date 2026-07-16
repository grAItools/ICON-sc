#!/usr/bin/env python3
"""Run the verification-gate battery (`development/policies/verification-gates.md`).

An accelerated *executor* of the gate, never a redefinition of it: every pytest invocation
below is the policy's marker command verbatim, plus `-n`/`--dist` and nothing else. The
marker expressions in the policy remain the canonical statement of what the gate runs.

Modes:
  (default)            full parallel gate — lint battery, then wave 1, then wave 2
  --serial             the marker commands with no -n/--dist: the baseline oracle
  --partition <name>   one partition at its spec-table -n/--dist

Scheduling comes from spec-0052's per-partition table (work unit 0052), which is the single
source of truth for every `--dist`/`-n` value; `PARTITIONS` below transcribes it. The waves
pair one reference-loading ("RAM-heavy") partition with one compute-bound partition. That is
only sound because 0052 made the partitions disjoint: the `fast` expression excludes `data`,
so `fast` carries no reference loads. Before that fix `fast` silently contained all 43
`data, not slow` tests and the pairing would have stacked reference loads. `_check_waves()`
asserts the invariant rather than trusting this comment.

Exit code is non-zero iff any partition or lint check failed. On failure the offending
partition's output is reproduced verbatim (verification-gates.md: report the full failure
block, never a summary).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import os
import pathlib
import subprocess
import sys
import threading
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
_MiB = 1024 * 1024


@dataclasses.dataclass(frozen=True)
class Partition:
    """One gate partition. `marker`/`dist`/`workers` transcribe spec-0052's table.

    `workers == 0` means "no xdist at all" and `dist` is then None: the partition runs in a
    single process even in the parallel gate. That is a scheduling choice like any other —
    for a partition xdist cannot speed up, it is the fastest *and* lowest-RAM option.
    """

    name: str
    marker: str
    dist: str | None
    workers: int
    ram_heavy: bool
    expected: str

    def __post_init__(self) -> None:
        if (self.dist is None) != (self.workers == 0):
            raise SystemExit(f"{self.name}: dist and workers disagree on whether xdist is used")


#: spec-0052 "Per-partition policy (the single authoritative table)". The data caps are
#: calibration outputs (0052 Item D) — change them only with per-wave RSS evidence.
PARTITIONS: dict[str, Partition] = {
    "fast": Partition("fast", "not gpu and not slow and not data", "load", 10, False, "696p/1s"),
    # Serial by calibration (0052 Item D): 7:39 serial vs 8:16 at -n 6, measured alone. The
    # spec's -n 6 was a "starting target"; this lowers it on evidence. Second benefit: wave 2
    # drops from 9 worker processes to 4, and wave contention — not xdist — is what actually
    # costs this battery time (data-noslow: 6:38 alone, 14:02 when paired with -n 6 here).
    "slow-nodata": Partition("slow-nodata", "slow and not gpu and not data", None, 0, False, "31p"),
    # Keeps -n 3: the one partition xdist genuinely helps (6:38 at -n 3 vs 8:12 serial, alone).
    "data-noslow": Partition(
        "data-noslow", "data and not slow and not gpu", "loadscope", 3, True, "43p"
    ),
    # Serial by measurement, not by omission (spec-0052 Amendment 2, TD-52.2). This partition
    # does not scale: one test, test_jw_t0_t1_bitwise_24h[gtfn_cpu], is 1519s of its 2012s
    # (75%), and no -n splits a single test. The spec's original premise — 55 static-fields
    # tests each re-running the gt4py factories — is false; _get_static is memoized per
    # process, so those 55 cost ~12s total and xdist only duplicates that cost per worker.
    # Measured: serial 33:04/5.0GiB, -n 2 33:08/6.4GiB, -n 4 35:13/9.0GiB. Serial wins twice.
    # It stays in wave 1 so it still overlaps `fast`; that overlap is its whole parallelism.
    "data-slow": Partition("data-slow", "data and slow and not gpu", None, 0, True, "76p/1s"),
}

#: One RAM-heavy partition per wave (asserted by `_check_waves`).
WAVES: tuple[tuple[str, ...], ...] = (("fast", "data-slow"), ("slow-nodata", "data-noslow"))

#: (log name, command). Names must be distinct — they name the log file, and two commands
#: sharing one would silently overwrite each other's verbatim output.
LINT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff-check", ("uv", "run", "ruff", "check", ".")),
    ("ruff-format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "mypy", "--strict", "-p", "symcon.core")),
    ("lint-imports", ("uv", "run", "lint-imports")),
)


def _check_waves() -> None:
    """Every partition scheduled exactly once; at most one RAM-heavy partition per wave."""
    scheduled = [name for wave in WAVES for name in wave]
    if sorted(scheduled) != sorted(PARTITIONS):
        raise SystemExit(f"wave composition drifted: {sorted(scheduled)} != {sorted(PARTITIONS)}")
    for wave in WAVES:
        heavy = [n for n in wave if PARTITIONS[n].ram_heavy]
        if len(heavy) > 1:
            raise SystemExit(f"wave {wave} pairs two RAM-heavy partitions {heavy}: OOM risk")


def _pytest_cmd(part: Partition, parallel: bool, workers: int | None = None) -> list[str]:
    """The policy's marker command, plus -n/--dist when parallel. Nothing else, ever.

    `workers` overrides the spec table for calibration sweeps (0052 Item D); 0 means run
    without xdist at all, which is the true per-partition serial baseline.
    """
    n = part.workers if workers is None else workers
    cmd = ["uv", "run", "pytest", "packages", "-m", part.marker, "-q"]
    if parallel and n > 0:
        # A calibration override can ask for workers on a partition the table runs serially
        # (dist is None there); `load` is the sweep default that measured it.
        cmd += ["-n", str(n), "--dist", part.dist or "load"]
    _assert_no_selection_flags(cmd)
    return cmd


_FORBIDDEN = ("-x", "--exitfirst", "-k", "--ignore", "--deselect", "-p")


def _assert_no_selection_flags(cmd: list[str]) -> None:
    """Guard the 'scheduling only' contract: -n/--dist never change *what* is selected."""
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
    """Peak RSS of this process tree while a wave runs (0052 Item D measures the *wave*)."""

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
    print(f"  [{status}] {res.name:12s} {res.seconds / 60:5.1f} min  {summary}")


def _report_failures(results: list[Result]) -> None:
    """Verbatim, per verification-gates.md — never a summary."""
    for res in (r for r in results if r.rc != 0):
        print(f"\n{'=' * 78}\nFAILED: {res.name}  (exit {res.rc})  — full output below, verbatim")
        print(f"{'=' * 78}\n{res.log.read_text(errors='replace')}")


def _run_wave(wave: tuple[str, ...], logdir: pathlib.Path, parallel: bool) -> list[Result]:
    sampler = _RssSampler()
    sampler.start()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(wave)) as pool:
        futures = [pool.submit(_run, n, _pytest_cmd(PARTITIONS[n], parallel), logdir) for n in wave]
        results = [f.result() for f in futures]
    peak = sampler.stop()
    print(f"  peak RSS this wave: {peak / 1024:.1f} GiB")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--serial", action="store_true", help="baseline oracle: no -n/--dist")
    mode.add_argument("--partition", choices=sorted(PARTITIONS), help="run one partition")
    ap.add_argument("--no-lint", action="store_true", help="skip the lint battery")
    ap.add_argument("--logdir", type=pathlib.Path, help="default: /tmp/symcon-gate-<pid>")
    ap.add_argument(
        "--workers",
        type=int,
        help="calibration only (0052 Item D): override --partition's -n; 0 = no xdist (serial)",
    )
    args = ap.parse_args()
    if args.workers is not None and not args.partition:
        ap.error("--workers only applies to --partition")

    _check_waves()
    logdir = args.logdir or pathlib.Path(f"/tmp/symcon-gate-{os.getpid()}")
    logdir.mkdir(parents=True, exist_ok=True)
    print(f"logs: {logdir}")

    started = time.monotonic()
    results: list[Result] = []

    if args.partition:
        cmd = _pytest_cmd(PARTITIONS[args.partition], True, args.workers)
        # Sample RSS here too: Item D's caps must come from measurement, not assumption.
        sampler = _RssSampler()
        sampler.start()
        results.append(_run(args.partition, cmd, logdir))
        peak = sampler.stop()
        _emit(results[-1])
        print(f"  peak RSS: {peak / 1024:.1f} GiB  ({' '.join(cmd[3:])})")
    elif args.serial:
        for name, cmd in () if args.no_lint else LINT:
            results.append(_run(name, list(cmd), logdir))
            _emit(results[-1])
        for name in PARTITIONS:
            results.append(_run(name, _pytest_cmd(PARTITIONS[name], False), logdir))
            _emit(results[-1])
    else:
        if not args.no_lint:
            print("lint battery (cheap fail-fast):")
            for name, cmd in LINT:
                results.append(_run(name, list(cmd), logdir))
                _emit(results[-1])
            if any(r.rc for r in results):
                _report_failures(results)
                return 1
        for i, wave in enumerate(WAVES, 1):
            print(f"wave {i}: {' || '.join(wave)}")
            wave_results = _run_wave(wave, logdir, parallel=True)
            for res in wave_results:
                _emit(res)
            results += wave_results

    failed = [r for r in results if r.rc != 0]
    _report_failures(results)
    print(f"\nwall-time: {(time.monotonic() - started) / 60:.1f} min")
    print("GATE: " + ("FAILED — " + ", ".join(r.name for r in failed) if failed else "green"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
