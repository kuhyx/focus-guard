# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""inotify on a directory, so a file replaced by rename still raises the flag."""

from __future__ import annotations

import ctypes
import logging
import os
import select
import struct
import threading
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

_logger: Final = logging.getLogger(__name__)
_IN_CLOSE_WRITE: Final = 0x00000008
_IN_MOVED_TO: Final = 0x00000080
_IN_CREATE: Final = 0x00000100
_MASK: Final = _IN_CLOSE_WRITE | _IN_MOVED_TO | _IN_CREATE
_HEADER: Final = struct.Struct("iIII")


class DirWatcher:
    """Sets :attr:`changed` when one of ``names`` (None: any file) is written."""

    def __init__(self, directory: Path, names: Collection[str] | None) -> None:
        """Start watching; on any failure the flag never fires (poll covers)."""
        self.changed = threading.Event()
        self._names = None if names is None else frozenset(names)
        self._stop_read, self._stop_write = os.pipe()
        self._fd = -1
        self._thread: threading.Thread | None = None
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self._fd = self._add_watch(directory)
        except OSError as exc:
            _logger.warning("no inotify on %s (%s): polling only", directory, exc)
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @staticmethod
    def _add_watch(directory: Path) -> int:
        libc = ctypes.CDLL(None, use_errno=True)
        fd = int(libc.inotify_init1(os.O_CLOEXEC))
        if fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        if libc.inotify_add_watch(fd, os.fsencode(directory), _MASK) < 0:
            err = ctypes.get_errno()
            os.close(fd)
            raise OSError(err, "inotify_add_watch")
        return fd

    def _run(self) -> None:
        while True:
            ready, _, _ = select.select([self._fd, self._stop_read], [], [])
            if self._stop_read in ready:
                return
            data = os.read(self._fd, 4096)
            offset = 0
            while offset < len(data):
                _wd, _mask, _cookie, size = _HEADER.unpack_from(data, offset)
                start = offset + _HEADER.size
                name = data[start : start + size].rstrip(b"\0").decode(errors="replace")
                if self._names is None or name in self._names:
                    self.changed.set()
                offset = start + size

    def close(self) -> None:
        """Stop the thread and release both descriptors. Idempotent."""
        if self._stop_write >= 0:
            os.write(self._stop_write, b"x")
        if self._thread is not None:
            self._thread.join(timeout=2)
        for fd in (self._fd, self._stop_read, self._stop_write):
            if fd >= 0:
                os.close(fd)
        self._fd = self._stop_read = self._stop_write = -1
        self._thread = None
