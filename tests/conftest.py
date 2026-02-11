from pathlib import Path

import pytest
from click import Command
from pytest import MonkeyPatch
from typer import Context

from mex.release.release import CHANGELOG_TEMPLATE


@pytest.fixture
def context(monkeypatch: MonkeyPatch, tmp_path: Path) -> Context:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-project"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(f"# Changelog\n\n{CHANGELOG_TEMPLATE}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return Context(Command("test"), obj={"root": tmp_path})
