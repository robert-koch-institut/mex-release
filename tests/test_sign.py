import base64
from pathlib import Path
from unittest.mock import patch

from pytest import MonkeyPatch

from mex.release.sign import setup_commit_signing


def test_setup_commit_signing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    private_key_data = b"fake-private-key"
    public_key_data = b"fake-public-key"
    monkeypatch.setenv("MEX_BOT_EMAIL", "bot@test.com")
    monkeypatch.setenv("MEX_BOT_USER", "test-bot")
    monkeypatch.setenv("SIGNING_KEY", base64.b64encode(private_key_data).decode())
    monkeypatch.setenv("SIGNING_PUB", base64.b64encode(public_key_data).decode())
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    with patch("mex.release.sign.run") as mock_run:
        setup_commit_signing()

    ssh_dir = tmp_path / ".ssh"
    assert ssh_dir.exists()
    assert (ssh_dir / "mex").read_bytes() == private_key_data
    assert (ssh_dir / "mex.pub").read_bytes() == public_key_data
    assert mock_run.call_count == 6
