import typer

app = typer.Typer()
from mex.release.release import app as release_app

app = typer.Typer()

app.add_typer(release_app, name="release")

if __name__ == "__main__":
    app()
