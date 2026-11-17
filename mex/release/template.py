import json
import re
import subprocess
from pathlib import Path
from typing import Annotated, cast
from urllib.parse import urlparse

import typer

app = typer.Typer()

# the first changes subsection of the changelog, usually the unreleased one
CHANGES = re.compile(r"^### Changes\n\n", flags=re.MULTILINE)


def _run(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a command in the project root, print it and pass through its output."""
    typer.secho(f"> {' '.join(args)}", fg=typer.colors.BRIGHT_BLACK, err=True)
    return subprocess.run(  # noqa: S603
        args, check=check, cwd=root, text=True
    )


def _output(root: Path, *args: str) -> str:
    """Run a command in the project root and return its stripped output."""
    typer.secho(f"> {' '.join(args)}", fg=typer.colors.BRIGHT_BLACK, err=True)
    return subprocess.run(  # noqa: S603
        args, check=True, cwd=root, text=True, capture_output=True
    ).stdout.strip()


def read_template_url(root: Path) -> str:
    """Read the template repository url from the cruft state file."""
    with (root / ".cruft.json").open(encoding="utf-8") as fh:
        return cast("str", json.load(fh)["template"])


def parse_latest_tag(ls_remote: str) -> str:
    """Pick the first tag from version sorted `git ls-remote --tags` output."""
    for line in ls_remote.splitlines():
        _, _, ref = line.partition("\t")
        if ref.startswith("refs/tags/") and not ref.endswith("^{}"):
            return ref.removeprefix("refs/tags/")
    msg = "Template repository has no tags."
    raise ValueError(msg)


def release_url(template_url: str, tag: str) -> str:
    """Link to the release page of a template tag, on github or gitlab."""
    base = template_url.removesuffix("/").removesuffix(".git")
    if urlparse(base).hostname == "github.com":
        return f"{base}/releases/tag/{tag}"
    return f"{base}/-/tags/{tag}"


def add_changelog_entry(changelog: str, entry: str) -> str:
    """Prepend a bullet point to the first changes subsection of the changelog."""
    if not (match := CHANGES.search(changelog)):
        return changelog
    rest = changelog[match.end() :]
    separator = "\n" if rest.startswith("- ") else "\n\n"
    return f"{changelog[: match.end()]}- {entry}{separator}{rest}"


def render_body(link: str, rejects: dict[str, str]) -> str:
    """Render the body of the pull request, including any rejected hunks."""
    body = f"### Changes\n\n- new template {link}\n"
    if rejects:
        body += "\n### Conflicts\n"
    for content in rejects.values():
        body += f"\n```diff\n{content.rstrip()}\n```\n"
    return body


def write_outputs(output: Path | None, **values: str) -> None:
    """Append `key=value` lines, as expected by `$GITHUB_OUTPUT` or gitlab dotenv."""
    lines = "".join(f"{key}={value}\n" for key, value in values.items())
    if output:
        with output.open("a", encoding="utf-8") as fh:
            fh.write(lines)
    else:
        typer.echo(lines, nl=False)


@app.command()
def update_template(
    ctx: typer.Context,
    output: Annotated[
        Path | None,
        typer.Option(
            help="File to append `key=value` outputs to, e.g. `$GITHUB_OUTPUT` "
            "or a gitlab dotenv report. Prints to stdout if omitted.",
        ),
    ] = None,
    body_file: Annotated[
        Path, typer.Option(help="File to write the pull request body to")
    ] = Path(".cruft-pr-body"),
    base: Annotated[str, typer.Option(help="Branch to start the update from")] = "main",
    branch_prefix: Annotated[
        str, typer.Option(help="Prefix for the update branch, followed by the tag")
    ] = "cruft/mex-template-",
) -> None:
    """Update the project to the latest cookiecutter template tag and commit.

    Does nothing if the project is already up to date. Otherwise creates a branch,
    applies the template update with cruft, adds a changelog entry, commits and
    writes `template_tag`, `branch` and `has_conflicts` to the output.
    Pushing and opening a pull request is left to the CI platform.
    """
    root = cast("Path", ctx.obj.get("root"))
    template_url = read_template_url(root)
    tag = parse_latest_tag(
        _output(root, "git", "ls-remote", "--tags", "--sort=-v:refname", template_url)
    )
    if _run(root, "cruft", "check", "--checkout", tag, check=False).returncode == 0:
        typer.secho(
            f"Template is up to date at {tag}.", fg=typer.colors.GREEN, err=True
        )
        return

    branch = f"{branch_prefix}{tag}"
    _run(root, "git", "checkout", base)
    _run(root, "git", "checkout", "-b", branch)
    _run(root, "cruft", "update", "--checkout", tag, "--skip-apply-ask")

    link = release_url(template_url, tag)
    changelog_path = root / "CHANGELOG.md"
    if changelog_path.is_file():
        changelog = changelog_path.read_text(encoding="utf-8")
        changelog_path.write_text(
            add_changelog_entry(changelog, f"new template {link}"), encoding="utf-8"
        )

    rejects = {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.rej"))
        if path.is_file()
    }
    _run(root, "git", "add", "--all", "--verbose")
    _run(root, "git", "commit", "--message", f"Update mex-template to {tag}")

    (root / body_file).write_text(render_body(link, rejects), encoding="utf-8")
    if rejects:
        typer.secho(
            f"Template update has conflicts: {', '.join(rejects)}",
            fg=typer.colors.YELLOW,
            err=True,
        )
    write_outputs(
        output,
        template_tag=tag,
        branch=branch,
        has_conflicts=str(bool(rejects)).lower(),
    )
