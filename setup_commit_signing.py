import argparse
import re
from subprocess import run
from datetime import date

from pdm import termui
from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project
from pdm.project.project_file import PyProject


class SetupCommitSigningCommand(BaseCommand):
    """Setup commit signing."""

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        """Execute the setup commit signing command."""
        run("./setup-commit-signing.sh")
        

def setup_commit_signing(core: Core) -> None:
    """Register the commit signing command as a pdm command."""
    core.register_command(SetupCommitSigningCommand, "setup-commit-signing")
