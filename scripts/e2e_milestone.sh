#!/bin/bash
# E2E of the interview-milestone lock on a private Xvfb (never :0).
#   lock  -> rules missed: the eye window appears; real clicks pick the
#            screenshot and tick it; the evidence row lands; the window closes
#   done  -> every milestone done: no window, exit 0
#   trip|phone|mock|slot -> that milestone is missed: its window appears
#            (screenshot only), then the gate is killed
#   with a second argument "act" (trip|mock|slot): real X input completes it
#            (trip: no-trip tap; mock: typed score + tick; slot: tick, confirm)
#            and the evidence row must land
# Usage: scripts/e2e_milestone.sh lock|done|trip|phone|mock|slot [act]
# Scratch HOME/XDG_RUNTIME_DIR/data keep real pools, claims and registry out.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_DIR
readonly SCENARIO="${1:?lock|done|trip|phone|mock|slot}"
readonly ACT="${2:-}"
# Real input per scenario (names of the widgets to tap, or type:<text>) and
# the evidence kind each must record.
declare -A CLICKS=([lock]="thumb0,ok" [trip]="no_trip" [mock]="type:88,ok" [slot]="ok,confirm")
declare -A KINDS=([lock]="file" [trip]="answer" [mock]="score" [slot]="slot_confirm")
readonly SCRATCH="${E2E_DIR:-$HOME/data/claude-scratch/e2e/focus-guard}"
readonly TAG="${SCENARIO}${ACT:+-${ACT}}"
readonly RUN="${SCRATCH}/ms-${TAG}-run"
readonly FLAG="${RUN}/click.flag"
readonly CLOSE_BUDGET_S=20
GATE_PID=""
XVFB_PID=""
DISPLAY_NUM=""

cleanup() {
    [[ -n "$GATE_PID" ]] && kill "$GATE_PID" 2>/dev/null || true
    [[ -n "$XVFB_PID" ]] && kill "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

windows() { DISPLAY=":${DISPLAY_NUM}" xwininfo -root -children | grep 'x[0-9]*+' | grep -vc ' 1x1+' || true; }
shot() { DISPLAY=":${DISPLAY_NUM}" import -window root "${SCRATCH}/ms-${TAG}-$1.png"; }
say() { printf 'e2e[%s]: %s\n' "$TAG" "$1"; }
alive() { kill -0 "$GATE_PID" 2>/dev/null; }

seed() {
    rm -rf "${RUN:?}"
    mkdir -p "$RUN"/{home,run,data,root/pictures,shim}
    chmod 700 "$RUN/run"
    magick -size 1200x700 gradient:'#336699-#99ccee' "$RUN/root/pictures/rules.png"
    # A redirected HOME hides the user site-packages (editable installs):
    # addsitedir brings them back, the worktree stays first on PYTHONPATH.
    printf 'import site\nsite.addsitedir("%s/.local/lib/python3.14/site-packages")\n' \
        "$HOME" >"$RUN/shim/sitecustomize.py"
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
    for _ in $(seq 50); do
        DISPLAY=":${DISPLAY_NUM}" xdpyinfo >/dev/null 2>&1 && return
        sleep 0.1
    done
    echo "Xvfb :${DISPLAY_NUM} did not start" >&2
    exit 1
}

start_gate() {
    local click=""
    if [[ "$SCENARIO" == lock || -n "$ACT" ]]; then click="${CLICKS[$SCENARIO]}"; fi
    env -u XAUTHORITY HOME="${RUN}/home" XDG_RUNTIME_DIR="${RUN}/run" \
        FOCUS_PROJECT_DATA="${RUN}/data" FOCUS_GUARD_ROOT="${RUN}/root" \
        DISPLAY=":${DISPLAY_NUM}" PYTHONPATH="${REPO_DIR}:${RUN}/shim" \
        /usr/bin/python3 "${REPO_DIR}/scripts/e2e_interview.py" \
        --scenario "$SCENARIO" --picture "${RUN}/root/pictures/rules.png" \
        --minutes-file "${RUN}/minutes.json" --click "$click" --click-flag "$FLAG" &
    GATE_PID=$!
}

wait_windows() { # wait_windows <gt|eq0> <seconds>
    local end=$((SECONDS + $2))
    while ((SECONDS < end)); do
        if [[ "$1" == gt ]]; then [[ "$(windows)" -gt 0 ]] && return 0
        else [[ "$(windows)" -eq 0 ]] && return 0; fi
        sleep 0.2
    done
    return 1
}

check_act() {
    wait_windows gt 30 || { say "FAIL: no lock window"; exit 1; }
    sleep 3
    shot locked
    say "window up (windows: $(windows))"
    touch "$FLAG"
    local end=$((SECONDS + CLOSE_BUDGET_S))
    while alive && ((SECONDS < end)); do sleep 0.2; done
    alive && { say "FAIL: still up ${CLOSE_BUDGET_S}s after the input"; exit 1; }
    wait "$GATE_PID"
    shot lifted
    grep -q "\"kind\": \"${KINDS[$SCENARIO]}\"" "${RUN}"/data/evidence/interview.jsonl \
        || { say "FAIL: no ${KINDS[$SCENARIO]} evidence row"; exit 1; }
    say "PASS: input recorded ${KINDS[$SCENARIO]}, window closed (windows left: $(windows))"
}

check_done() {
    sleep 4
    alive && { say "FAIL: gate still running"; exit 1; }
    wait "$GATE_PID"
    shot after
    [[ "$(windows)" -eq 0 ]] || { say "FAIL: a window is up"; exit 1; }
    say "PASS: exited 0, no window (windows: $(windows))"
}

check_shown() {
    wait_windows gt 30 || { say "FAIL: no lock window"; exit 1; }
    sleep 4 # the arbiter and the first paint run niced under the cap
    shot locked
    say "PASS: window up for the missed ${SCENARIO} milestone (windows: $(windows))"
    kill "$GATE_PID" 2>/dev/null || true
    wait "$GATE_PID" 2>/dev/null || true
    GATE_PID=""
}

main() {
    mkdir -p "$SCRATCH"
    seed
    start_x
    start_gate
    if [[ "$SCENARIO" == lock || -n "$ACT" ]]; then
        check_act
    elif [[ "$SCENARIO" == "done" ]]; then
        check_done
    else
        check_shown
    fi
    say "xwininfo children after: $(windows)"
}

main
