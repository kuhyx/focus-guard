# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The rules, as numbers. Every threshold lives here once."""

from __future__ import annotations

from datetime import date
from typing import Final

JUDGE_FROM: Final = date(2026, 11, 2)
"""The first "yesterday" the gate judges: the first project day. Nothing
before it is owed. Move it later if the phone timer is not crediting yet."""

RANK_FOCUS_GUARD: Final = 120
"""gatelock arbitration rank: below book-guard (125) and leetcode-guard
(150), above diet-guard (100). A literal, so no gatelock release is needed."""

POLL_INTERVAL_MS: Final = 15_000
"""Backstop re-check while locked, in case an inotify event was missed."""

TICK_MS: Final = 500
"""How often the Tk thread looks at the watcher's flag (no I/O)."""

WATCHED_FILES: Final = frozenset({"activity.jsonl", "ledger.json", "projects.json"})
"""Files in the focus_project data dir whose change can lift the lock.

``projects.json`` carries weekend answers and trips. Evidence rows live in
the ``evidence`` subdirectory, watched separately (any file) so a score or
tap written by another process (tutor) lifts the lock at once."""

MILESTONE_KINDS: Final = frozenset({"rules", "trip_ask", "phone", "mock", "slot"})
"""The milestone kinds the lock window has a form for (``_milestone_forms``).
A kind focus_project adds later cannot be completed from the window, so it
locks nothing (fail open, logged) instead of stranding the user."""
