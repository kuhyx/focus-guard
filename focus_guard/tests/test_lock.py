# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from focus_guard import _lock
from focus_guard._constants import POLL_INTERVAL_MS, TICK_MS
from focus_guard._verdict import decide
from focus_guard.tests._days import DAY
from focus_guard.tests._lock_fakes import (
    anything,
    arm,
    shown,
    tick,
    window_of,
)

if TYPE_CHECKING:
    from focus_guard._paths import Paths
    from focus_guard.tests.conftest import World


def test_hard_global_grab_in_production(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths, production=True)
    try:
        window = window_of(lock)
        assert window.config.resolved_grab() == "global"
        assert window.config.resolved_disable_vt()
        assert lock.root.titles == ["Focus Guard"]
        assert len(seams.turns) == 1
        assert window.events == ["setup", "grab"]
        assert window.arbiter.events == ["publish", "acquire"]
        assert shown(lock).today.value == "Today 0 / 30 min"
    finally:
        lock.close()


def test_demo_uses_a_local_grab_and_a_close_button(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    window = window_of(lock)
    assert window.config.resolved_grab() == "local"
    assert lock.root.titles == ["Focus Guard [DEMO]"]
    assert seams.turns == []
    lock.build_surface(anything("parent"), anything(SimpleNamespace()))
    assert seams.demo == ["parent", lock.close]
    lock.close()


def test_production_surface_has_no_close_button(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths, production=True)
    lock.build_surface(anything("parent"), anything(SimpleNamespace()))
    assert seams.demo == ["parent"]
    lock.close()


def test_a_credit_event_releases_the_lock(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    window = window_of(lock)
    world.minutes[DAY] = 30
    lock._watcher.changed.set()
    tick(lock)
    assert window.events[-1] == "close"
    assert lock._closed
    assert lock.root.scheduled[-1][0] == TICK_MS
    assert len(lock.root.scheduled) == 1


def test_a_real_file_write_raises_the_flag(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    try:
        (tmp_paths.watch_dir / "activity.jsonl").write_text("{}\n")
        assert lock._watcher.changed.wait(3)
    finally:
        lock.close()


def test_no_event_no_refresh_until_the_backstop(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    world.minutes[DAY] = 30
    for _ in range(POLL_INTERVAL_MS // TICK_MS - 1):
        tick(lock)
    assert not lock._closed
    tick(lock)
    assert lock._closed


def test_still_short_updates_the_numbers_and_stays(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    world.minutes[DAY] = 12
    lock._watcher.changed.set()
    tick(lock)
    assert not lock._closed
    assert shown(lock).today.value == "Today 12 / 30 min"
    assert not lock._watcher.changed.is_set()
    lock.close()


@pytest.mark.parametrize("pool", ["sick", "free"])
def test_a_sick_or_free_day_releases_without_a_credit(
    world: World, tmp_paths: Paths, seams: SimpleNamespace, pool: str
) -> None:
    lock = arm(world, tmp_paths)
    getattr(world, pool).add(DAY)
    lock._watcher.changed.set()
    tick(lock)
    assert lock._closed


def test_an_ended_project_releases(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    world.projects = []
    lock._watcher.changed.set()
    tick(lock)
    assert lock._closed


def test_a_failed_recheck_keeps_the_lock(
    world: World,
    tmp_paths: Paths,
    seams: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lock = arm(world, tmp_paths)
    world.broken = OSError("disk gone")
    lock._watcher.changed.set()
    tick(lock)
    assert not lock._closed
    assert "keeping the lock" in caplog.text
    lock.close()


def test_without_a_pinned_day_the_local_day_is_used(
    world: World,
    tmp_paths: Paths,
    seams: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world.short_yesterday()
    monkeypatch.setattr(_lock, "local_today", lambda: DAY + timedelta(days=0))
    lock = _lock.FocusGuardLock(tmp_paths, decide(DAY), production=False, today=None)
    lock._watcher.changed.set()
    tick(lock)
    assert not lock._closed
    lock.close()


def test_close_is_idempotent_and_run_hands_over(
    world: World, tmp_paths: Paths, seams: SimpleNamespace
) -> None:
    lock = arm(world, tmp_paths)
    window = window_of(lock)
    lock.run()
    lock.close()
    lock.close()
    assert window.events.count("close") == 1
    assert window.events[-2:] == ["run", "close"]


def test_hooks_are_quiet_and_callback_errors_are_logged(
    world: World,
    tmp_paths: Paths,
    seams: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lock = arm(world, tmp_paths)
    lock.teardown_surface(anything(SimpleNamespace()))
    lock.on_focus_ready(None)
    lock.on_callback_error()
    assert "a Tk callback raised" in caplog.text
    lock.close()
