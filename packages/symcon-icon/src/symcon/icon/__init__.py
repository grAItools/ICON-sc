"""symcon.icon — the ICON model as a client of symcon.core.

S06 ships the column foundation: the vertical grid (:mod:`symcon.icon.grid`), the
ICON thermodynamic relations (:mod:`symcon.icon.thermo`, constants in
:mod:`symcon.icon._constants`), the variable-registry seed (:mod:`symcon.icon.names`)
and column-state builders (:mod:`symcon.icon.testing`). ICON components, presets and
ingestion arrive in S07+. May import ``symcon.core`` and icon4py; ``symcon.core``
must never import this.
"""

__version__ = "0.1.0"
