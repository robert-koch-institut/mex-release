import json
from io import BytesIO
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from typer import Context
from typer.testing import CliRunner

from mex.release.emoji import _get_shortcodes, app

runner = CliRunner()

FAKE_EMOJI_DATA = [
    {"hexcode": "1F600", "label": "grinning face", "group": 0},
    {"hexcode": "1F955", "label": "carrot", "group": 4},
    {"hexcode": "1FADC", "label": "root vegetable", "group": 4},
    {"hexcode": "1F3FB", "label": "light skin tone", "group": 2},
    {"hexcode": "1F1E9-1F1EA", "label": "flag: Germany", "group": 9},
    {"hexcode": "1F1E6", "label": "regional indicator A"},
]
FAKE_SHORTCODE_DATA = {
    "1F600": ["grinning", "grinning_face"],
    "1F955": "carrot",
    "1F3FB": "skin-tone-2",
    "1F1E9-1F1EA": "flag-de",
    "1F1E6": "regional_indicator_a",
}


def fake_urlopen() -> MagicMock:
    return MagicMock(
        side_effect=lambda url: BytesIO(
            json.dumps(
                FAKE_SHORTCODE_DATA if "shortcodes" in url else FAKE_EMOJI_DATA
            ).encode()
        )
    )


@pytest.mark.parametrize(
    ("version", "expected_emoji"),
    [
        ("2.4.2", ":grinning:"),
        ("2.4.3", ":root_vegetable:"),
        ("2.4.4", ":carrot:"),
    ],
)
def test_get_emoji(context: Context, version: str, expected_emoji: str) -> None:
    root = cast("Path", context.obj["root"])
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "test-project"\nversion = "{version}"\n',
        encoding="utf-8",
    )

    with patch("mex.release.emoji.urllib.request.urlopen", fake_urlopen()):
        result = runner.invoke(app, [], obj=context.obj)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_emoji


def test_get_shortcodes_skips_control_flag_and_indicator_groups() -> None:
    with patch("mex.release.emoji.urllib.request.urlopen", fake_urlopen()):
        shortcodes = _get_shortcodes()

    assert shortcodes == ["carrot", "grinning", "root_vegetable"]
