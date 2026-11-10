# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from focus_guard._paths import (
    Paths,
    focus_data_dir,
    gate_hold,
    paths,
    set_override,
)

if TYPE_CHECKING:
    import pytest


def test_nothing_holds_by_default(tmp_paths: Paths) -> None:
    assert gate_hold(tmp_paths, wait=False) is None


def test_evening_lockdown_holds(
    tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    locked_at = datetime(2026, 11, 3, 22, 30).astimezone()
    monkeypatch.setattr(
        "focus_guard._paths.evening_lockdown_today", lambda _stamp: locked_at
    )
    hold = gate_hold(tmp_paths, wait=False)
    assert isinstance(hold, str)
    assert "22:30" in hold


def test_morning_carrot_wins(tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr("focus_guard._paths.morning_skip", lambda *_a, **_k: sentinel)
    assert gate_hold(tmp_paths, wait=True) is sentinel


def test_data_dir_follows_the_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOCUS_PROJECT_DATA", str(tmp_path / "d"))
    assert focus_data_dir() == tmp_path / "d"
    monkeypatch.delenv("FOCUS_PROJECT_DATA")
    assert focus_data_dir() == Path.home() / ".local/share/focus_project"


def test_sandbox_root_has_its_own_stamps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_override(None)
    monkeypatch.setenv("FOCUS_GUARD_ROOT", str(tmp_path / "sb"))
    got = paths()
    assert got.morning_session == tmp_path / "sb" / "morning_session.json"
    assert got.night_lockdown == tmp_path / "sb" / "locked_at_epoch"


def test_real_paths_without_a_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    set_override(None)
    monkeypatch.delenv("FOCUS_GUARD_ROOT", raising=False)
    assert paths().night_lockdown.is_absolute()


def test_evidence_dir_comes_from_focus_projects_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_override(None)
    monkeypatch.delenv("FOCUS_GUARD_ROOT", raising=False)
    monkeypatch.setenv("FOCUS_PROJECT_DATA", str(tmp_path / "d"))
    assert paths().evidence_dir == tmp_path / "d" / "evidence"
    monkeypatch.setenv("FOCUS_GUARD_ROOT", str(tmp_path / "sb"))
    assert paths().evidence_dir == tmp_path / "d" / "evidence"
