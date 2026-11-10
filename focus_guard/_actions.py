# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""What the milestone lock window's taps record, through focus_project.

Every function returns whether the evidence was accepted. A refusal or a
failed write is logged and the lock simply stays up (fail CLOSED): the window
re-reads the real state after each tap, it never trusts the return value to
close itself. focus_project is called through the module (patched in tests).
"""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import TYPE_CHECKING, Final

import focus_project

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

__all__ = [
    "confirm_slot",
    "recheck_phone",
    "submit_file",
    "submit_score",
    "submit_slot",
    "submit_trip",
    "tap_phone",
]

_logger: Final = logging.getLogger(__name__)
_REFUSED: Final = (ValueError, OSError, KeyError)


def _attempt(what: str, work: Callable[[], object]) -> bool:
    try:
        work()
    except _REFUSED:
        _logger.warning(
            "milestone evidence refused (%s), lock stays", what, exc_info=True
        )
        return False
    return True


def submit_file(project_id: str, milestone: str, path: Path, now: datetime) -> bool:
    """The rules screenshot."""
    return _attempt(
        milestone,
        lambda: focus_project.record_evidence(
            project_id, milestone, "file", file=path, now=now
        ),
    )


def _answer(
    project_id: str, milestone: str, span: tuple[date, date] | None, now: datetime
) -> None:
    saturday = date.fromisoformat(milestone.partition(":")[2])
    if span is not None:
        # The range first: a refused range leaves the question open.
        focus_project.add_trip(project_id, span[0], span[1], now=now)
    focus_project.answer_weekend(project_id, saturday, trip=span is not None, now=now)


def submit_trip(
    project_id: str, milestone: str, span: tuple[date, date] | None, now: datetime
) -> bool:
    """No trip (``span`` None), or a trip over the inclusive date range."""
    return _attempt(milestone, lambda: _answer(project_id, milestone, span, now))


def submit_score(project_id: str, milestone: str, text: str, now: datetime) -> bool:
    """The mock interview score, typed (a comma works as the decimal point)."""
    return _attempt(
        milestone,
        lambda: focus_project.record_evidence(
            project_id,
            milestone,
            "score",
            float(text.strip().replace(",", ".")),
            now=now,
        ),
    )


def submit_slot(project_id: str, milestone: str, text: str, now: datetime) -> bool:
    """The slot's date and time, as ``YYYY-MM-DD HH:MM``."""
    return _attempt(
        milestone,
        lambda: focus_project.record_evidence(
            project_id,
            milestone,
            "slot",
            datetime.fromisoformat(text.strip()).isoformat(),
            now=now,
        ),
    )


def confirm_slot(project_id: str, milestone: str, now: datetime) -> bool:
    """The "no other duties" tap, after the slot was entered."""
    return _attempt(
        milestone,
        lambda: focus_project.record_evidence(
            project_id, milestone, "slot_confirm", now=now
        ),
    )


def tap_phone(project_id: str, milestone: str, now: datetime) -> bool:
    """The one-time offline-ok tap."""
    return _attempt(
        milestone,
        lambda: focus_project.record_evidence(project_id, milestone, "tap", now=now),
    )


def recheck_phone(project_id: str, milestone: str, now: datetime) -> bool | None:
    """Re-run the phone check: True/False, or None when it could not run."""
    try:
        verdict: bool | None = focus_project.run_checks(project_id, now=now).get(
            milestone
        )
    except _REFUSED:
        _logger.warning("phone recheck failed for %s", project_id, exc_info=True)
        return None
    return verdict
