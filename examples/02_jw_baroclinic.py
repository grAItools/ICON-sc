"""symcon example 02 — the Jablonowski-Williamson baroclinic wave (dry, S13).

The architecture-§5.1 loop shape for the dry dynamical slice: the icon4py
nonhydrostatic solver hosted as a symcon ``DynamicalCore`` (S12) followed by the
horizontal-diffusion ``Stepper`` (S13), no physics — the slow-tendency bus slots
default to zero inside the dycore. Grid/static/config come from the pinned icon4py
JW datatest experiment (global R02B04, 35 levels, Δt = 300 s, 5 dynamics substeps);
the initial state is the JW analytic baroclinic-wave state (perturbation 1 m/s).

Run (CI smoke: 6 h; the baroclinic wave needs ~9 days)::

    uv run python examples/02_jw_baroclinic.py --hours 6 --output jw_baroclinic.nc

Requires the ``symcon-icon[datatest]`` extra (the JW archive, ~14 GB unpacked,
downloads once into ``~/.cache/symcon/icon4py-testdata``).
"""

from __future__ import annotations

import argparse
import os
import pathlib
import warnings
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any

# The persistent gtfn program cache (the pytest plugin sets the same defaults):
# without it, gt4py recompiles the ~70 dycore+diffusion programs on every run.
os.environ.setdefault("GT4PY_BUILD_CACHE_LIFETIME", "persistent")
os.environ.setdefault(
    "GT4PY_BUILD_CACHE_DIR", str(pathlib.Path.home() / ".cache" / "symcon" / "gt4py")
)

import numpy as np

from symcon.core import Monitor, NetCDFMonitor, timeloop
from symcon.core.state import canonical_units, make_dataarray

#: What the monitor writes: the prognostics the composed model steps, plus the
#: diagnosed surface pressure (the JW verification field).
OUTPUT_SET: tuple[str, ...] = (
    "icon:normal_wind",
    "upward_air_velocity_on_interface_levels",
    "air_density",
    "icon:exner_function",
    "icon:virtual_potential_temperature",
    "air_pressure_at_ground_level",
)


class EveryNSteps(Monitor):
    """Store every ``n``-th state (the NetCDF monitor rewrites its file per store)."""

    def __init__(self, inner: Monitor, n: int) -> None:
        super().__init__(name=f"every{n}({inner.name})")
        self._inner = inner
        self._n = max(1, n)
        self._count = 0

    def store(self, state: Mapping[str, Any]) -> None:
        self._count += 1
        if self._count % self._n == 0:
            self._inner.store(state)


def main(
    output: str | Path = "jw_baroclinic.nc",
    hours: float = 6.0,
    perturbation: float = 1.0,
    backend: str = "gtfn_cpu",
    store_every_hours: float = 6.0,
) -> dict[str, Any]:
    """Build the JW dry model, run it for ``hours``, write NetCDF; return the state."""
    from symcon.icon.presets import JWConfig, build_jw

    model = build_jw(JWConfig(perturbation_amplitude=perturbation, backend=backend))

    def with_surface_pressure(state: dict[str, Any]) -> dict[str, Any]:
        state["air_pressure_at_ground_level"] = make_dataarray(
            model.checkpoint(state)["surface_pressure"],
            name="air_pressure_at_ground_level",
            dims=("cell",),
            units=canonical_units("air_pressure_at_ground_level"),
            location="cell",
        )
        return state

    def step(state: Mapping[str, Any], dt: timedelta) -> dict[str, Any]:
        return with_surface_pressure(model.step(state, dt))  # dycore, then diffusion

    monitor = NetCDFMonitor(output, variables=OUTPUT_SET)
    stride = round(store_every_hours * 3600.0 / model.dtime.total_seconds())

    state = with_surface_pressure(dict(model.state))
    monitor.store(state)  # the initial record

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # gt4py performance chatter
        final = timeloop(
            state,
            step,
            timestep=model.dtime,
            until=timedelta(hours=hours),
            monitors=[EveryNSteps(monitor, stride)],
        )

    ps = model.checkpoint(final)["surface_pressure"]
    print(
        f"JW run complete: {hours} h at dt={model.dtime.total_seconds():.0f} s "
        f"(ndyn_substeps={model.provenance['ndyn_substeps']}, up={perturbation} m/s)"
    )
    print(f"  surface pressure min/max : {np.min(ps):12.3f} / {np.max(ps):12.3f} Pa")
    print(f"  vn Linf                  : {float(model.checkpoint(final)['vn_linf']):9.3f} m/s")
    print(f"  output                   : {monitor.path}")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="jw_baroclinic.nc", help="NetCDF output file")
    parser.add_argument("--hours", type=float, default=6.0, help="simulated hours")
    parser.add_argument("--perturbation", type=float, default=1.0, help="jw_up [m/s]")
    parser.add_argument("--backend", default="gtfn_cpu", help="gt4py backend")
    parser.add_argument("--store-every-hours", type=float, default=6.0, help="NetCDF store cadence")
    args = parser.parse_args()
    main(
        output=args.output,
        hours=args.hours,
        perturbation=args.perturbation,
        backend=args.backend,
        store_every_hours=args.store_every_hours,
    )
