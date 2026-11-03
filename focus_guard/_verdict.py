# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The lock's one question, about yesterday. Pure reads, no writes.

focus_project is called through the module so tests patch one attribute.
A registry that cannot be read raises; the caller picks the failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import focus_project
import freedays
import sickdays

from focus_guard import _standdown
from focus_guard._constants import JUDGE_FROM

if TYPE_CHECKING:
    from focus_project import Project


@dataclass(frozen=True)
class Verdict:
    """The decision plus the numbers the lock window shows."""

    locked: bool
    reason: str
    name: str = ""
    today_minutes: int = 0
    unlock_minutes: int = 0
    yesterday_minutes: int = 0
    daily_minutes: int = 0
    held: bool = False


def local_today() -> date:
    """Today's date in the local zone."""
    return datetime.now().astimezone().date()


def _off(day: date) -> bool:
    return sickdays.stands_down("focus", day) or freedays.is_free_day(day)


def _kept(yesterday: date, project: Project) -> tuple[bool, int]:
    if _off(yesterday):
        return True, 0
    minutes = focus_project.minutes_for(yesterday)
    return minutes >= project.daily_on(yesterday), minutes


def _preconditions(today: date) -> tuple[Project, Project] | str:
    """Today's and yesterday's project, or why the gate stands down."""
    yesterday = today - timedelta(days=1)
    if yesterday < JUDGE_FROM:
        return "before the first judged day"
    if _off(today):
        return "today is a sick or free day"
    project = focus_project.active(today)
    if project is None:
        return "no project today"
    before = focus_project.active(yesterday)
    if before is None:
        return "yesterday was not a project day"
    return project, before


def decide(today: date, *, honor_hold: bool = True) -> Verdict:
    """Locked iff yesterday missed its number and today is still short.

    A test hold covering now stands the verdict down but never erases the
    debt: ``honor_hold=False`` asks what would be owed once it ends.
    """
    if honor_hold and _standdown.active():
        return Verdict(locked=False, reason=_standdown.HOLD_REASON, held=True)
    found = _preconditions(today)
    if isinstance(found, str):
        return Verdict(locked=False, reason=found)
    project, before = found
    kept, missed_with = _kept(today - timedelta(days=1), before)
    if kept:
        return Verdict(locked=False, reason="yesterday kept its number")
    done = focus_project.minutes_for(today)
    need = project.unlock_on(today)
    unlocked = done >= need
    return Verdict(
        locked=not unlocked,
        reason="today's minutes are in" if unlocked else "yesterday fell short",
        name=project.name,
        today_minutes=done,
        unlock_minutes=need,
        yesterday_minutes=missed_with,
        daily_minutes=before.daily_on(today - timedelta(days=1)),
    )
