"""S06 acceptance 5: registry seed validates, icon: names collide with nothing,
docs table committed and current."""

from __future__ import annotations

import pathlib
import subprocess
import sys

from icon_sc.core.state import canonical_units, lookup_quantity, units_identical
from icon_sc.icon.names import QUANTITIES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: Names the SPEC pins for the seed (prognostics, tracers, diagnostics, ddt slots).
_SPEC_REQUIRED = {
    "air_density",
    "icon:normal_wind",
    "upward_air_velocity",
    "icon:exner_function",
    "icon:virtual_potential_temperature",
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
    "air_temperature",
    "air_pressure",
    "air_pressure_on_interface_levels",
    "eastward_wind",
    "northward_wind",
    "icon:ddt_temp",
    "icon:ddt_qv",
    "icon:ddt_qc",
    "icon:ddt_qi",
    "icon:ddt_qr",
    "icon:ddt_qs",
    "icon:ddt_qg",
}


def test_spec_required_names_are_seeded() -> None:
    missing = _SPEC_REQUIRED - set(QUANTITIES)
    assert not missing, f"SPEC-required registry names missing from the seed: {missing}"


def test_every_seeded_quantity_passes_registration_validation() -> None:
    """Every row is retrievable from the S02 registry and self-consistent."""
    for name, quantity in QUANTITIES.items():
        registered = lookup_quantity(name)  # raises NamesRegistryError if not seeded
        assert registered == quantity
        # canonical units resolve and parse (verify_noop's identity check accepts them)
        assert units_identical(canonical_units(name), quantity.units)
        # §2.5 namespace split, both ways
        if name.startswith("icon:"):
            assert quantity.cf_name is None
        else:
            assert quantity.cf_name is not None


def test_icon_names_collide_with_nothing() -> None:
    """No icon:-namespaced local part shadows an unprefixed canonical name, no
    duplicate ICON short names within the seed."""
    unprefixed = {n for n in QUANTITIES if not n.startswith("icon:")}
    for name in QUANTITIES:
        if name.startswith("icon:"):
            assert name.removeprefix("icon:") not in unprefixed, name
    short_names = [q.icon_name for q in QUANTITIES.values() if q.icon_name is not None]
    assert len(short_names) == len(set(short_names)), "duplicate ICON short names"


def test_exner_unit_is_one_not_dimensionless() -> None:
    """PLAN pitfall: the unit of Exner is the string "1" — no drift."""
    assert QUANTITIES["icon:exner_function"].units == "1"
    for tracer in ("qv", "qc", "qi", "qr", "qs", "qg"):
        row = next(q for q in QUANTITIES.values() if q.icon_name == tracer)
        assert row.units == "1"


def test_interface_level_variants_resolve_units_via_base() -> None:
    assert canonical_units("upward_air_velocity_on_interface_levels") == "m s-1"
    # explicitly seeded interface rows win over the fallback (own ICON short name)
    assert QUANTITIES["air_pressure_on_interface_levels"].icon_name == "pres_ifc"


def test_docs_table_is_committed_and_current() -> None:
    """PLAN item 4 / acceptance 5: docs/names_registry.md regenerates byte-identical."""
    page = REPO_ROOT / "docs" / "names_registry.md"
    assert page.exists(), "docs/names_registry.md missing — run tools/names_audit.py"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "names_audit.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_registry_size_matches_spec_scale() -> None:
    """SPEC: "the first ~40 entries" — guard against silent shrinkage."""
    assert len(QUANTITIES) >= 35
