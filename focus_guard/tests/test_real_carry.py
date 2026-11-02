# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The verdict counts banked overtime: real focus_project on a scratch data dir."""

from datetime import date, datetime, timedelta

import focus_project as fp
import pytest

from focus_guard._verdict import decide

D1, D2, D3 = date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)


def _work(day: date, mins: int) -> None:
    """``mins`` minutes of tutor heartbeats (one per five minutes) on ``day``."""
    base = datetime(day.year, day.month, day.day, 8).astimezone().timestamp()
    for k in range(1, mins // 5 + 1):
        fp.record_activity("tutor", "heartbeat", ts=base + 300 * k)


@pytest.fixture(autouse=True)
def _scratch_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("focus_project._clock.now", lambda: 1_893_456_000.0)
    monkeypatch.setattr("sickdays.stands_down", lambda *_a, **_k: False)
    monkeypatch.setattr("freedays.is_free_day", lambda *_a, **_k: False)
    fp.create_project(
        "exam",
        name="Exam",
        start=D1,
        end=D1 + timedelta(days=6),
        replaces=["leetcode"],
        daily_minutes=120,
        unlock_minutes=30,
    )


def test_yesterdays_short_day_is_made_up_by_the_banked_overtime() -> None:
    _work(D1, 125)  # five minutes of overtime bank for D2
    _work(D2, 115)  # 115 own + 5 banked = 120: the day is kept
    verdict = decide(D3)
    assert not verdict.locked
    assert verdict.reason == "yesterday kept its number"


def test_without_overtime_the_same_short_day_locks() -> None:
    _work(D1, 120)
    _work(D2, 115)
    verdict = decide(D3)
    assert verdict.locked
    assert verdict.yesterday_minutes == 115


def test_the_unlock_counts_own_plus_carried_minutes() -> None:
    _work(D1, 130)  # ten banked for D2, which then misses (5 + 10 < 120)
    _work(D2, 5)
    assert decide(D3).locked
    _work(D3, 20)  # 20 own; nothing was banked out of the short D2
    assert decide(D3).today_minutes == 20
