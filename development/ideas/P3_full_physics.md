**Status:** accepted-roadmap (graduates to development/specs/ via task 30).

# P3 — Full NWP physics suite + bridges (outline)
**After:** S09 pattern established; parallelizable per scheme · **Architecture:** §4.3, §11.1–11.2
One step per scheme, all cloned from the S07/S08 pattern (contracts → granule-or-port → L2 vs serialized/SCM references → constraints declarations): turbdiff (implicit vertical solve), TERRA (tiles; expect bridge-first), FLake, sea ice, surface transfer (time-level note!), convection Tiedtke–Bechtold (bridge-first, tendency bus), cloud cover, radiation (pyRTE-RRTMGP native + ecRad bridge as reference — the §11.2 decision lands here), NOGWD, SSO. Plus: `symcon-bridges` build system step (scikit-build-core + CFFI pattern, proven once on ecRad), `NWP_FAST_ORDER` completion with tutorial-§3.7.2 constraints, reduced-grid wrapper with its grid pair. Exit: L3 SCM suite vs ICON column output, multi-day.
