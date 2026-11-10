# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""FocusGuardLock when the verdict is a milestone: the panel, not the status."""

from __future__ import annotations

from datetime import date, datetime, time
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar

import focus_project
import pytest

from focus_guard import _constants, _lock
from focus_guard._paths import Paths
from focus_guard._verdict import Verdict, decide
from focus_guard.tests import _interview_world as iw
from focus_guard.tests._lock_fakes import anything, tick, window_of

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class FakePanel:
    made: ClassVar[list[FakePanel]] = []

    def __init__(
        self,
        _root: object,
        verdict: Verdict,
        *,
        pick_dirs: tuple[Path, ...],
        now: Callable[[], datetime],
        on_done: Callable[[], None],
    ) -> None:
        self.verdict, self.pick_dirs, self.now, self.on_done = (
            verdict,
            pick_dirs,
            now,
            on_done,
        )
        self.built: list[object] = []
        self.focused = 0
        FakePanel.made.append(self)

    def build(self, parent: object) -> None:
        self.built.append(parent)

    def focus(self) -> None:
        self.focused += 1


def noon(day: date) -> datetime:
    return datetime.combine(day, time(12))


@pytest.fixture(autouse=True)
def _world(monkeypatch: pytest.MonkeyPatch) -> iw.IWorld:
    FakePanel.made.clear()
    monkeypatch.setattr(_lock, "MilestonePanel", FakePanel)
    monkeypatch.setattr("focus_guard._verdict.now_for", noon)
    monkeypatch.setattr(_lock, "now_for", noon)
    return iw.install(monkeypatch)


def _arm(paths: Paths, now: datetime = iw.TUE, *, production: bool = False) -> Any:
    verdict = decide(now.date())
    assert verdict.milestone
    return _lock.FocusGuardLock(paths, verdict, production=production, today=now.date())


def test_the_panel_is_built_instead_of_the_status(
    tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = _arm(tmp_paths)
    lock.build_surface(anything("parent"), anything(SimpleNamespace()))
    (panel,) = FakePanel.made
    assert panel.built == ["parent"]
    assert seams.demo == [lock.close]  # the demo close only, no status
    assert panel.verdict.milestone == "rules"
    assert panel.now() == iw.at("2026-11-10T12:00")
    lock.close()


def test_production_has_no_close_button(
    tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = _arm(tmp_paths, production=True)
    lock.build_surface(anything("parent"), anything(SimpleNamespace()))
    assert seams.demo == []
    lock.close()


def test_the_picture_folders_come_from_the_paths(
    tmp_path: Path, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    where = Paths(
        watch_dir=tmp_paths.watch_dir,
        morning_session=tmp_paths.morning_session,
        night_lockdown=tmp_paths.night_lockdown,
        pick_dirs=(tmp_path / "pics",),
    )
    lock = _arm(where)
    assert FakePanel.made[0].pick_dirs == (tmp_path / "pics",)
    lock.close()


def test_focus_goes_to_the_panel(tmp_paths: Paths, seams: SimpleNamespace) -> None:
    lock = _arm(tmp_paths)
    lock.on_focus_ready(None)
    assert FakePanel.made[0].focused == 0
    lock.on_focus_ready(anything(SimpleNamespace()))
    assert FakePanel.made[0].focused == 1
    lock.close()


def test_a_status_lock_has_no_panel(tmp_paths: Paths, seams: SimpleNamespace) -> None:
    verdict = Verdict(locked=True, reason="r")
    lock = _lock.FocusGuardLock(tmp_paths, verdict, production=False, today=None)
    lock.on_focus_ready(anything(SimpleNamespace()))
    assert not FakePanel.made
    lock.close()


def test_completing_it_releases_the_lock(
    tmp_path: Path, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = _arm(tmp_paths)
    window = window_of(lock)
    focus_project.record_evidence(
        iw.PID, "rules", "file", file=iw.screenshot(tmp_path), now=iw.TUE
    )
    FakePanel.made[0].on_done()
    assert window.events[-1] == "close"
    assert lock._closed


def test_still_missed_keeps_the_lock_and_the_poll_rechecks(
    tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = _arm(tmp_paths)
    lock._watcher.changed.set()
    tick(lock)
    assert not lock._closed
    lock.close()


def test_another_missed_milestone_closes_it_so_the_gate_reopens(
    tmp_path: Path, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = _arm(tmp_paths, iw.FRI)
    focus_project.record_evidence(
        iw.PID, "rules", "file", file=iw.screenshot(tmp_path), now=iw.FRI
    )
    FakePanel.made[0].on_done()
    assert lock._closed


def test_a_sick_day_releases_a_milestone_lock(
    tmp_paths: Paths, seams: SimpleNamespace, _world: iw.IWorld
) -> None:
    lock = _arm(tmp_paths)
    _world.sick.add(iw.TUE.date())
    lock._watcher.changed.set()
    tick(lock)
    assert lock._closed


def test_watching_the_registry_file() -> None:
    assert "projects.json" in _constants.WATCHED_FILES
