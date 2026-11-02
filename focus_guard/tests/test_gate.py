# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, ClassVar

from focus_guard import _gate
from focus_guard.tests._days import DAY

if TYPE_CHECKING:
    import pytest

    from focus_guard._paths import Paths
    from focus_guard._verdict import Verdict
    from focus_guard.tests.conftest import World


class FakeLock:
    instances: ClassVar[list[FakeLock]] = []

    def __init__(
        self, _paths: Paths, verdict: Verdict, *, production: bool, today: date | None
    ) -> None:
        self.args = (verdict.locked, production, today)
        self.ran = False
        FakeLock.instances.append(self)

    def run(self) -> None:
        self.ran = True


def _arm(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    FakeLock.instances.clear()
    calls: list[str] = []
    monkeypatch.setattr(_gate, "FocusGuardLock", FakeLock)
    monkeypatch.setattr(_gate, "wait_for_x_server", lambda: calls.append("x"))
    return calls


def test_locks_when_owed(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _arm(monkeypatch)
    world.short_yesterday()
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert calls == ["x"]
    assert FakeLock.instances[0].args == (True, True, DAY)
    assert FakeLock.instances[0].ran


def test_demo_does_not_wait_for_x(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _arm(monkeypatch)
    world.short_yesterday()
    _gate.run_gate(tmp_paths, production=False, today=DAY)
    assert calls == []
    assert FakeLock.instances[0].args == (True, False, DAY)


def test_no_window_when_not_owed(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    world.minutes[DAY - timedelta(days=1)] = 120
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert not FakeLock.instances


def test_unreadable_registry_fails_open(
    world: World,
    tmp_paths: Paths,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _arm(monkeypatch)
    world.broken = ValueError("bad row")
    assert _gate.run_gate(tmp_paths, production=True, today=DAY) == 0
    assert not FakeLock.instances
    assert "cannot read the focus project" in caplog.text


def test_morning_carrot_holds_the_gate(
    world: World,
    tmp_paths: Paths,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _arm(monkeypatch)
    world.short_yesterday()
    monkeypatch.setattr(_gate, "gate_hold", lambda *_a, **_k: "morning carrot")
    _gate.run_gate(tmp_paths, production=True, today=DAY)
    assert not FakeLock.instances
    assert "not locking yet" in caplog.text


def test_defaults_to_today(
    world: World, tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _arm(monkeypatch)
    monkeypatch.setattr(_gate, "local_today", lambda: DAY)
    world.short_yesterday()
    _gate.run_gate(tmp_paths, production=False)
    assert FakeLock.instances
