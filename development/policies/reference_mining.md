# reference_mining — sources before code, and the provenance ledger

Scope: how external references are mined and recorded; the pinned reference pair.

**Mine references before writing code.** Candidate module paths in plans are hints —
icon4py/gt4py reorganize; discover the real paths, then append an entry to
`development/references/lock.toml` for every source consulted (schema in that file). Scientific
constants and algorithm structure come from references, never from memory or
improvisation.

Every consulted external source (icon4py, gt4py, ICON Fortran, docs) gets an entry
appended to `development/references/lock.toml` (schema in that file's header) **at the moment of
consultation**, with a commit SHA or tag — never at PR time. Pinned pair: icon4py
v0.2.0 (`28d32c45afb4dbea1da6b6e5170202f08b4adb88`) + gt4py 1.1.10; ICON Fortran
icon-2026.04-public (`8597da45…`) via the **gitlab.dkrz.de** mirror
(gitlab.dwd.de does not resolve).

Per-source context (canonical URL, pin, role, gotchas) lives in the reference cards,
`development/references/*.md`; local non-redistributable documents go in
`development/references/local/` (gitignored). When mining icon4py/ICON sources, clone
shallowly into `/tmp` (never into the repo) and record SHAs in `development/references/lock.toml`
immediately, not at the end.
