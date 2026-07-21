**Status:** accepted-roadmap (graduates to development/work/specs/ via plan 0030).

# P5 — Execution tiers T2/T3 (outline)
**After:** S14 (+P2 for exchange-delimited segments) · **Architecture:** §8.3
Steps: (a) T2 graph capture — CuPy stream capture per SegmentMarker-delimited region, signature cache, static-shape bind checks, HIP caveat handling; cross-tier CI job T1≡T2; (b) launch-count + step-time benchmarks vs icon4py-standalone (the §8.8 headline target); (c) T3 native driver — emitter + templates + cached build, gtfn entry-point linkage study first (spike step: prove one program callable from C++ before committing), GHEX native calls; explicitly profiling-gated per §8.3. Include the gt4py precompiled-program/static-args verification spike early — it de-risks both T1 depth and T3.
