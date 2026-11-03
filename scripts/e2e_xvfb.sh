#!/bin/bash
# E2E on a private Xvfb (never :0): short -> lock appears and lifts on an
# activity event; met -> no lock; hold -> a hold is on, owed but no lock;
# hold-lift -> lock up, hold starts, lock lifts and does not re-arm until it
# ends. Usage: scripts/e2e_xvfb.sh short|met|hold|hold-lift
# Scratch HOME/XDG_RUNTIME_DIR keep real pools and gatelock claims untouched.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_DIR
readonly SCENARIO="${1:?short|met}"
readonly SCRATCH="${E2E_DIR:-$HOME/data/claude-scratch/e2e/focus-guard}"
readonly LIFT_BUDGET_S=5
readonly HOLD_LIFT_BUDGET_S=30
readonly RUN="${SCRATCH}/${SCENARIO}-run"
readonly MINUTES="${RUN}/minutes.json"
readonly HOLD_FLAG="${RUN}/hold.flag"
GATE_PID=""
XVFB_PID=""
DISPLAY_NUM=""

cleanup() {
    [[ -n "$GATE_PID" ]] && kill "$GATE_PID" 2>/dev/null || true
    [[ -n "$XVFB_PID" ]] && kill "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Visible windows: Tk keeps a 1x1 helper while the process lives, not counted.
windows() { DISPLAY=":${DISPLAY_NUM}" xwininfo -root -children | grep 'x[0-9]*+' | grep -vc ' 1x1+' || true; }
shot() { DISPLAY=":${DISPLAY_NUM}" import -window root "${SCRATCH}/${SCENARIO}-$1.png"; }
say() { printf 'e2e[%s]: %s\n' "$SCENARIO" "$1"; }
alive() { kill -0 "$GATE_PID" 2>/dev/null; }

seed() {
    rm -rf "${RUN:?}"
    mkdir -p "$RUN"/{home,run,data,root}
    chmod 700 "$RUN/run"
    case "$SCENARIO" in
        short | hold | hold-lift) echo '{"2026-11-03": 10, "2026-11-04": 0}' >"$MINUTES" ;;
        met) echo '{"2026-11-03": 120, "2026-11-04": 0}' >"$MINUTES" ;;
        *) echo "unknown scenario" >&2; exit 1 ;;
    esac
}

free_display() {
    local n
    for n in $(seq 120 199); do
        [[ -e "/tmp/.X${n}-lock" || -e "/tmp/.X11-unix/X${n}" ]] || { echo "$n"; return; }
    done
    echo "no free display" >&2
    exit 1
}

start_x() {
    DISPLAY_NUM="$(free_display)"
    Xvfb ":${DISPLAY_NUM}" -screen 0 3840x2160x24 -nolisten tcp >/dev/null 2>&1 &
    XVFB_PID=$!
    sleep 0.3
    kill -0 "$XVFB_PID" 2>/dev/null || { echo "Xvfb :${DISPLAY_NUM} did not start" >&2; exit 1; }
    for _ in $(seq 50); do
        DISPLAY=":${DISPLAY_NUM}" xdpyinfo >/dev/null 2>&1 && break
        sleep 0.1
    done
}

start_gate() {
    env -u XAUTHORITY HOME="${RUN}/home" XDG_RUNTIME_DIR="${RUN}/run" \
        FOCUS_PROJECT_DATA="${RUN}/data" FOCUS_GUARD_ROOT="${RUN}/root" \
        DISPLAY=":${DISPLAY_NUM}" PYTHONPATH="${REPO_DIR}" \
        "${REPO_DIR}/.venv/bin/python" "${REPO_DIR}/scripts/e2e_driver.py" \
        --today 2026-11-04 --minutes-file "$MINUTES" --hold-file "$HOLD_FLAG" &
    GATE_PID=$!
    sleep 4
}

wait_windows() { # wait_windows <gt|eq0> <seconds>: poll the window count
    local end=$((SECONDS + $2))
    while ((SECONDS < end)); do
        if [[ "$1" == gt ]]; then [[ "$(windows)" -gt 0 ]] && return 0
        else [[ "$(windows)" -eq 0 ]] && return 0; fi
        sleep 0.2
    done
    return 1
}

check_met() {
    alive && { say "FAIL: gate still running"; exit 1; }
    wait "$GATE_PID"
    shot after
    say "PASS: exited 0, no lock (windows on :${DISPLAY_NUM}: $(windows))"
}

check_short() {
    local before start elapsed
    alive || { say "FAIL: no lock process"; exit 1; }
    before="$(windows)"
    shot locked
    say "lock up (windows on :${DISPLAY_NUM}: ${before})"
    [[ "$before" -gt 0 ]] || { say "FAIL: no window"; exit 1; }
    echo '{"2026-11-03": 10, "2026-11-04": 30}' >"$MINUTES"
    start="$(date +%s.%N)"
    echo '{"ts": 0, "source": "e2e"}' >>"${RUN}/data/activity.jsonl"
    for _ in $(seq $((LIFT_BUDGET_S * 10))); do
        alive || break
        sleep 0.1
    done
    elapsed="$(echo "$(date +%s.%N) - $start" | bc)"
    alive && { say "FAIL: lock still up after ${LIFT_BUDGET_S}s"; exit 1; }
    wait "$GATE_PID"
    shot lifted
    say "PASS: lifted in ${elapsed}s on the activity event; windows left: $(windows)"
}

check_hold() {
    alive || { say "FAIL: gate exited, it owes a re-judge after the hold"; exit 1; }
    [[ "$(windows)" -eq 0 ]] || { say "FAIL: a window is up during the hold"; exit 1; }
    shot held
    say "PASS: hold active, debt owed, no lock (windows: $(windows)), gate waiting"
}

check_hold_lift() {
    local start
    alive || { say "FAIL: no lock process"; exit 1; }
    wait_windows gt 10 || { say "FAIL: no lock window"; exit 1; }
    shot locked
    say "lock up (windows: $(windows))"
    touch "$HOLD_FLAG"
    start="$SECONDS"
    wait_windows eq0 "$HOLD_LIFT_BUDGET_S" || { say "FAIL: lock still up after ${HOLD_LIFT_BUDGET_S}s"; exit 1; }
    shot lifted
    say "lifted in $((SECONDS - start))s of the hold starting (budget 60s)"
    alive || { say "FAIL: gate exited, it must wait out the hold"; exit 1; }
    sleep 3
    [[ "$(windows)" -eq 0 ]] || { say "FAIL: re-armed during the hold"; exit 1; }
    rm -f "$HOLD_FLAG"
    wait_windows gt 10 || { say "FAIL: no re-arm after the hold ended"; exit 1; }
    shot rearmed
    say "PASS: re-armed after the hold ended (debt still owed), windows: $(windows)"
}

main() {
    mkdir -p "$SCRATCH"
    seed
    [[ "$SCENARIO" == "hold" ]] && touch "$HOLD_FLAG"
    start_x
    start_gate
    case "$SCENARIO" in
        met) check_met ;;
        hold) check_hold ;;
        hold-lift) check_hold_lift ;;
        *) check_short ;;
    esac
}

main
