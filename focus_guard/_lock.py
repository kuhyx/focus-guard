# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The lock: a gatelock consumer with no input that lets go when the numbers do.

It holds until the verdict says otherwise: a file event in the focus_project
data dir (inotify), a backstop poll, or a sick/free day or an ended project
changing the verdict. There is no typed override.
"""

from __future__ import annotations

import logging
from traceback import format_exc
from typing import TYPE_CHECKING, Final

from gatelock import (
    Arbiter,
    GateRoot,
    GrabPolicy,
    LockConfig,
    LockWindow,
    assert_not_under_pytest,
    wait_for_turn,
)

from focus_guard._constants import (
    POLL_INTERVAL_MS,
    RANK_FOCUS_GUARD,
    TICK_MS,
    WATCHED_FILES,
)
from focus_guard._lock_view import (
    build_status,
    fill_vars,
    install_demo_close,
    make_vars,
)
from focus_guard._verdict import decide, local_today
from focus_guard._watch import DirWatcher

if TYPE_CHECKING:
    from datetime import date
    import tkinter as tk

    from gatelock import SurfaceInfo

    from focus_guard._paths import Paths
    from focus_guard._verdict import Verdict

_logger: Final = logging.getLogger(__name__)


class FocusGuardLock:
    """Armed at construction; :meth:`run` blocks until the lock releases."""

    def __init__(
        self,
        paths: Paths,
        verdict: Verdict,
        *,
        production: bool,
        today: date | None = None,
    ) -> None:
        """Arm the lock. Demo mode (the default) uses a local grab."""
        assert_not_under_pytest("the focus-guard lock")
        self._today = today
        self._demo = not production
        self._closed = False
        self._polls = 0
        self._config = LockConfig(
            mode="hard",
            overrideredirect=True,
            grab=GrabPolicy(
                kind="global" if production else "local", disable_vt=production
            ),
            app_name="focus_guard",
            rank=RANK_FOCUS_GUARD,
        )
        self.root = GateRoot()
        self.root.title("Focus Guard" + ("" if production else " [DEMO]"))
        self._vars = make_vars(self.root)
        fill_vars(self._vars, verdict)
        self._watcher = DirWatcher(paths.watch_dir, WATCHED_FILES)
        arbiter = Arbiter(
            "focus_guard",
            RANK_FOCUS_GUARD,
            grab=self._config.resolved_grab(),
            disable_vt=self._config.resolved_disable_vt(),
        )
        arbiter.publish()
        if production:
            wait_for_turn(arbiter)
        arbiter.acquire_holder()
        self._lock = LockWindow(self.root, self._config, hooks=self, arbiter=arbiter)
        self._lock.setup()
        self._lock.grab_input()
        self.root.after(TICK_MS, self._tick)

    def build_surface(self, parent: tk.Misc, surface: SurfaceInfo) -> None:
        """Paint one output; every output shows the same read-only column."""
        del surface
        build_status(parent, self._vars)
        if self._demo:
            install_demo_close(parent, self.close)

    def teardown_surface(self, surface: SurfaceInfo) -> None:
        """Nothing per-surface to forget."""

    def on_focus_ready(self, surface: SurfaceInfo | None) -> None:
        """Nothing to focus: the window takes no input."""

    def on_callback_error(self) -> None:
        """A Tk callback raised: log it and keep the lock up."""
        _logger.error("a Tk callback raised inside the lock:\n%s", format_exc())

    def on_close(self) -> None:
        """Every exit path: stop the watcher."""
        self._watcher.close()

    def _tick(self) -> None:
        self._polls += TICK_MS
        due = self._polls >= POLL_INTERVAL_MS
        if self._watcher.changed.is_set() or due:
            self._watcher.changed.clear()
            self._polls = 0
            self._refresh()
        if not self._closed:
            self.root.after(TICK_MS, self._tick)

    def _refresh(self) -> None:
        today = self._today or local_today()
        try:
            verdict = decide(today)
        except (OSError, ValueError) as exc:
            _logger.warning("cannot re-check, keeping the lock: %s", exc)
            return
        if not verdict.locked:
            _logger.info("released: %s", verdict.reason)
            self.close()
            return
        fill_vars(self._vars, verdict)

    def close(self) -> None:
        """Release the lock. Idempotent."""
        if not self._closed:
            self._closed = True
            self._lock.close()

    def run(self) -> None:
        """Hand control to Tk until the lock releases."""
        self._lock.run()
