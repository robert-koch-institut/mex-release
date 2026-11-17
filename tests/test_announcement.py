from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from typer import Context
from typer.testing import CliRunner

from mex.release.announcement import app, collect_features, render_announcement

if TYPE_CHECKING:
    from pytest import MonkeyPatch

runner = CliRunner()

BOT = "RKIMetadataExchange"
HEADER = "## [mex-consent 1.4.0 🎈](https://github.com/robert-koch-institut/mex-consent/releases/tag/1.4.0)"


def notes(*entries: tuple[str, str]) -> str:
    lines = [
        f"* {title} by @{author} in https://github.com/robert-koch-institut/mex-consent/pull/{number}"
        for number, (title, author) in enumerate(entries)
    ]
    return "\n".join(
        [
            "## What's Changed",
            *lines,
            "",
            "",
            "**Full Changelog**: https://github.com/robert-koch-institut/mex-consent/compare/1.3.0...1.4.0",
        ]
    )


def render(*entries: tuple[str, str]) -> str:
    return render_announcement(
        "mex-consent 1.4.0 🎈",
        "https://github.com/robert-koch-institut/mex-consent/releases/tag/1.4.0",
        collect_features(notes(*entries), BOT),
    )


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param(
            [
                (
                    "Update ghcr.io/robert-koch-institut/mex-backend Docker tag to v4.7.0",
                    BOT,
                ),
                ("Update neo4j:2026.10.1-community Docker digest to 7dbd307", BOT),
            ],
            "featuring mex-backend 4.7.0 and neo4j 2026.10.1",
            id="docker tag and digest",
        ),
        pytest.param(
            [
                ("Update Python to >=3.15,<3.16", BOT),
                ("Update dependency mex-model to >=5.2,<5.3", BOT),
                (
                    "Update ghcr.io/robert-koch-institut/mex-backend Docker tag to v4.8.0",
                    BOT,
                ),
                ("hotfix/stricter-security-headers", "cutoffthetop"),
            ],
            "featuring python 3.15, mex-model 5.2, mex-backend 4.8.0 and stricter security headers",
            id="mixed",
        ),
        pytest.param(
            [
                ("Update neo4j Docker tag to v2026.10.0", BOT),
                ("Update neo4j:2026.10.1-community Docker digest to 44ad2a2", BOT),
                ("Update neo4j Docker tag to v2026.10.2", BOT),
                ("Update neo4j Docker tag to v2026.9.0", BOT),
                ("Update valkey Docker digest to 1a2b3c4", BOT),
                ("Update axllent/mailpit Docker tag to v1.33", BOT),
            ],
            "featuring neo4j 2026.10.2 and mailpit 1.33",
            id="highest version wins",
        ),
        pytest.param(
            [
                ("feature/mx-2120-infra-to-integration-tests", "a"),
                ("Feature/mx 2484 datepicker rewrite", "b"),
                ("feature/mx_2284_remove_default_settings", "c"),
                ("Hotfix/pin mex model version to 5.2.1", "d"),
                ("feature/conditional-supersededBy", "e"),
                ("grippeweb v5.2", "f"),
                ("Feature/mex 2315 wikidata locations extractor", "g"),
            ],
            "featuring infra to integration tests, datepicker rewrite, "
            "remove default settings, pin mex model version to 5.2.1, "
            "conditional supersededBy, grippeweb v5.2 and wikidata locations extractor",
            id="human titles",
        ),
        pytest.param(
            [
                ("Update dependency mex-release to v1.6.1", BOT),
                ("Update dependency mex-common to >=3.6,<3.7", BOT),
                ("Update dependency fastapi to >=0.162,<0.163", BOT),
                ("Update dependency uv to v0.13.4 [SECURITY]", BOT),
                ("Update tooling", BOT),
                ("Update python base image", BOT),
                ("Update docker digests", BOT),
                ("Bump cookiecutter template to 2.1.0", BOT),
                ("Update Node.js to v24.11.1", BOT),
                ("Update dependency npm to v11", BOT),
                ("Update docker/dockerfile:1 Docker digest to 4edf897", BOT),
                ("Update python:3.14-slim-trixie Docker digest to 51dafde", BOT),
                ("Update node:24-alpine Docker digest to 1a2b3c4", BOT),
            ],
            "featuring mex-release 1.6.1, mex-common 3.6, node 24.11.1 and npm 11",
            id="bot titles",
        ),
    ],
)
def test_render_announcement(entries: list[tuple[str, str]], expected: str) -> None:
    assert render(*entries) == f"{HEADER}\n\n{expected}"


def test_render_announcement_without_features() -> None:
    assert render(("Lock file maintenance", BOT)) == HEADER


def test_get_announcement(context: Context, monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "robert-koch-institut/test-project")
    with patch("mex.release.announcement.pick_emoji", return_value=("pear", "🍐")):
        result = runner.invoke(
            app,
            ["-"],
            input=notes(("feature/mx-1-shiny", "someone")),
            obj=context.obj,
        )

    assert result.exit_code == 0, result.output
    assert result.output == (
        "## [test-project 1.2.3 🍐](https://github.com/robert-koch-institut/test-project/releases/tag/1.2.3)\n"
        "\n"
        "featuring shiny\n"
    )
