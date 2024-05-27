Plugin for pdm package manager.

- bump version number in `pyproject.toml`
- CHANGELOG rollover, format according to https://keepachangelog.com/en/1.1.0/
- commit, tag, push

Install: `pip install git+https://github.com/rababerladuseladim/mex-release.git`

Execute: `pdm release VERSION` where VERSION matches the regular expression: `\d{1,4}\.\d{1,4}\.\d{1,4}`.
