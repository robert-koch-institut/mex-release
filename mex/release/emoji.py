import argparse
import hashlib
import json
import urllib.request
from subprocess import run

from pdm import termui
from pdm.cli.commands.base import BaseCommand
from pdm.core import Core
from pdm.project import Project

EMOJI_METADATA = (
    "raw.githubusercontent.com/googlefonts/emoji-metadata/main/emoji_15_0_ordering.json"
)


class GetVersionEmojiCommand(BaseCommand):
    """Pick an emoji shortcode for the unique hash of project name and version."""

    @staticmethod
    def _run(*args: str) -> None:
        """Run command with arguments and exit in case of non-zero return."""
        run(list(args), check=True)  # noqa: S603

    def handle(
        self,
        project: Project,
        options: argparse.Namespace,  # noqa: ARG002
    ) -> None:
        """Execute the emoji getter command."""
        with urllib.request.urlopen(f"https://{EMOJI_METADATA}") as response:
            data = json.loads(response.read())
        shortcodes = sorted(
            shortcode
            for group in data
            for emoji in group.get("emoji", [])
            for shortcode in emoji.get("shortcodes", [])
        )
        version_hash = hashlib.sha256(
            (
                f"{project.pyproject.metadata['name']}@"
                f"{project.pyproject.metadata['version']}"
            ).encode()
        )
        emoji = shortcodes[int(version_hash.hexdigest(), 16) % len(shortcodes)]
        project.pyproject.ui.echo(emoji, verbosity=termui.Verbosity.NORMAL)


def get_version_emoji(core: Core) -> None:
    """Register the emoji getter command as a pdm command."""
    core.register_command(GetVersionEmojiCommand, "get-version-emoji")
