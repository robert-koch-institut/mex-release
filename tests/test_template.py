import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from mex.release.cli import app
from mex.release.release import CHANGELOG_TEMPLATE
from mex.release.template import (
    add_changelog_entry,
    parse_latest_tag,
    read_template_url,
    release_url,
    render_body,
    write_outputs,
)

runner = CliRunner()

TEMPLATE_URL = "https://github.com/robert-koch-institut/mex-template"
LS_REMOTE = (
    "aaa\trefs/tags/2.2.0^{}\n"
    "bbb\trefs/tags/2.2.0\n"
    "ccc\trefs/tags/2.1.0^{}\n"
    "ddd\trefs/tags/2.1.0\n"
)


def test_read_template_url(tmp_path: Path) -> None:
    (tmp_path / ".cruft.json").write_text(json.dumps({"template": TEMPLATE_URL}))
    assert read_template_url(tmp_path) == TEMPLATE_URL


def test_parse_latest_tag() -> None:
    assert parse_latest_tag(LS_REMOTE) == "2.2.0"
    assert parse_latest_tag("bbb\trefs/tags/1.0.0\n") == "1.0.0"
    with pytest.raises(ValueError, match="no tags"):
        parse_latest_tag("")
    with pytest.raises(ValueError, match="no tags"):
        parse_latest_tag("aaa\trefs/tags/2.2.0^{}\n")


def test_parse_latest_tag_with_real_repo(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(tmp_path), *args],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    git("init", "--quiet")
    git(
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "--allow-empty",
        "-qm",
        "x",
    )
    for tag in ("1.9.0", "1.10.0", "1.2.0"):
        git("-c", "user.name=t", "-c", "user.email=t@t", "tag", "-a", tag, "-m", tag)
    ls_remote = git("ls-remote", "--tags", "--sort=-v:refname", str(tmp_path))
    assert parse_latest_tag(ls_remote) == "1.10.0"


@pytest.mark.parametrize(
    ("template_url", "expected"),
    [
        (TEMPLATE_URL, f"{TEMPLATE_URL}/releases/tag/1.0.0"),
        (f"{TEMPLATE_URL}.git", f"{TEMPLATE_URL}/releases/tag/1.0.0"),
        (f"{TEMPLATE_URL}/", f"{TEMPLATE_URL}/releases/tag/1.0.0"),
        (
            "https://gitlab.example.org/mex/mex-template.git",
            "https://gitlab.example.org/mex/mex-template/-/tags/1.0.0",
        ),
    ],
)
def test_release_url(template_url: str, expected: str) -> None:
    assert release_url(template_url, "1.0.0") == expected


def test_add_changelog_entry_to_empty_section() -> None:
    changelog = f"# Changelog\n{CHANGELOG_TEMPLATE}"
    updated = add_changelog_entry(changelog, "new template X")
    assert "### Changes\n\n- new template X\n\n### Deprecated\n" in updated
    assert updated.count("new template X") == 1


def test_add_changelog_entry_to_existing_bullets() -> None:
    changelog = (
        "## [Unreleased]\n\n### Changes\n\n- existing\n\n### Fixed\n\n"
        "## [1.0.0] - 2026-01-01\n\n### Changes\n\n- old\n"
    )
    assert add_changelog_entry(changelog, "new template X") == (
        "## [Unreleased]\n\n### Changes\n\n- new template X\n- existing\n\n### Fixed\n\n"
        "## [1.0.0] - 2026-01-01\n\n### Changes\n\n- old\n"
    )


def test_add_changelog_entry_without_section() -> None:
    changelog = "# Changelog\n\n### Changesets\n\n- foo\n"
    assert add_changelog_entry(changelog, "new template X") == changelog


def test_render_body() -> None:
    assert render_body("L", {}) == "### Changes\n\n- new template L\n"
    assert render_body("L", {"a.rej": "-x\n+y\n", "b.rej": "-z"}) == (
        "### Changes\n\n- new template L\n"
        "\n### Conflicts\n"
        "\n```diff\n-x\n+y\n```\n"
        "\n```diff\n-z\n```\n"
    )


def test_write_outputs(tmp_path: Path) -> None:
    output = tmp_path / "out.env"
    output.write_text("existing=1\n")
    write_outputs(output, template_tag="2.2.0", has_conflicts="false")
    assert output.read_text() == "existing=1\ntemplate_tag=2.2.0\nhas_conflicts=false\n"


class FakeRun:
    """Record commands and fake the outcome of git and cruft."""

    def __init__(self, root: Path, *, up_to_date: bool, conflicts: bool) -> None:
        self.root = root
        self.up_to_date = up_to_date
        self.conflicts = conflicts
        self.calls: list[tuple[str, ...]] = []

    def __call__(
        self, args: tuple[str, ...], **_: object
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(tuple(args))
        stdout, returncode = "", 0
        if args[:2] == ("git", "ls-remote"):
            stdout = LS_REMOTE
        elif args[:2] == ("cruft", "check"):
            returncode = 0 if self.up_to_date else 1
        elif args[:2] == ("cruft", "update") and self.conflicts:
            (self.root / "src").mkdir()
            (self.root / "src" / "file.py.rej").write_text("-old\n+new\n")
        return subprocess.CompletedProcess(args, returncode, stdout, "")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    (tmp_path / ".cruft.json").write_text(json.dumps({"template": TEMPLATE_URL}))
    (tmp_path / "CHANGELOG.md").write_text(f"# Changelog\n{CHANGELOG_TEMPLATE}")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _invoke(monkeypatch: MonkeyPatch, fake: FakeRun) -> str:
    monkeypatch.setattr("mex.release.template.subprocess.run", fake)
    result = runner.invoke(app, ["update-template", "--output", "out.env"])
    assert result.exit_code == 0, result.output
    return result.output


def test_update_template_up_to_date(project: Path, monkeypatch: MonkeyPatch) -> None:
    fake = FakeRun(project, up_to_date=True, conflicts=False)
    output = _invoke(monkeypatch, fake)

    assert "up to date at 2.2.0" in output
    assert fake.calls == [
        ("git", "ls-remote", "--tags", "--sort=-v:refname", TEMPLATE_URL),
        ("cruft", "check", "--checkout", "2.2.0"),
    ]
    assert not (project / "out.env").exists()
    assert not (project / ".cruft-pr-body").exists()
    assert "2.2.0" not in (project / "CHANGELOG.md").read_text()


def test_update_template(project: Path, monkeypatch: MonkeyPatch) -> None:
    fake = FakeRun(project, up_to_date=False, conflicts=False)
    _invoke(monkeypatch, fake)

    link = f"{TEMPLATE_URL}/releases/tag/2.2.0"
    assert fake.calls[2:] == [
        ("git", "checkout", "main"),
        ("git", "checkout", "-b", "cruft/mex-template-2.2.0"),
        ("cruft", "update", "--checkout", "2.2.0", "--skip-apply-ask"),
        ("git", "add", "--all", "--verbose"),
        ("git", "commit", "--message", "Update mex-template to 2.2.0"),
    ]
    assert (
        f"### Changes\n\n- new template {link}\n\n###"
        in (project / "CHANGELOG.md").read_text()
    )
    assert (project / ".cruft-pr-body").read_text() == (
        f"### Changes\n\n- new template {link}\n"
    )
    assert (project / "out.env").read_text() == (
        "template_tag=2.2.0\nbranch=cruft/mex-template-2.2.0\nhas_conflicts=false\n"
    )


def test_update_template_with_conflicts(
    project: Path, monkeypatch: MonkeyPatch
) -> None:
    fake = FakeRun(project, up_to_date=False, conflicts=True)
    output = _invoke(monkeypatch, fake)

    assert "has conflicts: src/file.py.rej" in output
    assert (
        "### Conflicts\n\n```diff\n-old\n+new\n```\n"
        in (project / ".cruft-pr-body").read_text()
    )
    assert (project / "out.env").read_text().endswith("has_conflicts=true\n")


def test_update_template_without_changelog_prints_outputs(
    project: Path, monkeypatch: MonkeyPatch
) -> None:
    (project / "CHANGELOG.md").unlink()
    monkeypatch.setattr(
        "mex.release.template.subprocess.run",
        FakeRun(project, up_to_date=False, conflicts=False),
    )
    result = runner.invoke(
        app,
        ["update-template", "--base", "develop", "--branch-prefix", "bump-"],
    )
    assert result.exit_code == 0, result.output
    assert "template_tag=2.2.0\nbranch=bump-2.2.0\nhas_conflicts=false\n" in (
        result.stdout
    )
    assert not (project / "CHANGELOG.md").exists()
