import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import tomlkit
import typer

if TYPE_CHECKING:
    from tomlkit.items import Table

app = typer.Typer()

# emojibase is the dataset that element uses to resolve `:shortcode:` aliases, see
# https://github.com/matrix-org/emojibase-bindings/blob/v1.5.0/src/emoji.ts
EMOJIBASE_CDN = "cdn.jsdelivr.net/npm/emojibase-data"
EMOJIBASE_VERSION = "17.0.0"
EMOJI_DATA = "en/compact.json"
SHORTCODE_DATA = "en/shortcodes/iamcal.json"

# emojibase group ids that make for poor release identifiers: skin tones and hair
# styles (which element hides from its picker too) and flags (which carry meaning
# we don't want to imply), emoji without a group are the bare regional indicators
SKIPPED_GROUPS = (None, 2, 9)


def _download(path: str) -> Any:  # noqa: ANN401
    """Fetch and parse an emojibase data file."""
    with urllib.request.urlopen(
        f"https://{EMOJIBASE_CDN}@{EMOJIBASE_VERSION}/{path}"
    ) as response:
        return json.loads(response.read())


def _get_shortcodes() -> list[str]:
    """Collect the canonical shortcode of every emoji that element can resolve."""
    emojis = cast("list[dict[str, Any]]", _download(EMOJI_DATA))
    aliases = cast("dict[str, str | list[str]]", _download(SHORTCODE_DATA))
    shortcodes = set()
    for emoji in emojis:
        if emoji.get("group") in SKIPPED_GROUPS:
            continue
        alias = aliases.get(emoji["hexcode"])
        if alias is None:
            # emojibase has no alias for this emoji, fall back the way element does
            alias = re.sub(r"\W+", "_", str(emoji["label"]).lower(), flags=re.ASCII)
        shortcodes.add(alias if isinstance(alias, str) else alias[0])
    return sorted(shortcodes)


@app.command()
def get_emoji(ctx: typer.Context) -> None:
    """Pick an emoji shortcode for the unique hash of project name and version."""
    shortcodes = _get_shortcodes()

    with Path.open(cast("Path", ctx.obj.get("root")) / "pyproject.toml") as f:
        project_data = tomlkit.load(f)
        project_name = cast("Table", project_data["project"])["name"]
        project_version = cast("Table", project_data["project"])["version"]

    version_hash = hashlib.sha256((f"{project_name}@{project_version}").encode())
    shortcode = shortcodes[int(version_hash.hexdigest(), 16) % len(shortcodes)]
    typer.echo(f":{shortcode}:")
