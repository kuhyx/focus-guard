# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""What the lock window's buttons do: real focus_project, scratch registry."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import focus_project
from focus_project import evidence
import pytest

from focus_guard import _actions
from focus_guard.tests import _interview_world as iw

if TYPE_CHECKING:
    from pathlib import Path

SAT_ID = f"trip_ask:{iw.SATURDAY}"


@pytest.fixture(autouse=True)
def _world(monkeypatch: pytest.MonkeyPatch) -> iw.IWorld:
    return iw.install(monkeypatch)


def _milestone(now: datetime, mid: str) -> focus_project.Milestone:
    project = focus_project.active(now.date())
    assert project is not None
    return next(m for m in focus_project.milestones(project, now) if m.id == mid)


def test_a_screenshot_completes_the_rules(tmp_path: Path) -> None:
    shot = iw.screenshot(tmp_path)
    assert _actions.submit_file(iw.PID, "rules", shot, iw.TUE)
    assert _milestone(iw.TUE, "rules").completed


def test_an_empty_file_is_refused_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    assert not _actions.submit_file(iw.PID, "rules", empty, iw.TUE)
    assert not _milestone(iw.TUE, "rules").completed
    assert "refused" in caplog.text


def test_no_trip_answers_the_weekend() -> None:
    assert _actions.submit_trip(iw.PID, SAT_ID, None, iw.TUE)
    assert _milestone(iw.FRI, SAT_ID).completed


def test_a_trip_answers_yes_and_announces_the_range() -> None:
    span = (date(2026, 11, 13), date(2026, 11, 15))
    assert _actions.submit_trip(iw.PID, SAT_ID, span, iw.TUE)
    project = focus_project.active(iw.TUE.date())
    assert project is not None
    assert [(t.start, t.end) for t in project.trips] == [span]
    assert dict(project.weekend_answers)[iw.SATURDAY] is True


def test_a_backwards_range_changes_nothing() -> None:
    span = (date(2026, 11, 15), date(2026, 11, 13))
    assert not _actions.submit_trip(iw.PID, SAT_ID, span, iw.TUE)
    assert not _milestone(iw.FRI, SAT_ID).completed


def test_a_score_completes_the_mock() -> None:
    mock = "mock"
    iw.focus_session()
    assert _actions.submit_score(iw.PID, mock, " 87,5 ", iw.FRI)
    assert _milestone(iw.FRI, mock).completed


@pytest.mark.parametrize("text", ["", "abc", "-3", "nan"])
def test_a_bad_score_is_refused(text: str) -> None:
    assert not _actions.submit_score(iw.PID, "mock", text, iw.FRI)
    assert not _milestone(iw.FRI, "mock").completed


def test_the_slot_needs_the_entry_and_then_the_tap() -> None:
    now = iw.at("2026-11-15T13:00")
    assert _actions.submit_slot(iw.PID, "slot", "2026-11-16 10:00", now)
    assert not _milestone(now, "slot").completed
    assert _actions.confirm_slot(iw.PID, "slot", now)
    assert _milestone(now, "slot").completed


def test_a_bad_slot_is_refused() -> None:
    assert not _actions.submit_slot(iw.PID, "slot", "tomorrow", iw.FRI)


def test_phone_recheck_and_tap() -> None:
    mid = f"phone:{iw.SATURDAY}"
    now = iw.at("2026-11-13T14:00")
    focus_project.answer_weekend(iw.PID, iw.SATURDAY, trip=True, now=now)
    report = {"plan": True, "due": 5, "seen_ms": evidence.to_ms(now)}
    focus_project.record_evidence(iw.PID, "phone", "phone_check", report, now=now)
    assert _actions.recheck_phone(iw.PID, mid, now) is True
    assert not _milestone(now, mid).completed
    assert _actions.tap_phone(iw.PID, mid, now)
    assert _milestone(now, mid).completed


def test_phone_recheck_without_a_report_is_none() -> None:
    mid = f"phone:{iw.SATURDAY}"
    now = iw.at("2026-11-13T14:00")
    focus_project.answer_weekend(iw.PID, iw.SATURDAY, trip=True, now=now)
    assert _actions.recheck_phone(iw.PID, mid, now) is None


def test_phone_recheck_of_an_unknown_project_is_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert _actions.recheck_phone("nope", "phone:x", iw.TUE) is None
    assert "recheck" in caplog.text


def test_a_tap_on_a_milestone_that_does_not_exist_fails() -> None:
    assert not _actions.tap_phone(iw.PID, "phone:2030-01-01", iw.TUE)
