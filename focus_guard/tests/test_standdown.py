# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import TYPE_CHECKING

from focus_guard import _standdown
from focus_guard._standdown import HOLD_POLL_SECONDS, active, load_holds, wait_s

if TYPE_CHECKING:
    import pytest

    from focus_guard.tests.conftest import World


def test_no_hold_is_not_a_standdown(world: World) -> None:
    assert not active()
    assert world.asked == ["focus"]


def test_a_covering_hold_stands_down(world: World) -> None:
    world.hold = True
    assert active()


def test_missing_package_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_standdown, "holds", None)
    assert not active()
    assert wait_s() == HOLD_POLL_SECONDS


def test_a_raising_holds_fails_closed_and_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(*_a: object, **_k: object) -> bool:
        msg = "corrupt holds.json"
        raise ValueError(msg)

    monkeypatch.setattr(_standdown, "holds", SimpleNamespace(covers=boom))
    assert not active()
    assert "holds unavailable" in caplog.text
    assert "corrupt holds.json" in caplog.text


def test_wait_follows_next_change(world: World) -> None:
    world.hold_ends_in = 7.5
    assert 6 < wait_s() <= 8.5


def test_wait_is_capped_so_a_clock_jump_is_caught(world: World) -> None:
    world.hold_ends_in = 3 * 3600
    assert wait_s() == HOLD_POLL_SECONDS


def test_wait_has_a_floor(world: World) -> None:
    world.hold_ends_in = 0.0
    assert wait_s() == 1.0


def test_wait_without_a_next_change_polls(world: World) -> None:
    world.hold_ends_in = None
    assert wait_s() == HOLD_POLL_SECONDS


def test_wait_survives_a_bad_next_change(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(_now: object) -> object:
        msg = "naive vs aware"
        raise TypeError(msg)

    monkeypatch.setattr(_standdown, "holds", SimpleNamespace(next_change=boom))
    assert wait_s() == HOLD_POLL_SECONDS
    assert "holds unavailable" in caplog.text


def test_load_returns_the_module(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(importlib, "import_module", lambda _name: sentinel)
    assert load_holds() is sentinel


def test_load_failure_is_logged_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def missing(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", missing)
    assert load_holds() is None
    assert "cannot import holds" in caplog.text
