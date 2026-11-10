# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The milestone forms: trip, phone, mock and slot."""

from __future__ import annotations

from datetime import date
import tkinter as tk
from typing import TYPE_CHECKING

import focus_project
from focus_project import evidence
import pytest

from focus_guard._verdict import decide
from focus_guard.tests import _interview_world as iw
from focus_guard.tests._panel_ctx import (
    PHONE_NOW,
    SAT_ID,
    SUN,
    SUN_PM,
    Ctx,
    _done,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture(autouse=True)
def _world(monkeypatch: pytest.MonkeyPatch) -> iw.IWorld:
    return iw.install(monkeypatch)


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    window = tk.Tk()
    yield window
    window.destroy()


def test_trip_no_answers_the_weekend(root: tk.Tk, tmp_path: Path) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    assert ctx.milestone == SAT_ID
    ctx.tap("no_trip")
    assert ctx.done == 1
    assert dict(focus_project.active(iw.FRI.date()).weekend_answers) == {
        iw.SATURDAY: False
    }


def test_trip_yes_takes_a_date_range(root: tk.Tk, tmp_path: Path) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    ctx.tap("trip")
    assert not ctx.has("ok")
    ctx.tap("day2026-11-13")
    assert not ctx.has("ok")
    ctx.tap("day2026-11-15")
    ctx.tap("ok")
    assert ctx.done == 1
    trips = focus_project.active(iw.FRI.date()).trips
    assert [(t.start, t.end) for t in trips] == [
        (date(2026, 11, 13), date(2026, 11, 15))
    ]


def test_trip_range_clicks_in_any_order_and_restart(
    root: tk.Tk, tmp_path: Path
) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    ctx.tap("trip")
    ctx.tap("day2026-11-15")
    ctx.tap("day2026-11-14")
    assert list(ctx.panel.span) == [date(2026, 11, 14), date(2026, 11, 15)]
    ctx.tap("day2026-11-16")
    assert list(ctx.panel.span) == [date(2026, 11, 16)]
    ctx.tap("day2026-11-16")
    assert list(ctx.panel.span) == [date(2026, 11, 16), date(2026, 11, 16)]


def test_past_days_and_days_after_the_test_cannot_be_picked(
    root: tk.Tk, tmp_path: Path
) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    ctx.tap("trip")
    ctx.tap("day2026-11-12")
    ctx.tap("day2026-11-17")
    assert list(ctx.panel.span) == []


def test_a_refused_trip_flashes(root: tk.Tk, tmp_path: Path) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    focus_project.add_trip(iw.PID, date(2026, 11, 14), date(2026, 11, 14), now=iw.FRI)
    ctx.tap("no_trip")  # an announced trip covers the Saturday: refused
    assert ctx.panel.error
    assert ctx.done == 0


def test_phone_recheck_shows_the_dot_and_tap_completes(
    root: tk.Tk, tmp_path: Path
) -> None:
    _done(("rules", "file"), (SAT_ID, "trip"), now=PHONE_NOW, folder=tmp_path)
    ctx = Ctx(root, PHONE_NOW, ())
    assert ctx.milestone.startswith("phone:")
    ctx.tap("recheck")
    first = ctx.panel.dot
    report = {"plan": True, "due": 4, "seen_ms": evidence.to_ms(PHONE_NOW)}
    focus_project.record_evidence(iw.PID, "phone", "phone_check", report, now=PHONE_NOW)
    ctx.tap("recheck")
    assert (first, ctx.panel.dot) == (None, True)
    assert ctx.done == 2
    ctx.tap("offline")
    assert ctx.done == 3
    assert not decide(PHONE_NOW.date(), now=PHONE_NOW).locked


def test_mock_takes_a_score(root: tk.Tk, tmp_path: Path) -> None:
    iw.focus_session()
    _done(("rules", "file"), (SAT_ID, "no_trip"), now=SUN, folder=tmp_path)
    ctx = Ctx(root, SUN, ())
    assert ctx.milestone == "mock"
    entry = ctx.get("entry")
    assert isinstance(entry, tk.Entry)
    ctx.tap("ok")  # empty: refused
    assert ctx.panel.error
    entry.insert(0, "88")
    ctx.tap("ok")
    assert ctx.done == 1
    assert not decide(SUN.date(), now=SUN).locked


def test_return_in_the_entry_submits(root: tk.Tk, tmp_path: Path) -> None:
    _done(("rules", "file"), (SAT_ID, "no_trip"), now=SUN, folder=tmp_path)
    ctx = Ctx(root, SUN, ())
    entry = ctx.get("entry")
    assert isinstance(entry, tk.Entry)
    entry.insert(0, "70")
    entry.focus_force()
    root.update()
    entry.event_generate("<Return>")
    assert ctx.done == 1


def test_slot_is_the_entry_then_the_confirm_tap(root: tk.Tk, tmp_path: Path) -> None:
    done = (("rules", "file"), (SAT_ID, "no_trip"), ("mock", "score"))
    _done(*done, now=SUN_PM, folder=tmp_path)
    ctx = Ctx(root, SUN_PM, ())
    assert ctx.milestone == "slot"
    entry = ctx.get("entry")
    assert isinstance(entry, tk.Entry)
    assert entry.get() == "2026-11-16 10:00"
    entry.delete(0, "end")
    ctx.tap("ok")  # empty: refused
    assert ctx.panel.error
    entry.insert(0, "2026-11-16 10:30")
    ctx.tap("ok")
    assert not ctx.has("entry")
    assert ctx.has("confirm")
    assert decide(SUN_PM.date(), now=SUN_PM).locked
    ctx.tap("confirm")
    assert not decide(SUN_PM.date(), now=SUN_PM).locked
    assert ctx.done >= 1


def test_a_mis_tap_on_the_suitcase_can_still_answer_no(
    root: tk.Tk, tmp_path: Path
) -> None:
    _done(("rules", "file"), now=iw.FRI, folder=tmp_path)
    ctx = Ctx(root, iw.FRI, ())
    ctx.tap("trip")
    ctx.tap("no_trip")
    assert ctx.done == 1
    project = focus_project.active(iw.FRI.date())
    assert project is not None
    assert dict(project.weekend_answers) == {iw.SATURDAY: False}
