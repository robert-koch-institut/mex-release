import argparse
import base64
import os
from pathlib import Path
from subprocess import run

from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project


class SetupCommitSigningCommand(BaseCommand):
    """Setup commit signing."""

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        """Execute the setup commit signing command."""
        ssh_path = Path.home() / ".ssh"
        private_key = ssh_path / "mex"
        public_key = ssh_path / "mex.pub"
        print(run(["ls", "-lah", Path.home()]))
        ssh_path.mkdir(mode=700, exist_ok=True)
        print(run(["ls", "-lah", Path.home()]))
        with private_key.open("wb") as fh:
            fh.write(base64.b64decode(os.environ["SIGNING_KEY"]))
        with public_key.open("wb") as fh:
            fh.write(base64.b64decode(os.environ["SIGNING_PUB"]))
        private_key.chmod(600)
        public_key.chmod(600)
        run(["ssh-add", private_key])
        run(["git", "config", "--local", "user.email", os.environ["MEX_BOT_EMAIL"]])
        run(["git", "config", "--local", "user.name", os.environ["MEX_BOT_USER"]])
        run(["git", "config", "--local", "gpg.format", "ssh"])
        run(["git", "config", "--local", "user.signingkey", public_key])
        run(["git", "config", "--local", "commit.gpgsign", "true"])


def setup_commit_signing(core: Core) -> None:
    """Register the commit signing command as a pdm command."""
    core.register_command(SetupCommitSigningCommand, "setup-commit-signing")
