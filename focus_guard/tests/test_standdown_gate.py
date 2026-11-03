# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from focus_guard import _cli, _gate, _verdict
from focus_guard.tests._days import DAY
from focus_guard.tests.test_gate import FakeLock, _arm

if TYPE_CHECKING:
    import pytest

    from focus_guard._paths import Paths
    from focus_guard.tests.conftest import World


def test_a_hold_stands_the_verdict_down(world: World) -> None:
    world.short_yesterday().hold = True
    verdict = _verdict.decide(DAY)
    assert (verdict.locked, verdict.held) == (False, True)
    assert verdict.reason == "a hold is active"


def test_a_hold_does_not_erase_yesterday(world: World) -> None:
    world.short_yesterday().hold = True
    world.hold = False
    assert _verdict.decide(DAY).locked


def test_honor_hold_false_still_sees_the_debt(world: World) -> None:
    world.short_yesterday().hold = True
    verdict = _verdict.decide(DAY, honor_hold=False)
    assert verdict.locked
    assert not verdict.held


def test_status_says_a_hold_is_active(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.short_yesterday().hold = True
    assert _cli.main(["status", "--today", DAY.isoformat()]) == 0
    assert capsys.readouterr().out.startswith("open: a hold is active")


def test_no_lock_while_a_hold_is_active_and_none_owed(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.minutes[DAY - timedelta(days=1)] = 120
    world.hold = True
    slept: list[float] = []
    assert (
        _gate.run_gate(tmp_paths, production=True, today=DAY, sleep=slept.append) == 0
    )
    assert not FakeLock.instances
    assert slept == []


def test_owed_but_held_waits_then_locks_when_it_ends(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.short_yesterday().hold = True
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 3:
            world.hold = False

    assert _gate.run_gate(tmp_paths, production=True, today=DAY, sleep=sleep) == 0
    assert len(slept) == 3
    assert len(FakeLock.instances) == 1
    assert FakeLock.instances[0].ran


def test_a_lock_lifted_by_a_hold_does_not_rearm_until_it_ends(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.short_yesterday()
    slept: list[float] = []

    def run(self: FakeLock) -> None:
        self.ran = True
        if len(FakeLock.instances) == 1:
            world.hold = True

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        world.hold = False

    monkeypatch.setattr(FakeLock, "run", run)
    assert _gate.run_gate(tmp_paths, production=True, today=DAY, sleep=sleep) == 0
    assert len(slept) == 1
    assert len(FakeLock.instances) == 2


def test_a_lock_lifted_by_minutes_just_exits(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.short_yesterday()
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert len(FakeLock.instances) == 1


def test_owed_check_with_unreadable_registry_exits(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.hold = True
    world.broken = OSError("disk")
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert not FakeLock.instances
