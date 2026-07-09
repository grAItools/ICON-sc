"""Import-boundary contracts (SPEC S01 acceptance 2).

Two directions:
- the real ``.importlinter`` config passes on the installed packages, and
- a synthetic ``core -> icon`` violation is *detected* by the same contract type,
  proving the tripwire actually trips (negative test via import-linter's API).
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
from importlinter import configuration
from importlinter.application.use_cases import lint_imports

configuration.configure()  # wire the app registry, as import-linter's CLI does

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_real_contracts_pass() -> None:
    assert lint_imports(config_filename=str(REPO_ROOT / ".importlinter")) is True


@pytest.fixture
def violating_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A package mimicking the symcon layout where core deliberately imports icon."""
    root = tmp_path / "src" / "fakesym"
    for sub in ("core", "icon"):
        (root / sub).mkdir(parents=True)
        (root / sub / "__init__.py").touch()
    (root / "__init__.py").touch()
    (root / "core" / "__init__.py").write_text("import fakesym.icon\n")

    config = tmp_path / ".importlinter"
    config.write_text(
        textwrap.dedent(
            """\
            [importlinter]
            root_packages =
                fakesym

            [importlinter:contract:core-independence]
            name = fakesym.core must not import fakesym.icon
            type = forbidden
            source_modules =
                fakesym.core
            forbidden_modules =
                fakesym.icon
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    return config


def test_forbidden_contract_detects_core_to_icon_import(
    violating_tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    passed = lint_imports(config_filename=str(violating_tree), cache_dir=str(tmp_path / ".cache"))
    assert passed is False
    assert "fakesym.core -> fakesym.icon" in capsys.readouterr().out


def test_symcon_packages_importable_without_each_other() -> None:
    # core must be importable with icon/bridges absent (acceptance 3 in miniature):
    # its module graph may not even reference them.
    #
    # The original module objects are restored afterwards: leaving freshly
    # re-imported symcon modules in sys.modules gives later tests *duplicate
    # class identities* (isinstance checks across old/new classes fail — the
    # S05 plan compiler's scheme dispatch tripped over exactly this).
    saved = {name: sys.modules[name] for name in list(sys.modules) if name.startswith("symcon")}
    for name in saved:
        sys.modules.pop(name)
    try:
        import symcon.core  # noqa: F401

        assert not any(m.startswith(("symcon.icon", "symcon.bridges")) for m in sys.modules)
    finally:
        for name in [m for m in sys.modules if m.startswith("symcon")]:
            sys.modules.pop(name)
        sys.modules.update(saved)
