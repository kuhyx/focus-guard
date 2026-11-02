# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Run the real gate on a private X display with a seeded scratch registry.

Only the minutes source is faked (``focus_project.minutes_for`` reads a JSON
file the e2e script rewrites); the registry, the window, gatelock and the
inotify watcher are the real ones. Refuses to run on display :0.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import focus_project

from focus_guard import _paths
from focus_guard._gate import run_gate

if TYPE_CHECKING:
    from collections.abc import Callable


def _fake_minutes(source: Path) -> Callable[[date], int]:
    def minutes_for(day: date) -> int:
        data = json.loads(source.read_text()) if source.exists() else {}
        return int(data.get(day.isoformat(), 0))

    return minutes_for


def main() -> int:
    """Seed, fake the minutes, run the production gate on the private display."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=date.fromisoformat, required=True)
    parser.add_argument("--minutes-file", type=Path, required=True)
    args = parser.parse_args()
    display = os.environ.get("DISPLAY", "")
    if not display or display == ":0":
        sys.stderr.write(f"refusing to run on display {display!r}\n")
        return 2
    focus_project.create_project(
        "exam",
        name="Exam prep",
        start=date(2026, 11, 2),
        end=date(2026, 11, 8),
        replaces=["leetcode", "reading", "tutor"],
        daily_minutes=120,
        unlock_minutes=30,
    )
    vars(focus_project)["minutes_for"] = _fake_minutes(args.minutes_file)
    _paths.MORNING_RETRY_SECONDS = 0.0
    return run_gate(_paths.paths(), production=True, today=args.today)


if __name__ == "__main__":
    sys.exit(main())
