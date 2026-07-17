"""Idealized-state initializers and (later) real-data ingestion (architecture §7; S13).

:mod:`symcon.icon.ingest.idealized` provides analytic initial states; GRIB2/analysis
ingestion (§7.2/7.3) arrives with its own step.
"""

from symcon.icon.ingest.idealized import (
    JablonowskiWilliamsonConfig,
    jablonowski_williamson,
)

__all__ = ["JablonowskiWilliamsonConfig", "jablonowski_williamson"]
