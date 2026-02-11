import json
from io import BytesIO
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from typer import Context
from typer.testing import CliRunner

from mex.release.emoji import app

runner = CliRunner()

FAKE_EMOJI_DATA = {
    "emoji": [
        {"shortcodes": [":foo:", ":bar:", ":batz:"]},
        {"shortcodes": [":wave:", ":tide:"]},
    ]
}


@pytest.mark.parametrize(
    ("version", "expected_emoji"),
    [
        ("2.4.2", ":bar:"),
        ("2.4.3", ":foo:"),
    ],
)
def test_get_emoji(context: Context, version: str, expected_emoji: str) -> None:
    root = cast("Path", context.obj["root"])
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "test-project"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    fake_response = BytesIO(json.dumps([FAKE_EMOJI_DATA]).encode())

    with patch("mex.release.emoji.urllib.request.urlopen", return_value=fake_response):
        result = runner.invoke(app, [], obj=context.obj)

    assert result.exit_code == 0
    assert result.output.strip() == expected_emoji
