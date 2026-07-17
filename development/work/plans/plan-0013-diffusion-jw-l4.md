# S13 — Plan
1. Mine icon4py diffusion package + tests (S12 pattern); mine the icon4py **driver** for its JW experiment: initializer, run config, and any regression tolerances — the driver is both the initializer donor and the reference-trajectory generator.
2. Reference trajectory: script under `validation/L4_idealized/make_reference.py` that runs the pinned icon4py driver and stores selected fields (ps, vn norms, 850 hPa vorticity proxy) at checkpoints; checksum + pooch-cache so CI never reruns it.
3. Compose example 02 from S12+this; keep the loop shape identical to the architecture §5.1 skeleton minus physics.
4. Tolerance schedule: extract from icon4py driver tests; if none exist at this grid, derive the envelope from a perturbed-IC pair (two reference runs, perturbation 1e-13) — the probtest idea at minimum viable scale; document in the test.
**Pitfalls:** config congruence between ICON-sc run and reference run (ndyn_substeps, diffusion coefficients, damping) — assert config equality against the reference's stored provenance before comparing trajectories; grid orientation of the JW analytic winds → vn projection uses S11 geometry (edge normals), test on a few edges by hand.
