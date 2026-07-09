"""Config base + provenance stamping (SPEC S02, architecture §5.3)."""

from __future__ import annotations

import dataclasses

import pytest

from symcon.core.config import Config, provenance_stamp


@dataclasses.dataclass(frozen=True)
class DiffusionConfig(Config):
    order: int = 4
    coefficient: float = 0.1

    def validate(self) -> None:
        if self.order not in (2, 4):
            raise ValueError(f"order must be 2 or 4, got {self.order}.")


def test_configs_are_frozen() -> None:
    config = DiffusionConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.order = 2  # type: ignore[misc]


def test_validation_runs_at_construction() -> None:
    with pytest.raises(ValueError, match="order"):
        DiffusionConfig(order=3)


def test_replace_revalidates() -> None:
    config = DiffusionConfig()
    assert config.replace(order=2).order == 2
    with pytest.raises(ValueError, match="order"):
        config.replace(order=7)


def test_unfrozen_subclass_rejected() -> None:
    # dataclasses itself refuses at class-definition time; the __post_init__ guard
    # is belt-and-braces for exotic metaclass routes.
    with pytest.raises(TypeError, match="frozen"):

        @dataclasses.dataclass
        class Mutable(Config):
            x: int = 1


def test_provenance_stamp_contents() -> None:
    stamp = provenance_stamp(DiffusionConfig(), grid_uuid="abc-123")
    assert stamp["config"] == {"order": 4, "coefficient": 0.1}
    assert stamp["config_class"] == "DiffusionConfig"
    assert len(stamp["config_sha256"]) == 64
    assert stamp["packages"]["symcon-core"] != "<not installed>"
    assert stamp["packages"]["numpy"]
    assert stamp["grid_uuid"] == "abc-123"
    assert "T" in stamp["created_at"]  # ISO timestamp


def test_provenance_stamp_is_content_keyed() -> None:
    a1 = provenance_stamp(DiffusionConfig())
    a2 = provenance_stamp(DiffusionConfig())
    b = provenance_stamp(DiffusionConfig(order=2))
    assert a1["config_sha256"] == a2["config_sha256"]
    assert a1["config_sha256"] != b["config_sha256"]
