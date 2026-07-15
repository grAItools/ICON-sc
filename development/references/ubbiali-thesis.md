# ubbiali-thesis

**Source:** https://doi.org/10.3929/ethz-b-000546695 (S. Ubbiali, ETH diss. no. 28022)
**Pinned:** the published dissertation — corpus pin, see
`development/work/reports/report-0000-overview.md` §3; local copy
`development/references/local/phd_thesis_ubbiali.pdf`.
**License:** not recorded

## Role in the project

Coupling scheme definitions (§2.3, eqs 2.8–2.13, implemented verbatim in S04),
expected convergence orders (§2.4, Table 2.1 — the slope contracts of the order
tests), Burgers experiment design (§2.5.2), Tasmania/DynamicalCore design (ch. 3,
Fig. 3.8–3.10: tiers, fast-tendency call pipeline, substep fractions).

## Gotchas

- Table 2.1's second-order clauses rarely hold in practice: measured orders are
  FC ≈ 2 unconditionally, SSUS second-order iff λ=1/2, LFC/PS/STS/SUS effectively 1.
- The STS forcing always uses the step-initial ψⁿ — easy to get wrong when reading
  the recombined stage kernels in tasmania.

## Consultation ledger

`grep -n 'id = "ubbiali-thesis' development/references/lock.toml` — one `[[ref]]` entry per
consultation.
