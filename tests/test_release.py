from unittest.mock import MagicMock, patch

import pytest
from pytest import CaptureFixture
from typer import Context, Exit

from mex.release.release import Releaser, release


def test_releaser_run(context: Context, capsys: CaptureFixture[str]) -> None:
    releaser = Releaser(context.obj["root"], "patch")
    result_with_output = releaser.run("echo", "hello")
    assert result_with_output == "hello"

    result_no_output = releaser.run("true")
    assert result_no_output == ""

    with pytest.raises(Exit):
        releaser.run("false")
    assert "Error running command" in capsys.readouterr().out


def test_releaser_check_working_tree(
    context: Context, capsys: CaptureFixture[str]
) -> None:
    releaser = Releaser(context.obj["root"], "patch")
    releaser.run = MagicMock(return_value="")  # type: ignore[method-assign]
    releaser.check_working_tree()

    releaser.run = MagicMock(return_value="M file.txt")  # type: ignore[method-assign]
    with pytest.raises(Exit):
        releaser.check_working_tree()
    assert "Working tree is dirty" in capsys.readouterr().out


def test_releaser_check_default_branch(
    context: Context, capsys: CaptureFixture[str]
) -> None:
    releaser = Releaser(context.obj["root"], "patch")
    releaser.run = MagicMock(  # type: ignore[method-assign]
        side_effect=["main", "  HEAD branch: main\n"]
    )
    releaser.check_default_branch()

    releaser.run = MagicMock(  # type: ignore[method-assign]
        side_effect=["feature", "  HEAD branch: main\n"]
    )
    with pytest.raises(Exit):
        releaser.check_default_branch()
    assert "Not on default branch" in capsys.readouterr().out


def test_releaser_get_current_version(context: Context) -> None:
    releaser = Releaser(context.obj["root"], "patch")
    assert releaser.get_current_version() == "1.2.3"


def test_releaser_check_version_string(
    context: Context, capsys: CaptureFixture[str]
) -> None:
    releaser = Releaser(context.obj["root"], "patch")
    releaser.check_version_string()

    releaser.pyproject_data["project"]["version"] = "invalid"  # type: ignore[index]
    with pytest.raises(Exit):
        releaser.check_version_string()
    assert "does not match expected format" in capsys.readouterr().out


def test_releaser_release(context: Context, capsys: CaptureFixture[str]) -> None:
    releaser = Releaser(context.obj["root"], "patch")

    def _fake_run(*args: str) -> str:
        calls.append(args)
        return ""

    calls: list[tuple[str, ...]] = []
    releaser.run = MagicMock(side_effect=_fake_run)  # type: ignore[method-assign]
    releaser.check_working_tree = MagicMock()  # type: ignore[method-assign]
    releaser.check_default_branch = MagicMock()  # type: ignore[method-assign]
    releaser.release()

    assert releaser.get_current_version() == "1.2.4"
    changelog = (context.obj["root"] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.2.4]" in changelog
    assert any("git" in c and "commit" in c for c in calls)
    assert any("git" in c and "tag" in c for c in calls)

    # test valid version
    releaser_major = Releaser(context.obj["root"], "major")
    releaser_major.run = MagicMock(return_value="")  # type: ignore[method-assign]
    releaser_major.check_working_tree = MagicMock()  # type: ignore[method-assign]
    releaser_major.check_default_branch = MagicMock()  # type: ignore[method-assign]
    releaser_major.release()
    assert releaser_major.get_current_version() == "2.0.0"

    # test invalid version
    releaser_bad = Releaser(context.obj["root"], "invalid")
    releaser_bad.run = MagicMock(return_value="")  # type: ignore[method-assign]
    releaser_bad.check_working_tree = MagicMock()  # type: ignore[method-assign]
    releaser_bad.check_default_branch = MagicMock()  # type: ignore[method-assign]
    with pytest.raises(Exit):
        releaser_bad.release()
    assert "Unexpected bump value" in capsys.readouterr().out


def test_release(context: Context, capsys: CaptureFixture[str]) -> None:
    with patch.object(Releaser, "release") as mock_release:
        release(context, bump="patch")
        mock_release.assert_called_once()

    with (
        patch.object(Releaser, "release", side_effect=RuntimeError("fail")),
        pytest.raises(Exit),
    ):
        release(context, bump="patch")
    assert "Release failed" in capsys.readouterr().out
