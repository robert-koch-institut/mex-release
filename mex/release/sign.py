import base64
import os
from pathlib import Path
from subprocess import run

import typer

app = typer.Typer()


def _run(*args: str) -> None:
    """Run command with arguments and exit in case of non-zero return."""
    run(list(args), check=True)  # noqa: S603


@app.command()
def setup_commit_signing() -> None:
    """Setup commit signing."""
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
    _run("ssh-add", str(private_key))
    _run("git", "config", "--local", "user.email", bot_email)
    _run("git", "config", "--local", "user.name", bot_user)
    _run("git", "config", "--local", "gpg.format", "ssh")
    _run("git", "config", "--local", "user.signingkey", str(public_key))
    _run("git", "config", "--local", "commit.gpgsign", "true")
