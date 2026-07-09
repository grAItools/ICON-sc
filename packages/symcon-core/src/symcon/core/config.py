"""Configuration base and provenance stamping (architecture §5.3).

Typed, layered, Pythonic: components declare frozen dataclasses subclassing
:class:`Config`; validation happens at construction via the :meth:`Config.validate`
hook (ranges, cross-field constraints). :func:`provenance_stamp` produces the
reproducibility record (config content hash + package versions + timestamp) that
monitors stamp into every output artifact.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import sys
from typing import Any, TypeVar

__all__ = ["Config", "provenance_stamp"]

_C = TypeVar("_C", bound="Config")

#: Packages whose versions are stamped (extended per artifact by callers).
_STAMPED_PACKAGES: tuple[str, ...] = ("symcon-core", "numpy", "xarray", "pint", "cftime")


@dataclasses.dataclass(frozen=True)
class Config:
    """Frozen-dataclass config base: subclass with ``@dataclass(frozen=True)``.

    ``__post_init__`` invokes :meth:`validate`, so invalid configurations cannot be
    constructed. Per-field ``metadata={"icon_namelist_origin": ...}`` documents the
    ICON namelist variable an option corresponds to (§5.3).
    """

    def __post_init__(self) -> None:
        if not (dataclasses.is_dataclass(type(self)) and type(self).__dataclass_params__.frozen):  # type: ignore[attr-defined]
            raise TypeError(
                f"{type(self).__name__} must be decorated with @dataclass(frozen=True)."
            )
        self.validate()

    def validate(self) -> None:
        """Override to enforce ranges and cross-field constraints; raise ValueError."""

    def replace(self: _C, **changes: Any) -> _C:
        """A modified copy (re-validated on construction)."""
        return dataclasses.replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        """Nested plain-dict form (stable field order)."""
        return dataclasses.asdict(self)


def _package_versions() -> dict[str, str]:
    from importlib import metadata

    versions: dict[str, str] = {}
    for package in _STAMPED_PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "<not installed>"
    return versions


def provenance_stamp(config: Config | None = None, **extra: str) -> dict[str, Any]:
    """Provenance record for an output artifact (§5.3).

    Keys: ``created_at`` (UTC ISO), ``python``, ``packages`` (name → version),
    ``config`` (nested dict) + ``config_sha256`` when a config is given, plus any
    ``extra`` key/values the caller stamps (grid UUIDs, git SHAs, experiment ids).
    """
    stamp: dict[str, Any] = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "packages": _package_versions(),
    }
    if config is not None:
        config_dict = config.to_dict()
        payload = json.dumps(config_dict, sort_keys=True, default=str).encode()
        stamp["config"] = config_dict
        stamp["config_class"] = type(config).__name__
        stamp["config_sha256"] = hashlib.sha256(payload).hexdigest()
    stamp.update(extra)
    return stamp
