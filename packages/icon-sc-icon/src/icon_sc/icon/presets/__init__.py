"""Validated ICON composition presets (architecture §4.2/§5.1; S09+).

A preset is a *builder*: it assembles components, coupling operators and the
tendency-bus wiring into one composition object plus a matching initial state,
so run scripts stay legible and diff-clean against the preset (S14 adds the
plan-hash regression enforcing that). S09 ships the single-column (SCM) preset;
the full NWP preset arrives with the dycore lane.
"""

from symcon.icon.presets.jw import (
    JWConfig,
    JWModel,
    build_jw,
)
from symcon.icon.presets.scm import (
    SCM_FAST_ORDER,
    SCMComposition,
    SCMConfig,
    build_scm,
)

__all__ = [
    "SCM_FAST_ORDER",
    "JWConfig",
    "JWModel",
    "SCMComposition",
    "SCMConfig",
    "build_jw",
    "build_scm",
]
