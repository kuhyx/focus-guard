# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The real ``holds`` package against a scratch data file (the contract)."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from typing import TYPE_CHECKING

from focus_guard import _standdown

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write(path: Path, start: datetime, end: datetime) -> None:
    row = {
        "id": "t",
        "start": start.isoformat(timespec="minutes"),
        "end": end.isoformat(timespec="minutes"),
        "reason": "contract test",
        "created": start.isoformat(),
    }
    path.write_text(json.dumps({"holds": [row]}))


def test_real_holds_cover_now_and_end_the_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "holds.json"
    monkeypatch.setenv("HOLDS_DATA", str(data))
    monkeypatch.setattr(_standdown, "holds", _standdown.load_holds())
    now = datetime.now().astimezone().replace(tzinfo=None)
    assert not _standdown.active()
    _write(data, now - timedelta(hours=1), now + timedelta(minutes=2))
    assert _standdown.active()
    assert 1 <= _standdown.wait_s() <= _standdown.HOLD_POLL_SECONDS
    _write(data, now + timedelta(hours=1), now + timedelta(hours=2))
    assert not _standdown.active()


def test_a_corrupt_file_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "holds.json"
    data.write_text("{not json")
    monkeypatch.setenv("HOLDS_DATA", str(data))
    monkeypatch.setattr(_standdown, "holds", _standdown.load_holds())
    assert not _standdown.active()
