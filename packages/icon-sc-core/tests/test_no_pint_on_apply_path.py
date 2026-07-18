"""Acceptance SPEC S02 §5: no runtime Pint import on the ``IngressPlan.apply`` path.

Two guards: (a) importing icon_sc.core and running build+apply on a canonical state
never imports pint at all (subprocess, clean interpreter); (b) with pint made
unimportable via an import-time monkeypatch, apply still works in-process.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

import numpy as np
import pytest

_SUBPROCESS_PROGRAM = """
import sys

class _PintBlocker:
    def find_module(self, name, path=None):  # pragma: no cover - legacy hook
        return None
    def find_spec(self, name, path=None, target=None):
        if name == "pint" or name.startswith("pint."):
            raise ImportError("pint import attempted on the apply path")
        return None

sys.meta_path.insert(0, _PintBlocker())

import numpy as np
from icon_sc.core import IngressPlan, StateSchema, make_dataarray, parse_properties

spec = parse_properties({"air_temperature": {"dims": ["cell", "height"], "units": "K"}})
state = {
    "air_temperature": make_dataarray(
        np.zeros((3, 4)), name="air_temperature", dims=("cell", "height"),
        units="K", location="cell",
    )
}
plan = IngressPlan.build(spec, StateSchema.from_state(state))
for _ in range(3):
    plan.apply(state)

assert "pint" not in sys.modules, "pint was imported"
print("OK")
"""


def test_import_build_apply_never_touch_pint_in_clean_interpreter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_PROGRAM],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"


def test_apply_with_pint_unimportable(monkeypatch: pytest.MonkeyPatch) -> None:
    from icon_sc.core import IngressPlan, make_dataarray, parse_properties
    from icon_sc.core.state import units

    # Fresh identity caches so no earlier test pre-paid a pint parse for us ...
    units._registry.cache_clear()
    units._parse.cache_clear()
    units.units_identical.cache_clear()

    # ... and an import-time monkeypatch making any pint import an error.
    class _PintBlocker:
        def find_spec(self, name: str, path: object = None, target: object = None) -> None:
            if name == "pint" or name.startswith("pint."):
                raise ImportError("pint import attempted on the apply path")
            return None

    for mod in [m for m in sys.modules if m == "pint" or m.startswith("pint.")]:
        monkeypatch.delitem(sys.modules, mod)
    monkeypatch.setattr(sys, "meta_path", [_PintBlocker(), *sys.meta_path])

    with pytest.raises(ImportError):
        importlib.import_module("pint")  # the blocker is armed

    spec = parse_properties({"air_temperature": {"dims": ["cell", "height"], "units": "K"}})
    state = {
        "air_temperature": make_dataarray(
            np.zeros((3, 4)),
            name="air_temperature",
            dims=("cell", "height"),
            units="K",
            location="cell",
        )
    }
    plan = IngressPlan.build(spec, state)  # identical strings: no pint needed
    buffers = plan.apply(state)
    assert buffers[0] is state["air_temperature"].data
