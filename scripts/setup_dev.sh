#!/bin/bash
# Dev venv for tests and pre-commit; focus_project comes from a utils checkout.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_DIR
readonly VENV="${REPO_DIR}/.venv"
readonly UTILS_ROOT="${UTILS_ROOT:-$HOME/src/utils}"

if [[ ! -d "${UTILS_ROOT}/focus_project" ]]; then
    echo "setup_dev: ${UTILS_ROOT}/focus_project missing (clone kuhyx/utils)" >&2
    exit 1
fi
if [[ ! -x "${VENV}/bin/python" ]]; then
    python3 -m venv "$VENV"
fi
"${VENV}/bin/python" -m pip install --quiet --upgrade pip
"${VENV}/bin/python" -m pip install --quiet -e "${UTILS_ROOT}/focus_project"
"${VENV}/bin/python" -m pip install --quiet -e "${REPO_DIR}[dev]"
"${VENV}/bin/python" -c "import focus_guard, focus_project, pytest, mypy, pylint; print('dev venv OK')"
