"""icon_sc.icon — the ICON model as a client of icon_sc.core.

S06 ships the column foundation: the vertical grid (:mod:`icon_sc.icon.grid`), the
ICON thermodynamic relations (:mod:`icon_sc.icon.thermo`, constants in
:mod:`icon_sc.icon._constants`), the variable-registry seed (:mod:`icon_sc.icon.names`)
and column-state builders (:mod:`icon_sc.icon.testing`). ICON components, presets and
ingestion arrive in S07+. May import ``icon_sc.core`` and icon4py; ``icon_sc.core``
must never import this.
"""

__version__ = "0.1.0"
