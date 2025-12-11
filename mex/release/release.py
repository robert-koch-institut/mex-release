import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import tomlkit
import typer

if TYPE_CHECKING:
    from tomlkit.items import Table

app = typer.Typer()

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


class Releaser:
    """Wrap the release functionality in a single object."""

    def __init__(self, project_root: Path, bump: str) -> None:
        """Create a new releaser instance."""
        self.bump = bump
        self.root = project_root
        self.pyproject_path = self.root / "pyproject.toml"
        self.changelog_path = self.root / "CHANGELOG.md"

        with Path.open(self.pyproject_path, encoding="utf-8") as f:
            self.pyproject_data = tomlkit.load(f)

    def run(self, *args: str) -> str:
        """Run a command as subproccess, first print it, later print the output."""
        command = " ".join(args)
        typer.secho(f"> {command}", fg=typer.colors.BRIGHT_BLACK)

        try:
            # use noqa because we check user input (bump) and all other args are hard
            # coded
            result = subprocess.run(  # noqa: S603
                args, check=True, capture_output=True, text=True, cwd=self.root
            )
            output = result.stdout.strip()
            if output:
                typer.echo(output)
            return output  # noqa: TRY300
        except subprocess.CalledProcessError as e:
            typer.secho(f"Error running command: {command}", fg=typer.colors.RED)
            typer.secho(e.stderr, fg=typer.colors.RED)
            raise typer.Exit(code=1) from e

    def check_working_tree(self) -> None:
        """Only continue if working tree is empty."""
        if self.run("git", "status", "--short"):
            typer.secho(
                "Working tree is dirty. Can only release clean working tree.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

    def check_default_branch(self) -> None:
        """Only continue if default branch is checked out."""
        git_branch = self.run("git", "rev-parse", "--abbrev-ref", "HEAD")
        git_origin_branches = self.run("git", "remote", "show", "origin")
        git_default_branch = re.findall(
            r"HEAD branch: (\S+)", str(git_origin_branches)
        )[0]
        if git_branch != git_default_branch:
            typer.secho(
                "Not on default branch. Can only release on default branch.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

    def get_current_version(self) -> str:
        """Extract version from pyproject data."""
        return str(cast("Table", self.pyproject_data["project"])["version"])

    def check_version_string(self) -> None:
        """Validate the version string to format `0.3.14`."""
        version = self.get_current_version()
        if not re.match(r"\d{1,4}\.\d{1,4}\.\d{1,4}", version):
            typer.secho(
                "Current version string does not match expected format.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

    def release(self) -> None:
        """Execute the release command."""
        self.check_working_tree()
        self.check_default_branch()
        self.check_version_string()

        current_version = self.get_current_version()
        major, minor, patch = current_version.split(".")

        # update project version in toml
        if self.bump == "major":
            new_version = f"{int(major) + 1}.0.0"
        elif self.bump == "minor":
            new_version = f"{major}.{int(minor) + 1}.0"
        elif self.bump == "patch":
            new_version = f"{major}.{minor}.{int(patch) + 1}"
        else:
            typer.secho("Unexpected bump value.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        typer.secho(
            f"Bumping version: {current_version} -> {new_version}",
            fg=typer.colors.GREEN,
            bold=True,
        )

        cast("Table", self.pyproject_data["project"])["version"] = new_version

        with Path.open(self.pyproject_path, "w", encoding="utf-8") as f:
            tomlkit.dump(self.pyproject_data, f)

        # rollover changelog sections
        with Path.open(self.changelog_path, "r", encoding="utf-8") as fh:
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
        with Path.open(self.changelog_path, "w", encoding="utf-8") as fh:
            fh.write(changelog)

        typer.secho(
            "Changes are written to [success]CHANGELOG.md[/].", fg=typer.colors.GREEN
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

        typer.secho(
            f"Successfully released version {new_version}!",
            fg=typer.colors.GREEN,
            bold=True,
        )


@app.command()
def release(
    ctx: typer.Context,
    bump: Annotated[
        str, typer.Argument(help="Part of the version to update (major, minor, patch)")
    ] = "patch",
) -> None:
    """Release a new version of the project."""
    project_root = ctx.obj.get("root")

    try:
        releaser = Releaser(project_root, bump)
        releaser.release()
    except Exception as e:
        typer.secho("Release failed.", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e
