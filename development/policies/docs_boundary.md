# docs_boundary — the development/ ↔ docs/ boundary

Scope: what may cross between the published documentation site and the repo-internal
process memory.

1. `docs/` is the published surface (the Sphinx site source). Its only trunk-frozen
   zone is `architecture/`; everything else there is living site source.
2. `development/` is repo-internal process memory: **never a Sphinx source, never
   hyperlinked from `docs/` site pages** (prose mentions without links are fine),
   **never deployed**.
3. Development content wanted user-facing is *rewritten* under `docs/` (tutorials cite
   `development/records/036_implementation_report_record.md` as author-side source material,
   without links) — never included, symlinked, or excerpted mechanically. P7's
   architecture canonicalization owns any future exception.
4. Generated files are committed under `docs/` only with a `GENERATED FILE` header
   naming the regeneration command (`docs/names_registry.md` is the precedent).
