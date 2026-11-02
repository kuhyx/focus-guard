# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Decide, and lock only when owed (unreadable registry: fail open, logged)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from gatelock import wait_for_x_server

from focus_guard._lock import FocusGuardLock
from focus_guard._paths import gate_hold
from focus_guard._verdict import decide, local_today

if TYPE_CHECKING:
    from datetime import date

    from focus_guard._paths import Paths
    from focus_guard._verdict import Verdict

__all__ = ["run_gate", "verdict_for"]

_logger: Final = logging.getLogger(__name__)
_UNREADABLE: Final = "registry unreadable"
_READ_ERRORS: Final = (OSError, ValueError)


def verdict_for(today: date | None = None) -> Verdict | None:
    """The verdict, or None (logged) when the registry cannot be read."""
    try:
        return decide(today or local_today())
    except _READ_ERRORS:
        _logger.exception("cannot read the focus project, not locking")
        return None


def run_gate(paths: Paths, *, production: bool, today: date | None = None) -> int:
    """Lock when the verdict says so and nothing holds the gate. Exit 0."""
    verdict = verdict_for(today)
    if verdict is None or not verdict.locked:
        _logger.info("not locking: %s", verdict.reason if verdict else _UNREADABLE)
        return 0
    hold = gate_hold(paths, wait=production)
    if hold:
        _logger.warning("not locking yet: %s; %s", verdict.reason, hold)
        return 0
    _logger.warning("locking: %s", verdict.reason)
    if production:
        wait_for_x_server()
    lock = FocusGuardLock(paths, verdict, production=production, today=today)
    lock.run()
    return 0
