import argparse

from pathlib import Path
from subprocess import run

from pdm import termui
from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project


class SetupCommitSigningCommand(BaseCommand):
    """Setup commit signing."""

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        """Execute the setup commit signing command."""
        run(Path(__file__).parent.resolve()/"setup-commit-signing.sh")  # noqa: S603


def setup_commit_signing(core: Core) -> None:
    """Register the commit signing command as a pdm command."""
    core.register_command(SetupCommitSigningCommand, "setup-commit-signing")
