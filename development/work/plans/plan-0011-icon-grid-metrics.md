# S11 — Plan
1. Mine icon4py `common`: grid manager / grid file ingestion, `DecompositionInfo`-adjacent structures, metrics + interpolation field factories, and their datatest savepoints. Strong preference: **delegate** to icon4py's implementations behind ICON-sc interfaces (they are the reference; wrapping minimizes divergence). Write independent code only where their API is driver-entangled — record each such decision.
2. Grid files: obtain via icon4py's datatest download; if a direct grid-file URL is needed, MPI-M's grid file server is the canonical source — lock URLs + checksums into a pooch manifest.
3. Registry extension: static-field names (`icon:ddqz_z_half`, `icon:wgtfac_c`, RBF coefficient names, …) exactly as consumed in S12 — coordinate the list with the S12 SPEC field enumeration.
4. Parity tests structured per factory, parametrized over fields.
**Pitfalls:** 1-based Fortran indices and orientation signs in the grid file; icon4py normalizes — do it the same way and test against them, not against the raw file; keep the reader pure (no gt4py imports) so `core ↛ icon` stays clean and the reader is reusable in P4 tooling.
