# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from focus_guard import _lock
from focus_guard._verdict import decide
from focus_guard.tests._days import DAY

if TYPE_CHECKING:
    from collections.abc import Callable

    from focus_guard._paths import Paths
    from focus_guard.tests.conftest import World


class FakeVar:
    def __init__(self) -> None:
        self.value: Any = None

    def set(self, value: Any) -> None:
        self.value = value


class FakeRoot:
    def __init__(self) -> None:
        self.titles: list[str] = []
        self.scheduled: list[tuple[int, Callable[[], None]]] = []

    def title(self, text: str) -> None:
        self.titles.append(text)

    def after(self, ms: int, callback: Callable[[], None]) -> None:
        self.scheduled.append((ms, callback))


class FakeWindow:
    def __init__(self, _root: object, config: Any, *, hooks: Any, arbiter: Any) -> None:
        self.config, self.hooks, self.arbiter = config, hooks, arbiter
        self.events: list[str] = []

    def setup(self) -> None:
        self.events.append("setup")

    def grab_input(self) -> None:
        self.events.append("grab")

    def run(self) -> None:
        self.events.append("run")

    def close(self) -> None:
        self.events.append("close")
        self.hooks.on_close()


class FakeArbiter:
    def __init__(self, name: str, rank: int, **kwargs: Any) -> None:
        self.name, self.rank, self.kwargs = name, rank, kwargs
        self.events: list[str] = []

    def publish(self) -> None:
        self.events.append("publish")

    def acquire_holder(self) -> None:
        self.events.append("acquire")


def arm(
    world: World, paths: Paths, *, production: bool = False
) -> _lock.FocusGuardLock:
    world.short_yesterday()
    return _lock.FocusGuardLock(paths, decide(DAY), production=production, today=DAY)


def window_of(lock: _lock.FocusGuardLock) -> FakeWindow:
    return cast("FakeWindow", lock._lock)


def shown(lock: _lock.FocusGuardLock) -> Any:
    return lock._vars


def anything(value: object) -> Any:
    return value


def tick(lock: _lock.FocusGuardLock) -> None:
    lock._tick()
