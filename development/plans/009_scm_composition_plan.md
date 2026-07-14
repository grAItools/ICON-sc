# S09 — Plan
1. Compose from existing pieces only — this step should add ≈ zero numerics. `PrescribedCooling` is analytic (Newtonian relaxation profile per tutorial-style idealized forcing).
2. Preset builder returns `(composition, state, cfg)`; the example script must stay diff-clean against the builder (assert equal composition structure in a test — the plan-hash version of this arrives in S10/S14).
3. Choose the initial column from S06 builders (conditionally unstable moist profile); document provenance.
4. Wire CI smoke job for examples.
**Pitfalls:** the second satad's inputs are the graupel outputs — verify the SUS chaining actually feeds updated buffers (a deliberate bug here still "runs"); pick dt/dt_slow so the cadence phase logic is exercised (non-divisor start offset).
