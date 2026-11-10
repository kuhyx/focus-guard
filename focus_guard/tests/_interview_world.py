# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""A real interview project in a scratch registry; only the day pools are fake."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import json
from typing import TYPE_CHECKING

import focus_project
from focus_project._paths import activity_path

from focus_guard import _standdown

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def at(text: str) -> datetime:
    """A naive local moment from ``YYYY-MM-DDTHH:MM``."""
    return datetime.fromisoformat(text)


PID = "interview"
START = date.fromisoformat("2026-11-09")
TEST_AT = at("2026-11-16T10:00")
SATURDAY = date.fromisoformat("2026-11-14")
TUE = at("2026-11-10T09:00")
"""rules (due Mon 23:59) is missed; nothing else is due yet."""
FRI = at("2026-11-13T09:00")
"""rules and trip_ask:<sat> (Thu 23:59) are missed."""


@dataclass
class IWorld:
    """Fake sick/free pools and hold around the real registry."""

    sick: set[date] = field(default_factory=set)
    free: set[date] = field(default_factory=set)
    hold: bool = False
    asked: list[str] = field(default_factory=list)

    def covers(self, gate: str, now: datetime | None = None) -> bool:
        del now
        self.asked.append(gate)
        return self.hold

    def next_change(self, now: datetime) -> datetime | None:
        return now + timedelta(seconds=1) if self.hold else None


def install(monkeypatch: pytest.MonkeyPatch) -> IWorld:
    """Create the project in the (already redirected) registry, patch the pools."""
    fake = IWorld()
    focus_project.create_project(
        PID,
        name="Interview",
        start=START,
        end=TEST_AT.date(),
        replaces=["leetcode"],
        daily_minutes=120,
        unlock_minutes=30,
        kind="interview",
        test_at=TEST_AT,
    )
    monkeypatch.setattr("sickdays.stands_down", lambda _l, day, **_k: day in fake.sick)
    monkeypatch.setattr("freedays.is_free_day", lambda day, **_k: day in fake.free)
    monkeypatch.setattr("focus_project.minutes_for", lambda _day: 999)
    monkeypatch.setattr(_standdown, "holds", fake)
    return fake


def focus_session() -> None:
    """A 100 min contiguous timer session on Nov 9, before any score row."""
    first = datetime.combine(START, time(8))
    activity_path().parent.mkdir(parents=True, exist_ok=True)
    with activity_path().open("a", encoding="utf-8") as handle:
        for offset in range(0, 101, 5):
            row = {
                "ts": (first + timedelta(minutes=offset)).timestamp(),
                "source": "timer",
                "kind": "start" if offset == 0 else "check" + "in",  # the timer kind
                "project": PID,
                "dev": "pc",
            }
            handle.write(json.dumps(row) + "\n")


def screenshot(folder: Path, name: str = "shot.png") -> Path:
    """A non-empty file standing in for the rules screenshot."""
    path = folder / name
    path.write_bytes(b"not really a png")
    return path
