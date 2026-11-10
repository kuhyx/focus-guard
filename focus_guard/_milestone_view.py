# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The milestone lock window: the missed milestone's icon and its one action.

No text anywhere (textgate). Every output shows the same state; a tap on any
of them records the evidence, and the lock re-reads the real state to close.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Final

from focus_guard import _icons, _milestone_forms, _thumbs
from focus_guard._form_kit import Ctx, State

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import date, datetime
    from pathlib import Path

    from focus_guard._verdict import Verdict

__all__ = ["MilestonePanel"]

_PALETTE: Final = _icons.PALETTE
HERO_SIZE: Final = 360
SLOT_FORMAT: Final = "%Y-%m-%d %H:%M"


class MilestonePanel:
    """One state, drawn on every output."""

    def __init__(
        self,
        root: tk.Misc,
        verdict: Verdict,
        *,
        pick_dirs: Sequence[Path],
        now: Callable[[], datetime],
        on_done: Callable[[], None],
    ) -> None:
        """Prepare the shared state; widgets come with :meth:`build`."""
        self._root = root
        self._kind = verdict.milestone.partition(":")[0]
        # The slot entry starts at the test's own date and time.
        start = verdict.test_at
        text = start.strftime(SLOT_FORMAT) if start and self._kind == "slot" else ""
        dirs = tuple(pick_dirs)
        self._ctx = Ctx(
            verdict=verdict,
            entry=tk.StringVar(master=root, value=text),
            now=now,
            pick_dirs=dirs,
            state=State(pictures=_thumbs.recent_pictures(dirs)),
            rerender=self._render,
            done=on_done,
            fail=self._flash,
        )
        self._frames: list[tk.Frame] = []

    @property
    def error(self) -> bool:
        """Whether the last tap was refused and the tint has not cleared yet."""
        return self._ctx.state.error

    @property
    def span(self) -> tuple[date, ...]:
        """The picked trip days: none, the first, or first and last."""
        return self._ctx.state.span

    @property
    def dot(self) -> bool | None:
        """The phone check's latest verdict (None: could not run / not run)."""
        return self._ctx.state.dot

    def build(self, parent: tk.Misc) -> None:
        """Paint one output."""
        parent.configure({"bg": _PALETTE.bg})
        column = tk.Frame(parent, bg=_PALETTE.bg)
        column.place(relx=0.5, rely=0.5, anchor="center")
        self._frames.append(column)
        self._paint(column)

    def focus(self) -> None:
        """Put the keyboard in the entry, when the form has one."""
        live = [box for box in self._ctx.entries if box.winfo_exists()]
        if live:
            live[0].focus_force()

    def _paint(self, column: tk.Frame) -> None:
        for child in column.winfo_children():
            child.destroy()
        color = _PALETTE.danger if self._ctx.state.error else _PALETTE.accent
        _icons.hero(column, self._kind, HERO_SIZE, color=color, name="hero")
        _milestone_forms.FORMS[self._kind](column, self._ctx)

    def _render(self) -> None:
        self._frames = [f for f in self._frames if f.winfo_exists()]
        self._ctx.entries.clear()
        for column in self._frames:
            self._paint(column)

    def _tint(self, color: str) -> None:
        for column in self._frames:
            if column.winfo_exists():
                hero = column.nametowidget("hero")
                _icons.recolor(hero, color)

    def _flash(self) -> None:
        self._ctx.state.error = True
        self._tint(_PALETTE.danger)
        self._root.after(_milestone_forms.FLASH_MS, self._calm)

    def _calm(self) -> None:
        self._ctx.state.error = False
        self._tint(_PALETTE.accent)
