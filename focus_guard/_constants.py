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

WATCHED_FILES: Final = frozenset({"activity.jsonl", "ledger.json"})
"""Files in the focus_project data dir whose change can lift the lock."""
