**Status:** accepted-roadmap (graduates to development/specs/ via plan 030).

# P4 — Ingestion & real-data validation (outline)
**After:** P2+P3 · **Architecture:** §7, ladder L5
Steps: ExtPar reader → registry-driven GRIB2 ingestion (eccodes; names table gains its GRIB2 column in anger) → `from_dwd_analysis`/`from_ifs_analysis` prognostic-set construction + IAU component → global R2B4 forecast example → L5 probtest-style ensemble-band comparison vs ICON (reference ensemble generation tooling is its own step; perturbed-IC methodology per §9.5). Data governance step: pooch manifests, licensing notes for DWD open data.
