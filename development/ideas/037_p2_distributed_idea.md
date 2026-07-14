**Status:** accepted-roadmap (graduates to development/specs/ via plan 030).

# P2 — Distributed execution (outline)
**After:** S14 · **Architecture:** §6
Steps to be specced: (a) `comm/decomposition.py` — partitioner registry (METIS + icon4py's decomposition structures as donor), local IconGrid construction with halo rows, `DecompositionInfo`; (b) GHEX substrate — per-location pattern cache, bulk `HaloExchange` component, GPU-aware-MPI probe + pinned-host fallback; (c) halo validator pass — `halo` metadata walk shared with `plan/bind.py`, auto/manual modes, the negative-test suite (gap, redundancy, dirty-input) is the heart of the step; (d) distributed JW — np=4 vs np=1 bitwise-or-tolerance study, restart under decomposition; (e) I/O ranks — async gather/forward monitors, Zarr region writes. Reference donors: icon4py decomposition + GHEX Python bindings + ICON ch. 8 semantics. Exit: L6 invariants under MPI at np=4 in CI.
