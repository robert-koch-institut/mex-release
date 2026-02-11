from pathlib import Path
from unittest.mock import patch

import pytest
from click import Command
from pytest import CaptureFixture, MonkeyPatch
from typer import Context, Exit

from mex.release.cli import common_setup, find_project_root


def test_find_project_root(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").touch()
    sub_dir = project_dir / "sub" / "dir"
    sub_dir.mkdir(parents=True)

    assert find_project_root(project_dir) == project_dir
    assert find_project_root(sub_dir) == project_dir

    no_project_dir = tmp_path / "empty"
    no_project_dir.mkdir()
    with pytest.raises(FileNotFoundError, match=r"No pyproject\.toml found"):
        find_project_root(no_project_dir)


def test_common_setup(
    tmp_path: Path, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    (tmp_path / "pyproject.toml").touch()
    monkeypatch.chdir(tmp_path)
    ctx = Context(Command("test"))
    ctx.ensure_object(dict)
    common_setup(ctx)
    assert ctx.obj["root"] == tmp_path

    with patch("mex.release.cli.find_project_root", side_effect=FileNotFoundError):
        ctx_fail = Context(Command("test"))
        ctx_fail.ensure_object(dict)
        with pytest.raises(Exit):
            common_setup(ctx_fail)
    assert "Cannot find project root" in capsys.readouterr().out
