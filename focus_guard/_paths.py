# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Every on-disk location focus-guard reads, and the stamps that hold it."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING

from focus_project._paths import evidence_dir
from gatelock.morning_session import (
    MORNING_RETRY_SECONDS,
    MORNING_SESSION_FILE,
    MorningSkip,
    morning_skip,
)
from gatelock.night_lockdown import NIGHT_LOCKDOWN_STAMP, evening_lockdown_today

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "DATA_VAR",
    "MORNING_RETRY_SECONDS",
    "ROOT_VAR",
    "Paths",
    "focus_data_dir",
    "gate_hold",
    "paths",
    "set_override",
]

ROOT_VAR = "FOCUS_GUARD_ROOT"
DATA_VAR = "FOCUS_PROJECT_DATA"


@dataclass(frozen=True)
class Paths:
    """Data dir to watch, the stamps that hold the gate, and where screenshots are.

    ``pick_dirs`` are searched for the rules screenshot, newest first.
    """

    watch_dir: Path
    morning_session: Path
    night_lockdown: Path
    pick_dirs: tuple[Path, ...] = ()
    evidence_dir: Path | None = None
    """Where other processes (tutor) append milestone evidence; None = the
    ``evidence`` subdirectory of ``watch_dir``."""

    @property
    def evidence_watch_dir(self) -> Path:
        """The directory whose writes can complete a milestone."""
        return self.evidence_dir or self.watch_dir / "evidence"


def focus_data_dir() -> Path:
    """focus_project's data dir, resolved as its contract says."""
    override = os.environ.get(DATA_VAR)
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "focus_project"


def _default() -> Paths:
    root = os.environ.get(ROOT_VAR)
    if root:
        return Paths(
            watch_dir=focus_data_dir(),
            evidence_dir=evidence_dir(),
            morning_session=Path(root) / "morning_session.json",
            night_lockdown=Path(root) / "locked_at_epoch",
            pick_dirs=(Path(root) / "pictures",),
        )
    return Paths(
        watch_dir=focus_data_dir(),
        evidence_dir=evidence_dir(),
        morning_session=MORNING_SESSION_FILE,
        night_lockdown=NIGHT_LOCKDOWN_STAMP,
        pick_dirs=(
            Path.home() / "media" / "pictures" / "Screenshots",
            Path.home() / "media" / "pictures",
            Path.home() / "Downloads",
        ),
    )


_override: dict[str, Paths] = {}


def paths() -> Paths:
    """The active locations: real, or the test suite's override."""
    return _override.get("paths") or _default()


def set_override(value: Paths | None) -> None:
    """Point every path at ``value`` (tests), or back at the real tree."""
    _override.clear()
    if value is not None:
        _override["paths"] = value


def gate_hold(
    where: Paths, *, wait: bool, sleep: Callable[[float], None] = time.sleep
) -> MorningSkip | str | None:
    """Why this arming run must not lock, or None: morning carrot, then lockdown."""
    skip = morning_skip(
        where.morning_session,
        wait=wait,
        retry_seconds=MORNING_RETRY_SECONDS,
        sleep=sleep,
    )
    if skip:
        return skip
    locked_at = evening_lockdown_today(where.night_lockdown)
    if locked_at is None:
        return None
    return f"night lockdown already locked tonight at {locked_at:%H:%M}"
