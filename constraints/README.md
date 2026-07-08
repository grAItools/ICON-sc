# constraints/ — pinned dependency sets (populated by step S01)

S01 discovers the tested gt4py + icon4py combination and writes `cpu-ci.txt` and
`gpu-cuda12.txt` here (later: `alps-gh200.txt`, `jax-interop.txt`). Packages declare lower
bounds; these files pin exact working sets. Changing a pin is a trunk decision.
