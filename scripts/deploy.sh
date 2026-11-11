#!/bin/bash
# Deploy focus-guard for real: update the live checkout, reinstall, restart the
# unit, then health-check. Idempotent. `--check` runs the health check only.
# Exits non-zero unless every health check passes.

set -euo pipefail

readonly LIVE_DIR="${FOCUS_GUARD_LIVE_DIR:-${HOME}/src/focus-guard}"
readonly SYSTEM_PYTHON="/usr/bin/python3"
readonly UNIT_DIR="${HOME}/.config/systemd/user"
readonly UNITS=(focus-guard.service focus-guard.timer)
readonly SETTLE_SEC=3

log() { printf 'deploy: %s\n' "$1" >&2; }
fail() { printf 'deploy: FAILED -- %s\n' "$1" >&2; exit 1; }

update_checkout() {
    log "pulling $LIVE_DIR"
    git -C "$LIVE_DIR" fetch -q origin || fail "git fetch in $LIVE_DIR"
    git -C "$LIVE_DIR" pull -q --ff-only || fail "git pull --ff-only in $LIVE_DIR (dirty or diverged?)"
}

install_and_restart() {
    "${LIVE_DIR}/install.sh" || fail "install.sh"
    log "restarting focus-guard.service"
    # Exits 0 at once when nothing is owed; keeps the lock window up when it is.
    systemctl --user restart focus-guard.service || fail "restart focus-guard.service"
    sleep "$SETTLE_SEC"
}

health_check() {
    systemctl --user is-active -q focus-guard.timer || fail "focus-guard.timer is not active"
    systemctl --user is-enabled -q focus-guard.timer || fail "focus-guard.timer is not enabled"
    if systemctl --user is-failed -q focus-guard.service; then
        fail "focus-guard.service is in the failed state"
    fi
    local unit
    for unit in "${UNITS[@]}"; do
        cmp -s "${LIVE_DIR}/${unit}" "${UNIT_DIR}/${unit}" || fail "installed $unit differs from $LIVE_DIR"
    done
    local imported
    imported="$(cd / && "$SYSTEM_PYTHON" -c 'import focus_guard, os; print(os.path.dirname(os.path.dirname(os.path.realpath(focus_guard.__file__))))')" \
        || fail "system python cannot import focus_guard"
    [[ "$imported" == "$(realpath "$LIVE_DIR")" ]] || fail "system python imports focus_guard from $imported, not $LIVE_DIR"
    [[ "$(git -C "$LIVE_DIR" rev-parse HEAD)" == "$(git -C "$LIVE_DIR" rev-parse origin/main)" ]] \
        || fail "$LIVE_DIR HEAD is not origin/main"
    (cd / && "$SYSTEM_PYTHON" -m focus_guard status >/dev/null) || fail "focus_guard status exited non-zero"
}

main() {
    if [[ "${1:-}" != "--check" ]]; then
        update_checkout
        install_and_restart
    fi
    health_check
    log "deployed $(git -C "$LIVE_DIR" rev-parse --short HEAD)"
}

main "$@"
