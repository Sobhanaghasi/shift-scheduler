# Chejooli Core

Python scheduling package and CLI. Read `README.md` for CLI usage and `API.md` for backend integration.

Release versions follow git tags (`5.1`, `5.2`, ...). Keep `pyproject.toml` `version` aligned with the tag you publish to `repo.hsre.ir` (`hpypi`).

Publishing is handled by GitLab CI on tag push (see `.gitlab-ci.yml`). Bump `pyproject.toml`, commit, tag, and push `main` plus the tag.
