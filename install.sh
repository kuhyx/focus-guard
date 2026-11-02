#!/bin/bash
# Install focus-guard for real use, as kuhy (never sudo). Idempotent.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_DIR
readonly SYSTEM_PYTHON="/usr/bin/python3"
readonly UNIT_DIR="${HOME}/.config/systemd/user"
readonly UTILS_ROOT="${UTILS_ROOT:-$HOME/src/utils}"
readonly UNITS=(focus-guard.service focus-guard.timer)

log() { printf 'install: %s\n' "$1" >&2; }
fail() { printf 'install: FAILED -- %s\n' "$1" >&2; exit 1; }

install_packages() {
    [[ -d "${UTILS_ROOT}/focus_project" ]] || fail "${UTILS_ROOT}/focus_project missing"
    log "installing into the system python's user site-packages"
    "$SYSTEM_PYTHON" -m pip install --user --break-system-packages -q -e "${UTILS_ROOT}/focus_project" \
        || fail "pip install focus_project"
    "$SYSTEM_PYTHON" -m pip install --user --break-system-packages -q -e "$REPO_DIR" \
        || fail "pip install focus-guard"
}

verify_runtime() {
    "$SYSTEM_PYTHON" -c "import focus_guard, focus_project, gatelock, freedays, sickdays; print('imports OK')" \
        || fail "a runtime dependency is missing from the system python"
    (cd / && "$SYSTEM_PYTHON" -m focus_guard status) || fail "status exited non-zero"
}

install_units() {
    log "installing systemd user units into $UNIT_DIR"
    mkdir -p "$UNIT_DIR"
    local unit
    for unit in "${UNITS[@]}"; do
        install -m 644 "${REPO_DIR}/${unit}" "$UNIT_DIR/"
    done
    systemctl --user daemon-reload
    systemctl --user enable --now focus-guard.timer
    systemctl --user enable focus-guard.service
}

main() {
    install_packages
    verify_runtime
    install_units
    log "done -- verdict: python3 -m focus_guard status"
}

main "$@"
