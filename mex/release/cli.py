from pathlib import Path

import typer

from mex.release.emoji import app as emoji_app
from mex.release.release import app as release_app
from mex.release.sign import app as sign_app

app = typer.Typer()


def find_project_root(start_path: Path) -> Path:
    """Looks for pyproject.toml."""
    for path in [start_path, *list(start_path.parents)]:
        if (path / "pyproject.toml").exists():
            return path

    msg = "No pyproject.toml found."
    raise FileNotFoundError(msg)


@app.callback()
def common_setup(ctx: typer.Context) -> None:
    """This Callback runs before each command.

    It looks for the root directory and puts
    it into the context.
    """
    ctx.ensure_object(dict)

    try:
        root = find_project_root(Path.cwd())
        ctx.obj["root"] = root
    except FileNotFoundError as e:
        typer.secho(
            "Error: Cannot find project root (no pyproject.toml)", fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from e


app.add_typer(release_app)
app.add_typer(emoji_app)
app.add_typer(sign_app)


def main() -> None:
    """Entrypoint for cli script."""
    app()
