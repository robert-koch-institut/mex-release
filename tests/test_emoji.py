import hashlib
import json
from io import BytesIO
from unittest.mock import patch

from typer import Context
from typer.testing import CliRunner

from mex.release.emoji import app

runner = CliRunner()


def test_get_emoji(context: Context) -> None:
    fake_emoji_data = [
        {
            "emoji": [
                {"shortcodes": ["smile", "grin", "wave"]},
                {"shortcodes": ["heart", "star"]},
            ]
        }
    ]
    fake_response = BytesIO(json.dumps(fake_emoji_data).encode())
    shortcodes = sorted(["grin", "heart", "smile", "star", "wave"])
    version_hash = hashlib.sha256(b"test-project@1.2.3")
    expected_emoji = shortcodes[int(version_hash.hexdigest(), 16) % len(shortcodes)]

    with patch("mex.release.emoji.urllib.request.urlopen", return_value=fake_response):
        result = runner.invoke(app, [], obj=context.obj)

    assert result.exit_code == 0
    assert expected_emoji in result.output
