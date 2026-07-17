"""ICON-sc example 01 — a single-column model (SCM), the architecture-§5.1 shape.

One legible script (the sympl-paper promise): which schemes, what order, what
cadences, where output happens — all on one screen. The composition is the S09
validated preset (``icon_sc.icon.presets.scm``): ICON's fast-physics subset
satad → graupel microphysics → satad coupled by sequential-update splitting
(tutorial §3.7.2), plus a ``CallingFrequency``-wrapped prescribed cooling
publishing a piecewise-constant tendency to the ``icon:ddt_temperature_slow``
bus slot, consumed by a trivial dycore stand-in.

Run (CI smoke: < 60 s CPU on the embedded debug backend)::

    uv run python examples/01_scm_column.py --hours 1 --output scm_column.nc
"""

from __future__ import annotations

import argparse
import warnings
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np

from icon_sc.core import NetCDFMonitor, timeloop
from icon_sc.icon.presets import SCMConfig, build_scm

#: What the monitor writes: prognostics the suite steps, the grid-scale surface
#: precipitation rates it diagnoses, and the slow-tendency bus slot.
OUTPUT_SET: tuple[str, ...] = (
    "air_temperature",
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
    "icon:ddt_temperature_slow",
)


def build_model() -> Any:
    """The example's model: exactly the S09 preset builder, default config.

    Exposed as a function so the S14 plan-hash drift test can bind the
    composition this script runs and assert it hashes identically to the
    preset builder's (the layout-doc drift test — SPEC S14 acceptance 3).
    """
    return build_scm(SCMConfig())  # embedded backend: no compile step


def main(output: str | Path = "scm_column.nc", hours: float = 1.0) -> dict[str, Any]:
    """Build the SCM preset, run it for ``hours``, write NetCDF; return the final state."""
    composition, state, cfg = build_model()
    monitor = NetCDFMonitor(output, variables=OUTPUT_SET)

    with warnings.catch_warnings():
        # icon4py's embedded execution warns about Python-level execution; their
        # own integration tests run with the same warnings suppressed.
        warnings.simplefilter("ignore")
        final = timeloop(
            state,
            composition.step,
            timestep=cfg.dtime,
            until=timedelta(hours=hours),
            monitors=[monitor],
        )

    rain = float(np.max(final["icon:rain_gsp_rate"].data))
    t_sfc = float(final["air_temperature"].data[0, -1])
    print(f"SCM run complete: {hours} h at dt={cfg.dtime.total_seconds():.0f} s")
    print(f"  surface temperature      : {t_sfc:9.3f} K")
    print(f"  max surface rain rate    : {rain:9.3e} kg m-2 s-1")
    print(f"  output                   : {monitor.path}")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="scm_column.nc", help="NetCDF output file")
    parser.add_argument("--hours", type=float, default=1.0, help="simulated hours")
    args = parser.parse_args()
    main(output=args.output, hours=args.hours)
