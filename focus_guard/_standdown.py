# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Stand down while a declared test hold covers now (fail CLOSED).

``holds`` is read through this module's ``holds`` attribute, so tests patch one
name. If the package cannot be imported or raises, the gate behaves exactly as
before the hold existed: the failure is logged, never treated as "held".
"""

from __future__ import annotations

from datetime import datetime
import importlib
import logging
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType

__all__ = ["GATE", "HOLD_POLL_SECONDS", "HOLD_REASON", "active", "load_holds", "wait_s"]

_logger: Final = logging.getLogger(__name__)
GATE: Final = "focus"
HOLD_REASON: Final = "a hold is active"
HOLD_POLL_SECONDS: Final = 30.0
"""Longest sleep while held: a clock jump or an edited hold is seen within it."""
_HOLD_ERRORS: Final = (
    ImportError,
    OSError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def load_holds() -> ModuleType | None:
    """Import ``holds``; None (logged) means the gate behaves as before."""
    try:
        return importlib.import_module("holds")
    except _HOLD_ERRORS:
        _logger.exception("cannot import holds, no hold will stand the gate down")
        return None


holds: ModuleType | None = load_holds()


def active() -> bool:
    """True while a hold covers now. Any failure: False, logged."""
    if holds is None:
        return False
    try:
        return bool(holds.covers(GATE))
    except _HOLD_ERRORS:
        _logger.exception("holds unavailable (%s), treating as no hold", GATE)
        return False


def wait_s() -> float:
    """Seconds to sleep before asking again: until the next change, capped."""
    if holds is None:
        return HOLD_POLL_SECONDS
    now = datetime.now().astimezone().replace(tzinfo=None)  # holds: naive local
    try:
        change = holds.next_change(now)
    except _HOLD_ERRORS:
        _logger.exception("holds unavailable (%s), polling instead", GATE)
        return HOLD_POLL_SECONDS
    if change is None:
        return HOLD_POLL_SECONDS
    left = float((change - now).total_seconds())
    return max(1.0, min(HOLD_POLL_SECONDS, left + 0.5))
