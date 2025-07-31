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

    @staticmethod
    def _run(*args: str) -> None:
        """Run command with arguments and exit in case of non-zero return."""
        run(list(args), check=True)  # noqa: S603

    def handle(
        self,
        project: Project,  # noqa: ARG002
        options: argparse.Namespace,  # noqa: ARG002
    ) -> None:
        """Execute the setup commit signing command."""
        bot_email = os.environ["MEX_BOT_EMAIL"]
        bot_user = os.environ["MEX_BOT_USER"]
        ssh_path = Path.home() / ".ssh"
        private_key = ssh_path / "mex"
        public_key = ssh_path / "mex.pub"
        ssh_path.mkdir(mode=0o700, exist_ok=True)
        with private_key.open("wb") as fh:
            fh.write(base64.b64decode(os.environ["SIGNING_KEY"]))
        with public_key.open("wb") as fh:
            fh.write(base64.b64decode(os.environ["SIGNING_PUB"]))
        private_key.chmod(0o600)
        public_key.chmod(0o600)
        self._run("ssh-add", str(private_key))
        self._run("git", "config", "--local", "user.email", bot_email)
        self._run("git", "config", "--local", "user.name", bot_user)
        self._run("git", "config", "--local", "gpg.format", "ssh")
        self._run("git", "config", "--local", "user.signingkey", str(public_key))
        self._run("git", "config", "--local", "commit.gpgsign", "true")


def setup_commit_signing(core: Core) -> None:
    """Register the commit signing command as a pdm command."""
    core.register_command(SetupCommitSigningCommand, "setup-commit-signing")
