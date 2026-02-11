import json
from io import BytesIO
from unittest.mock import patch

from typer import Context
from typer.testing import CliRunner

from mex.release.emoji import app

runner = CliRunner()


def test_get_emoji(context: Context) -> None:
    fake_emoji_data = {
        "emoji": [
            {"shortcodes": [":foo:", ":bar:", ":batz:"]},
            {"shortcodes": [":wave:", ":tide:"]},
        ]
    }
    fake_response = BytesIO(json.dumps([fake_emoji_data]).encode())

    with patch("mex.release.emoji.urllib.request.urlopen", return_value=fake_response):
        result = runner.invoke(app, [], obj=context.obj)

    assert result.exit_code == 0
    assert result.output.strip() == ":tide:"
