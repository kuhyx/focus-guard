# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Decide, and lock only when owed (unreadable registry: fail open, logged)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Final

from gatelock import wait_for_x_server

from focus_guard import _standdown
from focus_guard._lock import FocusGuardLock
from focus_guard._paths import gate_hold
from focus_guard._verdict import decide, local_today

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    from focus_guard._paths import Paths
    from focus_guard._verdict import Verdict

__all__ = ["run_gate", "verdict_for"]

_logger: Final = logging.getLogger(__name__)
_UNREADABLE: Final = "registry unreadable"
_READ_ERRORS: Final = (OSError, ValueError)


def verdict_for(
    today: date | None = None, *, honor_hold: bool = True
) -> Verdict | None:
    """The verdict, or None (logged) when the registry cannot be read."""
    try:
        return decide(today or local_today(), honor_hold=honor_hold)
    except _READ_ERRORS:
        _logger.exception("cannot read the focus project, not locking")
        return None


def _owed_after_hold(today: date | None) -> bool:
    owed = verdict_for(today, honor_hold=False)
    return owed is not None and owed.locked


def _owes_another(shown: Verdict, today: date | None) -> bool:
    """A different lock is owed now (the next missed milestone, say)."""
    nxt = verdict_for(today)
    return nxt is not None and nxt.locked and nxt.milestone != shown.milestone


def _lock_once(
    paths: Paths, verdict: Verdict, *, production: bool, today: date | None
) -> None:
    hold = gate_hold(paths, wait=production)
    if hold:
        _logger.warning("not locking yet: %s; %s", verdict.reason, hold)
        return
    _logger.warning("locking: %s", verdict.reason)
    if production:
        wait_for_x_server()
    FocusGuardLock(paths, verdict, production=production, today=today).run()


def run_gate(
    paths: Paths,
    *,
    production: bool,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Lock when the verdict says so and nothing holds the gate. Exit 0.

    While a test hold is active nothing locks and an open lock lifts; when it
    ends the normal rules apply again, so a debt that is still owed re-arms.
    """
    while True:
        verdict = verdict_for(today)
        if verdict is not None and verdict.held:
            if not _owed_after_hold(today):
                _logger.info("not locking: %s and nothing owed", verdict.reason)
                return 0
            _logger.info("standing down: %s; re-judging when it ends", verdict.reason)
            while _standdown.active():
                sleep(_standdown.wait_s())
            continue
        if verdict is None or not verdict.locked:
            _logger.info("not locking: %s", verdict.reason if verdict else _UNREADABLE)
            return 0
        _lock_once(paths, verdict, production=production, today=today)
        if not _standdown.active() and not _owes_another(verdict, today):
            return 0
