"""Saturation-adjustment scheme constants consumed on the symcon side (S10; §8.6).

One scheme-constants module per scheme (single source of numerical truth for the
imperative kernel *and* the S10 functional core). The imperative kernel is
icon4py's satad granule, whose closures live in ``microphysical_processes.py``
next to ``microphysics_constants.MicrophysicsConstants`` (REFERENCES.lock
``icon4py-satad``/``icon4py-satad-stencils``, v0.2.0; originally ICON
``mo_lookup_tables_constants.f90``): this module transcribes the subset the
satad functional core draws on. The Tetens constants deliberately duplicate the
graupel module's rows — each scheme module stays self-contained per the repo
convention, and ``tests/test_scheme_constants.py`` pins both against a live
icon4py import so they cannot drift apart.
"""

from __future__ import annotations

from typing import Final

from symcon.icon._constants import TMELT

__all__ = [
    "CP_V",
    "TETENS_AW",
    "TETENS_BW",
    "TETENS_DER",
    "TETENS_P0",
    "ZQWMIN",
]

#: p0 in the Tetens formula for saturation water pressure [Pa] — icon4py
#: ``TETENS_P0`` (ICON ``c1es``).
TETENS_P0: Final[float] = 610.78
#: aw in the Tetens water formula — icon4py ``TETENS_AW`` (ICON ``c3les``).
TETENS_AW: Final[float] = 17.269
#: bw in the Tetens water formula [K] — icon4py ``TETENS_BW`` (ICON ``c4les``).
TETENS_BW: Final[float] = 35.86
#: Numerator of dpsat/dT — icon4py ``TETENS_DER = TETENS_AW * (tmelt - TETENS_BW)``
#: (ICON ``c5les``); derivation expression kept operation-for-operation.
TETENS_DER: Final[float] = TETENS_AW * (TMELT - TETENS_BW)
#: Specific heat of water vapor [J/K/kg] in the Kirchhoff latent-heat closure —
#: icon4py ``CP_V`` = 1850.0, a local Landolt-Börnstein literal deliberately
#: distinct from the model constant ``CPV = 1869.46`` (S07 provenance).
CP_V: Final[float] = 1850.0
#: Minimum cloud water after adjustment [kg/kg] — the granule's ``zqwmin`` literal
#: (ICON ``mo_satad.f90`` ``zqwmin = 1e-20``).
ZQWMIN: Final[float] = 1.0e-20
