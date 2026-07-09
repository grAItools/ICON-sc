#!/usr/bin/env python3
"""Generate the variable-registry docs table from the registry seed (S06, PLAN item 4).

Emits ``docs/names_registry.md`` — canonical name ↔ units ↔ CF standard name ↔ ICON
short name ↔ GRIB2 — from :data:`symcon.icon.names.QUANTITIES`. The committed page is
generated output; edit the seed tables (``symcon.core.state.names`` /
``symcon.icon.names``), rerun ``uv run python tools/names_audit.py``, and commit both.
``--check`` exits non-zero when the committed page is stale (used by the S06
acceptance test).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_PAGE = REPO_ROOT / "docs" / "names_registry.md"

_HEADER = """\
# Variable registry

<!-- GENERATED FILE — do not edit. Regenerate with `uv run python tools/names_audit.py`
     after changing the seed tables in symcon.core.state.names / symcon.icon.names. -->

Canonical quantity names (architecture §2.5): CF standard names are canonical and
unprefixed; solver-internal quantities live in the `icon:` namespace. The GRIB2
column exists for table-driven *ingestion* only (§7.2). The `_on_interface_levels`
suffix marks the `height_interface` dim variant of a quantity and inherits its base
quantity's canonical units.

| canonical name | units | CF standard name | ICON | GRIB2 |
|---|---|---|---|---|
"""


def render() -> str:
    from symcon.icon.names import QUANTITIES

    rows = []
    for q in QUANTITIES.values():
        cf = q.cf_name if q.cf_name is not None else "—"
        icon = f"`{q.icon_name}`" if q.icon_name is not None else "—"
        grib2 = "/".join(str(x) for x in q.grib2) if q.grib2 is not None else "—"
        rows.append(f"| `{q.name}` | `{q.units}` | {cf} | {icon} | {grib2} |")
    return _HEADER + "\n".join(rows) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed page is current")
    args = parser.parse_args(argv)
    content = render()
    if args.check:
        committed = DOCS_PAGE.read_text() if DOCS_PAGE.exists() else ""
        if committed != content:
            sys.stderr.write(
                f"{DOCS_PAGE} is stale — rerun `uv run python tools/names_audit.py`.\n"
            )
            return 1
        return 0
    DOCS_PAGE.write_text(content)
    print(f"wrote {DOCS_PAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
