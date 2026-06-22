#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./release.sh <version> <artifactory-username> <artifactory-password-or-token>

Example:
  ./release.sh 5.3 sobhan.aghasizadeh "$ARTIFACTORY_TOKEN"

Updates pyproject.toml, builds wheel/sdist, and uploads to hpypi on repo.hsre.ir.
After a successful upload, commit the version bump, tag the release, and push:

  git add pyproject.toml
  git commit -m "chore(core): release <version>"
  git tag -a <version> -m "Release <version>"
  git push origin main
  git push origin <version>
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

VERSION="${1:?version required — run ./release.sh --help}"
USERNAME="${2:?artifactory username required}"
PASSWORD="${3:?artifactory password or token required}"

REPOSITORY_URL="https://repo.hsre.ir/artifactory/api/pypi/hpypi"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT"

python3 - <<PY
import pathlib
import re
import sys

version = sys.argv[1]
path = pathlib.Path("pyproject.toml")
text = path.read_text(encoding="utf-8")
new_text, count = re.subn(
    r'^version = ".*"$',
    f'version = "{version}"',
    text,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit("Could not update version in pyproject.toml")
path.write_text(new_text, encoding="utf-8")
print(f"Set pyproject.toml version to {version}")
PY
"$VERSION"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip build twine

rm -rf dist build src/*.egg-info
.venv/bin/python -m build

TWINE_USERNAME="$USERNAME" \
TWINE_PASSWORD="$PASSWORD" \
TWINE_NON_INTERACTIVE=1 \
  .venv/bin/twine upload \
    --repository-url "$REPOSITORY_URL" \
    dist/*

cat <<EOF

Published chejooli-core==${VERSION} to ${REPOSITORY_URL}

Install from the virtual index:
  pip install chejooli-core==${VERSION} \\
    --index-url https://repo.hsre.ir/artifactory/api/pypi/pypi/simple

Next: commit, tag, and push this release in git.
EOF
