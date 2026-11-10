# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Run the real gate on a private X display against a seeded interview project.

Only the clock's time of day, the minutes source and (optionally) the real
pointer clicks are driven from here; the registry, evidence store, window,
gatelock and the tap handlers are the production ones. The clicks are real X
input (xdotool on the private display) so the lock's grab is exercised.
Refuses to run on display :0.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

import focus_project

from focus_guard import _lock, _milestone_view, _paths, _verdict
from focus_guard._gate import run_gate

if TYPE_CHECKING:
    import tkinter as tk

PID = "interview"
SATURDAY = date(2026, 11, 14)
EARLY = datetime.fromisoformat("2026-11-10T08:00")
# scenario -> (the moment it is, what was already done)
SCENARIOS: dict[str, tuple[str, tuple[str, ...]]] = {
    "lock": ("2026-11-10T13:00", ()),
    "done": ("2026-11-10T13:00", ("rules",)),
    "trip": ("2026-11-13T09:00", ("rules",)),
    "phone": ("2026-11-13T14:00", ("rules", "trip")),
    "mock": ("2026-11-15T09:00", ("rules", "no_trip")),
    "slot": ("2026-11-15T13:00", ("rules", "no_trip", "mock")),
}
CLICK_EVERY_MS = 900
TYPE_PREFIX = "type:"


def _seed(done: tuple[str, ...], picture: Path) -> None:
    focus_project.create_project(
        PID,
        name="Interview",
        start=date(2026, 11, 9),
        end=date(2026, 11, 16),
        replaces=["leetcode"],
        daily_minutes=120,
        unlock_minutes=30,
        kind="interview",
        test_at=datetime.fromisoformat("2026-11-16T10:00"),
    )
    for step in done:
        if step == "rules":
            focus_project.record_evidence(PID, "rules", "file", file=picture, now=EARLY)
        elif step == "mock":
            focus_project.record_evidence(PID, "mock", "score", 80, now=EARLY)
        else:
            focus_project.answer_weekend(PID, SATURDAY, trip=step == "trip", now=EARLY)


def _find(parent: tk.Misc, name: str) -> tk.Misc | None:
    for child in parent.winfo_children():
        if child.winfo_name() == name:
            return child
        found = _find(child, name)
        if found is not None:
            return found
    return None


def _click(parent: tk.Misc, names: list[str], flag: Path) -> None:
    """Once ``flag`` exists, click each named widget, or type ``type:<text>``."""
    if not flag.exists():
        parent.after(200, _click, parent, names, flag)
        return
    if not names:
        return
    token = names[0]
    if token.startswith(TYPE_PREFIX):
        subprocess.run(
            ["/usr/bin/xdotool", "type", "--delay", "50", token[len(TYPE_PREFIX) :]],
            check=True,
        )
        names = names[1:]
    elif (widget := _find(parent, token)) is not None:
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() // 2
        subprocess.run(
            ["/usr/bin/xdotool", "mousemove", str(x), str(y), "click", "1"],
            check=True,
        )
        names = names[1:]
    parent.after(CLICK_EVERY_MS, _click, parent, names, flag)


def _drive_clicks(names: list[str], flag: Path) -> None:
    """Swap the lock's panel class for one that also clicks (a subclass)."""

    class Clicking(_milestone_view.MilestonePanel):
        """The production panel plus the click schedule."""

        def build(self, parent: tk.Misc) -> None:
            super().build(parent)
            parent.after(300, _click, parent, names, flag)

    vars(_lock)["MilestonePanel"] = Clicking


def main() -> int:
    """Seed, pin the moment, run the production gate on the private display."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    parser.add_argument("--picture", type=Path, required=True)
    parser.add_argument("--minutes-file", type=Path, required=True)
    parser.add_argument("--click", default="")
    parser.add_argument("--click-flag", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("DISPLAY", ":0") in {"", ":0"}:
        sys.stderr.write("e2e: DISPLAY must be a private Xvfb, never :0\n")
        return 2
    moment, done = SCENARIOS[args.scenario]
    at = datetime.fromisoformat(moment)
    _seed(done, args.picture)

    def now_for(day: date) -> datetime:
        return datetime.combine(day, at.time())

    vars(_verdict)["now_for"] = now_for
    vars(_lock)["now_for"] = now_for
    minutes = {
        f"2026-11-{day:02d}": 999 for day in range(1, 31)
    }  # the minute rule never fires: only milestones are under test
    args.minutes_file.write_text(json.dumps(minutes))
    vars(focus_project)["minutes_for"] = lambda day: minutes.get(day.isoformat(), 0)
    if args.click:
        _drive_clicks(args.click.split(","), args.click_flag)
    _paths.MORNING_RETRY_SECONDS = 0.0
    return run_gate(_paths.paths(), production=True, today=at.date())


if __name__ == "__main__":
    sys.exit(main())
