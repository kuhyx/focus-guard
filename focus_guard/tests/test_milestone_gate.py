# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The milestone lock in the verdict: real focus_project, scratch registry."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import focus_project
import pytest

from focus_guard import _constants, _milestone_forms
from focus_guard._gate import verdict_for
from focus_guard._verdict import decide
from focus_guard.tests import _interview_world as iw

if TYPE_CHECKING:
    from pathlib import Path

    from focus_guard._verdict import Verdict


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> iw.IWorld:
    return iw.install(monkeypatch)


def _decide(now: datetime, *, honor_hold: bool = True) -> Verdict:
    return decide(now.date(), honor_hold=honor_hold, now=now)


def test_a_missed_milestone_locks(world: iw.IWorld) -> None:
    verdict = _decide(iw.TUE)
    assert verdict.locked
    assert verdict.milestone == "rules"
    assert verdict.project_id == iw.PID
    assert verdict.test_at == iw.TEST_AT


def test_minutes_in_do_not_unlock_a_milestone(world: iw.IWorld) -> None:
    # minutes_for is 999 in this world: the old unlock number is long met.
    assert _decide(iw.TUE).locked


def test_completing_it_late_lifts_the_lock(world: iw.IWorld, tmp_path: Path) -> None:
    shot = iw.screenshot(tmp_path)
    focus_project.record_evidence(iw.PID, "rules", "file", file=shot, now=iw.TUE)
    verdict = _decide(iw.TUE)
    assert not verdict.locked
    assert verdict.milestone == ""


def test_the_earliest_missed_milestone_comes_first(
    world: iw.IWorld, tmp_path: Path
) -> None:
    assert _decide(iw.FRI).milestone == "rules"
    shot = iw.screenshot(tmp_path)
    focus_project.record_evidence(iw.PID, "rules", "file", file=shot, now=iw.FRI)
    assert _decide(iw.FRI).milestone == f"trip_ask:{iw.SATURDAY}"


def test_the_test_day_never_locks(world: iw.IWorld) -> None:
    verdict = _decide(iw.at("2026-11-16T09:00"))
    assert not verdict.locked
    assert verdict.milestone == ""


def test_a_sick_day_stands_the_milestone_lock_down(world: iw.IWorld) -> None:
    world.sick.add(iw.TUE.date())
    assert not _decide(iw.TUE).locked


def test_a_free_day_does_not(world: iw.IWorld) -> None:
    world.free.add(iw.TUE.date())
    verdict = _decide(iw.TUE)
    assert verdict.locked
    assert verdict.milestone == "rules"


def test_a_test_hold_stands_down_but_the_debt_stays(world: iw.IWorld) -> None:
    world.hold = True
    held = _decide(iw.TUE)
    assert held.held
    assert not held.locked
    owed = _decide(iw.TUE, honor_hold=False)
    assert owed.locked
    assert owed.milestone == "rules"


def test_unreadable_evidence_fails_open_and_logs(
    world: iw.IWorld, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # A directory where the evidence file should be: OSError on read.
    (tmp_path / "focus_project" / "evidence" / f"{iw.PID}.jsonl").mkdir(parents=True)
    verdict = verdict_for(iw.TUE.date())
    assert verdict is not None
    assert not verdict.locked
    assert "no milestone lock" in caplog.text


def test_default_now_is_the_real_clock_on_the_given_day(
    world: iw.IWorld,
) -> None:
    # A day with nothing due yet (before the project): no lock, no crash.
    assert not decide(date(2026, 11, 3)).locked


def test_a_kind_without_a_form_locks_nothing_and_logs(
    world: iw.IWorld,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    unknown = focus_project.Milestone("hotel:1", iw.TUE, "missed", completed=False)
    monkeypatch.setattr("focus_project.owed_lock", lambda _now: unknown)
    assert not _decide(iw.TUE).locked
    assert "no lock form" in caplog.text


def test_every_kind_in_the_gate_has_a_form() -> None:
    assert set(_milestone_forms.FORMS) == _constants.MILESTONE_KINDS
