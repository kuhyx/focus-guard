# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Hermetic defaults for every test: no real registry, pools or stamps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

from focus_project import Limits, Project
import pytest

from focus_guard import _lock, _paths, _standdown
from focus_guard._paths import Paths
from focus_guard.tests import _lock_fakes as fk
from focus_guard.tests._days import DAY

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def project(
    start: date = date(2026, 11, 2),
    end: date = date(2026, 11, 8),
    *,
    history: tuple[Limits, ...] = (),
    daily: int = 120,
    unlock: int = 30,
) -> Project:
    return Project(
        id="exam",
        name="Exam",
        start=start,
        end=end,
        replaces=("leetcode",),
        daily_minutes=daily,
        unlock_minutes=unlock,
        history=history,
    )


@dataclass
class World:
    """The faked outside: registry, minutes and the two day pools."""

    projects: list[Project] = field(default_factory=lambda: [project()])
    minutes: dict[date, int] = field(default_factory=dict)
    sick: set[date] = field(default_factory=set)
    kept: set[date] = field(default_factory=set)
    free: set[date] = field(default_factory=set)
    broken: Exception | None = None
    hold: bool = False
    hold_ends_in: float | None = None
    asked: list[str] = field(default_factory=list)

    def covers(self, gate: str, now: datetime | None = None) -> bool:
        del now
        self.asked.append(gate)
        return self.hold

    def next_change(self, now: datetime) -> datetime | None:
        if self.hold_ends_in is None:
            return None
        return now + timedelta(seconds=self.hold_ends_in)

    def active(self, day: date) -> Project | None:
        if self.broken:
            raise self.broken
        return next((p for p in self.projects if p.covers(day)), None)

    def minutes_for(self, day: date) -> int:
        return self.minutes.get(day, 0)

    def short_yesterday(self) -> World:
        self.minutes[DAY - timedelta(days=1)] = 10
        return self


@pytest.fixture
def tmp_paths(tmp_path: Path) -> Paths:
    return Paths(
        watch_dir=tmp_path / "focus_project",
        morning_session=tmp_path / "morning_session.json",
        night_lockdown=tmp_path / "locked_at_epoch",
    )


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> World:
    fake = World()
    monkeypatch.setattr("focus_project.active", fake.active)
    monkeypatch.setattr("focus_project.minutes_for", fake.minutes_for)
    monkeypatch.setattr("sickdays.is_sick_day", lambda day, **_k: day in fake.sick)
    monkeypatch.setattr(
        "sickdays.stands_down",
        lambda locker, day, **_k: (
            locker == "focus" and day in fake.sick and day not in fake.kept
        ),
    )
    monkeypatch.setattr("freedays.is_free_day", lambda day, **_k: day in fake.free)
    monkeypatch.setattr(_standdown, "holds", fake)
    return fake


@pytest.fixture(autouse=True)
def _hermetic(
    tmp_paths: Paths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    _paths.set_override(tmp_paths)
    monkeypatch.setenv("FOCUS_PROJECT_DATA", str(tmp_path / "focus_project"))
    monkeypatch.delenv("FOCUS_GUARD_ROOT", raising=False)
    monkeypatch.setattr("focus_guard._paths.MORNING_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(_standdown, "holds", None)
    yield
    _paths.set_override(None)


@pytest.fixture
def seams(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    turns: list[fk.FakeArbiter] = []
    demo: list[object] = []
    monkeypatch.setattr(_lock, "assert_not_under_pytest", lambda _what: None)
    monkeypatch.setattr(_lock, "GateRoot", fk.FakeRoot)
    monkeypatch.setattr(_lock, "Arbiter", fk.FakeArbiter)
    monkeypatch.setattr(_lock, "LockWindow", fk.FakeWindow)
    monkeypatch.setattr(_lock, "wait_for_turn", turns.append)
    monkeypatch.setattr(
        _lock,
        "make_vars",
        lambda _root: SimpleNamespace(
            title=fk.FakeVar(),
            today=fk.FakeVar(),
            yesterday=fk.FakeVar(),
            fraction=fk.FakeVar(),
        ),
    )
    monkeypatch.setattr(
        _lock, "build_status", lambda parent, _vars: demo.append(parent)
    )
    monkeypatch.setattr(
        _lock, "install_demo_close", lambda _parent, cb: demo.append(cb)
    )
    return SimpleNamespace(turns=turns, demo=demo)
