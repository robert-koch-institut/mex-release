import argparse
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pdm import termui
from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project
from pdm.project.project_file import PyProject

CHANGELOG_TEMPLATE = """
## [Unreleased]

### Added

### Changes

### Deprecated

### Removed

### Fixed

### Security

## [{version}] - {date}
"""


class ReleaseCommand(BaseCommand):
    """Set project version to the given version."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Manipulate the argument parser to add more arguments."""
        parser.add_argument(
            "bump",
            choices=("major", "minor", "patch"),
            default="patch",
            help="part of the project version to update",
        )

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        """Execute the release command."""
        releaser = Releaser(project.pyproject, options.bump)
        releaser.release()


class Releaser:
    """Wrap the release functionality in a single object."""

    def __init__(self, pyproject: PyProject, bump: str) -> None:
        """Create a new releaser instance."""
        self.bump = bump
        self.pyproject = pyproject

    def run(self, *args: str) -> str:
        """Run a command as subproccess, first print it, later print the output."""
        self.pyproject.ui.echo(" ".join(args))
        # use noqa because we check user input (bump) and all other args are hard
        # coded
        stdout = subprocess.check_output(args).decode("utf-8")  # noqa: S603
        self.pyproject.ui.echo(
            stdout,
            verbosity=termui.Verbosity.NORMAL,
        )
        return stdout.strip()

    def check_working_tree(self) -> None:
        """Only continue if working tree is empty."""
        if self.run("git", "status", "--short"):
            msg = "Working tree is dirty. Can only release clean working tree."
            raise RuntimeError(msg)

    def check_default_branch(self) -> None:
        """Only continue if default branch is checked out."""
        git_branch = self.run("git", "rev-parse", "--abbrev-ref", "HEAD")
        git_origin_branches = self.run("git", "remote", "show", "origin")
        git_default_branch = re.findall(
            r"HEAD branch: (\S+)", str(git_origin_branches)
        )[0]
        if git_branch != git_default_branch:
            msg = "Not on default branch. Can only release on default branch."
            raise RuntimeError(msg)

    def check_version_string(self) -> None:
        """Validate the version string to format `0.3.14`."""
        if not re.match(
            r"\d{1,4}\.\d{1,4}\.\d{1,4}", str(self.pyproject.metadata["version"])
        ):
            msg = "Current version string does not match expected format."
            raise RuntimeError(msg)

    def release(self) -> None:
        """Execute the release command."""
        self.check_working_tree()
        self.check_default_branch()
        self.check_version_string()

        # update project version in toml
        major, minor, patch = str(self.pyproject.metadata["version"]).split(".")
        if self.bump == "major":
            new_version = f"{int(major) + 1}.0.0"
        elif self.bump == "minor":
            new_version = f"{major}.{int(minor) + 1}.0"
        elif self.bump == "patch":
            new_version = f"{major}.{minor}.{int(patch) + 1}"
        else:
            msg = "Unexpected bump value."
            raise ValueError(msg)
        self.pyproject.metadata["version"] = new_version
        self.pyproject.write()

        # rollover changelog sections
        changelog_path = Path("CHANGELOG.md")
        with changelog_path.open() as fh:
            changelog = fh.read()
        # remove empty subsections
        changelog = re.sub(r"^### [A-Za-z]+\s+(?=#)", "", changelog, flags=re.MULTILINE)
        # add a new unreleased section
        changelog = changelog.replace(
            "\n## [Unreleased]\n",
            CHANGELOG_TEMPLATE.format(
                version=new_version, date=datetime.now(tz=UTC).date()
            ),
        )
        with changelog_path.open("w") as fh:
            fh.write(changelog)
        self.pyproject.ui.echo(
            "Changes are written to [success]CHANGELOG.md[/].",
            verbosity=termui.Verbosity.NORMAL,
        )

        # commit, tag and push
        self.run(
            "git",
            "commit",
            "-m",
            f"bump version to {new_version}",
            "CHANGELOG.md",
            "pyproject.toml",
        )
        self.run("git", "tag", f"{new_version}")
        self.run("git", "push")
        self.run("git", "push", "--tags")


def release(core: Core) -> None:
    """Register the release command as a pdm command."""
    core.register_command(ReleaseCommand, "release")
