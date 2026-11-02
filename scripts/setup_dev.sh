#!/bin/bash
# Dev venv for tests and pre-commit.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_DIR
readonly VENV="${REPO_DIR}/.venv"

if [[ ! -x "${VENV}/bin/python" ]]; then
    python3 -m venv "$VENV"
fi
"${VENV}/bin/python" -m pip install --quiet --upgrade pip
"${VENV}/bin/python" -m pip install --quiet -e "${REPO_DIR}[dev]"
"${VENV}/bin/python" -c "import focus_guard, focus_project, pytest, mypy, pylint; print('dev venv OK')"
