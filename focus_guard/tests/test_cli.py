# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from datetime import date, timedelta
import runpy
from typing import TYPE_CHECKING

import pytest

from focus_guard import _cli
from focus_guard.tests._days import DAY

if TYPE_CHECKING:
    from focus_guard.tests.conftest import World


def test_status_prints_locked_with_numbers(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.short_yesterday().minutes[DAY] = 7
    assert _cli.main(["status", "--today", DAY.isoformat()]) == 0
    out = capsys.readouterr().out
    assert out.startswith("locked: yesterday fell short")
    assert "today 7/30" in out
    assert "yesterday 10/120" in out


def test_status_open(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    world.minutes[DAY - timedelta(days=1)] = 120
    assert _cli.main(["status", "--today", DAY.isoformat()]) == 0
    assert capsys.readouterr().out.startswith("open:")


def test_status_unreadable_exits_1(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.broken = OSError("disk")
    assert _cli.main(["status", "--today", DAY.isoformat()]) == 1
    assert capsys.readouterr().out == "unreadable\n"


def test_lock_passes_the_options_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(_paths: object, *, production: bool, today: date | None) -> int:
        seen.update(production=production, today=today)
        return 0

    monkeypatch.setattr(_cli, "run_gate", fake_run)
    assert _cli.main(["lock", "--today", "2026-11-04"]) == 0
    assert seen == {"production": False, "today": DAY}
    assert _cli.main(["lock", "--production"]) == 0
    assert seen == {"production": True, "today": None}


def test_today_is_refused_in_production(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _cli.main(["lock", "--production", "--today", "2026-11-04"]) == 2
    assert "sandbox" in capsys.readouterr().err


def test_module_entry_point_exits_with_main_status(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["focus_guard", "status", "--today", "2026-11-04"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("focus_guard", run_name="__main__")
    assert exit_info.value.code == 0
