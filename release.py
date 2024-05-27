import argparse
import re
import subprocess
from datetime import date

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
        parser.add_argument("version", help="new version for the project")

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        """Execute the release command."""
        releaser = Releaser(project.pyproject, options.version)
        releaser.release()


class Releaser:
    """Wrap the release functionality in a single object."""

    def __init__(self, pyproject: PyProject, version: str) -> None:
        """Create a new releaser instance."""
        self.version = version
        self.pyproject = pyproject

    def run(self, *args: str) -> str:
        """Run a command as subproccess, first print it, later print the output."""
        self.pyproject.ui.echo(" ".join(args))
        # use noqa because we check user input (version) and all other args are hard
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
            raise RuntimeError(
                "Working tree is dirty. Can only release clean working tree."
            )

    def check_default_branch(self) -> None:
        """Only continue if default branch is checked out."""
        git_branch = self.run("git", "rev-parse", "--abbrev-ref", "HEAD")
        git_origin_branches = self.run("git", "remote", "show", "origin")
        git_default_branch = re.findall(
            r"HEAD branch: (\S+)", str(git_origin_branches)
        )[0]
        if git_branch != git_default_branch:
            raise RuntimeError(
                "Not on default branch. Can only release on default branch."
            )

    def check_version_string(self) -> None:
        """Validate the version string to format `0.3.14`."""
        if not re.match(r"\d{1,4}\.\d{1,4}\.\d{1,4}", self.version):
            raise RuntimeError("Version string does not match expected format.")

    def release(self) -> None:
        """Execute the release command."""
        self.check_working_tree()
        self.check_default_branch()
        self.check_version_string()

        # update project version in toml
        self.pyproject.metadata["version"] = self.version
        self.pyproject.write()

        # rollover changelog sections
        with open("CHANGELOG.md") as fh:
            changelog = fh.read()
        # remove empty subsections
        changelog = re.sub(r"^### [A-Za-z]+\s+(?=#)", "", changelog, flags=re.MULTILINE)
        # add a new unreleased section
        changelog = changelog.replace(
            "\n## [Unreleased]\n",
            CHANGELOG_TEMPLATE.format(version=self.version, date=date.today()),
        )
        with open("CHANGELOG.md", "w") as fh:
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
            f"bump version to {self.version}",
            "CHANGELOG.md",
            "pyproject.toml",
        )
        self.run("git", "tag", f"{self.version}")
        self.run("git", "push")
        self.run("git", "push", "--tags")


def release(core: Core) -> None:
    """Register the release command as a pdm command."""
    core.register_command(ReleaseCommand, "release")
