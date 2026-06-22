# Chejooli Core

Python scheduling package and CLI. Read `README.md` for CLI usage and `API.md` for backend integration.

Release versions follow git tags (`5.1`, `5.2`, ...). Keep `pyproject.toml` `version` aligned with the tag you publish to `repo.hsre.ir` (`hpypi`).

Publish a release:

```bash
./release.sh <version> <artifactory-username> <artifactory-token>
```

Then commit the version bump, create the matching git tag, and push `main` plus the tag.
