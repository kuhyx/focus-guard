# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING

import pytest

from focus_guard._watch import DirWatcher

if TYPE_CHECKING:
    import threading


def _wait(event: threading.Event, seconds: float = 3.0) -> bool:
    return event.wait(seconds)


def test_write_to_a_watched_file_raises_the_flag(tmp_path: Path) -> None:
    watcher = DirWatcher(tmp_path, {"activity.jsonl"})
    try:
        (tmp_path / "activity.jsonl").write_text("{}\n")
        assert _wait(watcher.changed)
    finally:
        watcher.close()


def test_atomic_replace_is_seen(tmp_path: Path) -> None:
    watcher = DirWatcher(tmp_path, {"ledger.json"})
    try:
        staged = tmp_path / "ledger.json.tmp"
        staged.write_text("[]")
        assert not watcher.changed.is_set()
        staged.replace(tmp_path / "ledger.json")
        assert _wait(watcher.changed)
    finally:
        watcher.close()


def test_no_names_means_every_file_raises_the_flag(tmp_path: Path) -> None:
    watcher = DirWatcher(tmp_path, None)
    try:
        (tmp_path / "iv.jsonl").write_text("{}\n")
        assert _wait(watcher.changed)
    finally:
        watcher.close()


def test_other_files_are_ignored(tmp_path: Path) -> None:
    watcher = DirWatcher(tmp_path, {"activity.jsonl"})
    try:
        (tmp_path / "other.txt").write_text("x")
        time.sleep(0.3)
        assert not watcher.changed.is_set()
    finally:
        watcher.close()


def test_a_missing_directory_is_created(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    watcher = DirWatcher(target, {"x"})
    try:
        assert target.is_dir()
    finally:
        watcher.close()


def test_close_is_idempotent(tmp_path: Path) -> None:
    watcher = DirWatcher(tmp_path, {"x"})
    watcher.close()
    watcher.close()


def test_unusable_directory_falls_back_to_polling(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    watcher = DirWatcher(blocker / "sub", {"x"})
    assert not watcher.changed.is_set()
    assert "polling only" in caplog.text
    watcher.close()


class _Libc:
    def __init__(self, init: int, add: int) -> None:
        self._init, self._add = init, add

    def inotify_init1(self, _flags: int) -> int:
        return self._init

    def inotify_add_watch(self, *_args: object) -> int:
        return self._add


def test_inotify_init_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ctypes.CDLL", lambda *_a, **_k: _Libc(-1, 0))
    with pytest.raises(OSError, match="inotify_init1"):
        DirWatcher._add_watch(Path("/"))


def test_add_watch_failure_closes_the_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fd = os.open(os.devnull, os.O_RDONLY)
    monkeypatch.setattr("ctypes.CDLL", lambda *_a, **_k: _Libc(fd, -1))
    with pytest.raises(OSError, match="inotify_add_watch"):
        DirWatcher._add_watch(tmp_path)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(fd)
