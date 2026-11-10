# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""run_gate with milestone locks: one window per missed milestone, no loops."""

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING, ClassVar

import focus_project
import pytest

from focus_guard import _gate
from focus_guard.tests import _interview_world as iw

if TYPE_CHECKING:
    from pathlib import Path

    from focus_guard._paths import Paths
    from focus_guard._verdict import Verdict

DAY = iw.FRI.date()


class FakeLock:
    """Stands in for the window; "completes" what it was opened for."""

    instances: ClassVar[list[FakeLock]] = []
    complete: ClassVar[bool] = True
    folder: ClassVar[Path]

    def __init__(
        self, _paths: Paths, verdict: Verdict, *, production: bool, today: object
    ) -> None:
        del production, today
        self.verdict = verdict
        FakeLock.instances.append(self)

    def run(self) -> None:
        if not FakeLock.complete:
            return
        mid = self.verdict.milestone
        if mid == "rules":
            shot = iw.screenshot(FakeLock.folder)
            focus_project.record_evidence(iw.PID, mid, "file", file=shot, now=iw.FRI)
        else:
            focus_project.answer_weekend(iw.PID, iw.SATURDAY, trip=False, now=iw.FRI)


@pytest.fixture(autouse=True)
def _world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    iw.install(monkeypatch)
    FakeLock.instances.clear()
    FakeLock.complete = True
    FakeLock.folder = tmp_path
    monkeypatch.setattr(_gate, "FocusGuardLock", FakeLock)
    monkeypatch.setattr(_gate, "wait_for_x_server", lambda: None)
    monkeypatch.setattr(
        "focus_guard._verdict.now_for", lambda day: datetime.combine(day, time(12))
    )


def test_each_missed_milestone_gets_its_window_in_turn(tmp_paths: Paths) -> None:
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert [lock.verdict.milestone for lock in FakeLock.instances] == [
        "rules",
        f"trip_ask:{iw.SATURDAY}",
    ]


def test_a_window_closed_without_completing_does_not_reopen(
    tmp_paths: Paths,
) -> None:
    FakeLock.complete = False
    assert _gate.run_gate(tmp_paths, production=False, today=DAY) == 0
    assert len(FakeLock.instances) == 1


def test_nothing_missed_nothing_opens(tmp_paths: Paths) -> None:
    assert _gate.run_gate(tmp_paths, production=True, today=iw.START) == 0
    assert not FakeLock.instances
