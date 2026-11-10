# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The lock's one question, about yesterday. Pure reads, no writes.

focus_project is called through the module so tests patch one attribute.
A registry that cannot be read raises; the caller picks the failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import TYPE_CHECKING

import focus_project
import freedays
import sickdays

from focus_guard import _standdown
from focus_guard._constants import JUDGE_FROM, MILESTONE_KINDS

if TYPE_CHECKING:
    from focus_project import Project

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Owed:
    """The interview milestone a lock is for."""

    milestone: str
    project_id: str
    test_at: datetime | None


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
    owed: Owed | None = None
    """The missed interview milestone when this is a milestone lock."""

    @property
    def milestone(self) -> str:
        """Id of the missed milestone, or "" for a minute lock / no lock."""
        return self.owed.milestone if self.owed else ""

    @property
    def project_id(self) -> str:
        """The interview project the milestone belongs to, or ""."""
        return self.owed.project_id if self.owed else ""

    @property
    def test_at(self) -> datetime | None:
        """When the test is, for a milestone lock."""
        return self.owed.test_at if self.owed else None


def local_today() -> date:
    """Today's date in the local zone."""
    return datetime.now().astimezone().date()


def now_for(today: date) -> datetime:
    """Naive local "now" on ``today`` (the real clock time of day)."""
    stamp = datetime.now().astimezone().replace(tzinfo=None)
    return datetime.combine(today, stamp.time())


def _sick(day: date) -> bool:
    return sickdays.stands_down("focus", day)


def _off(day: date) -> bool:
    return _sick(day) or freedays.is_free_day(day)


def _milestone_lock(today: date, now: datetime) -> Verdict | None:
    """The lock for the earliest missed interview milestone, or None.

    Only a sick day stands it down: a free day does not (a free day pays off
    the minute rule, not an interview obligation). It lifts only when the
    milestone is completed; the unlock minutes play no part.
    """
    if _sick(today):
        return None
    owed = focus_project.owed_lock(now)
    project = focus_project.active(today) if owed is not None else None
    if owed is None or project is None:
        return None
    if owed.id.partition(":")[0] not in MILESTONE_KINDS:
        _logger.error("milestone %s has no lock form, not locking", owed.id)
        return None
    return Verdict(
        locked=True,
        reason="interview milestone missed",
        name=project.name,
        owed=Owed(owed.id, project.id, project.test_at),
    )


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


def decide(
    today: date, *, honor_hold: bool = True, now: datetime | None = None
) -> Verdict:
    """Locked iff a milestone is missed, or yesterday missed its number.

    The milestone lock comes first and ignores the minutes (see
    :func:`_milestone_lock`); otherwise the old minute rule applies.

    A test hold covering now stands the verdict down but never erases the
    debt: ``honor_hold=False`` asks what would be owed once it ends.
    """
    if honor_hold and _standdown.active():
        return Verdict(locked=False, reason=_standdown.HOLD_REASON, held=True)
    milestone = _milestone_lock(today, now or now_for(today))
    if milestone is not None:
        return milestone
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
