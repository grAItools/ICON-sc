# work/ — the work-document lifecycle

One work unit, one four-digit id (allocated in `../REGISTRY.md` §1 at assignment),
one lifecycle: **proposal** (`proposals/`, living until graduated) → **spec**
(`specs/`, frozen contract) → **plan** (`plans/`, frozen instructions) → **report**
(`reports/`, frozen account, written at merge).

Naming (TD-50.1/ADR-0006, TD-51.1–2/ADR-0007): `<kind>-<NNNN>-<kebab-slug>.md`, kind
prefix = singular of the subfolder (`proposal-`, `spec-`, `plan-`, `report-`);
reports are always flat files — artifacts, only when they exist, live in a sibling
folder `report-NNNN-<kebab>/` named like the report file minus `.md`. Related items
share NNNN across subfolders: `spec-0005-vault-plan-t1.md` / `plan-0005-…` /
`report-0005-….md`. The work-id sequence is independent of everything outside `work/`
(ADRs number separately in `../ADRs/`). Branches: `work/NNNN-<kebab>`. Liveness rules:
`../policies/document-kinds.md`; historical names: `../REGISTRY.md` §2/§2b.
