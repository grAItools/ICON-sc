# envs/

Environment specs for targets where MPI/CUDA/eccodes come from the system:
`pixi.toml` for local/laptop dev, `spack/` for HPC sites. Populated when the first
HPC target is exercised; uv workspace + constraints/ cover CI until then.
