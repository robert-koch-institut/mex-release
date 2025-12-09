import hashlib
import json
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, cast

import tomlkit
import typer

if TYPE_CHECKING:
    from tomlkit.items import Table

app = typer.Typer()

EMOJI_METADATA = (
    "raw.githubusercontent.com/googlefonts/emoji-metadata/main/emoji_15_0_ordering.json"
)


@app.command()
def get_emoji(ctx: typer.Context) -> None:
    """Pick an emoji shortcode for the unique hash of project name and version."""
    with urllib.request.urlopen(f"https://{EMOJI_METADATA}") as response:
        data = json.loads(response.read())
    shortcodes = sorted(
        shortcode
        for group in data
        for emoji in group.get("emoji", [])
        for shortcode in emoji.get("shortcodes", [])
    )

    with Path.open(cast("Path", ctx.obj.get("root")) / "pyproject.toml") as f:
        project_data = tomlkit.load(f)
        project_name = cast("Table", project_data["project"])["name"]
        project_version = cast("Table", project_data["project"])["version"]

    version_hash = hashlib.sha256((f"{project_name}@{project_version}").encode())
    emoji = shortcodes[int(version_hash.hexdigest(), 16) % len(shortcodes)]
    typer.echo(emoji)
