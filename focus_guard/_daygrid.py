# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""A two-week day grid for the trip range. Numerals only, no words."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import partial
import tkinter as tk
from typing import TYPE_CHECKING, Final

from focus_guard import _icons

if TYPE_CHECKING:
    from collections.abc import Callable

_PALETTE: Final = _icons.PALETTE
CELL: Final = 130
WEEKS: Final = 2
DAYS_BEFORE_SATURDAY: Final = 5
"""The grid starts on the Monday of the asked Saturday's week."""
WEEKEND_START: Final = 5


@dataclass(frozen=True)
class Look:
    """How one cell reads."""

    pickable: bool
    inside: bool
    asked: bool


@dataclass(frozen=True)
class Grid:
    """The two weeks around the asked Saturday and what is picked in them."""

    saturday: date
    window: tuple[date, date]
    """First and last pickable day."""
    span: tuple[date, ...] = ()


def day_cell(
    parent: tk.Misc, day: date, command: Callable[[], None], look: Look
) -> tk.Canvas:
    """One day: its number, tinted by weekend, range membership and pickability."""
    if look.inside:
        bg, ink = _PALETTE.accent, _PALETTE.on_fill
    else:
        weekend = day.weekday() >= WEEKEND_START
        bg = _PALETTE.field_bg if weekend else _PALETTE.bg
        ink = _PALETTE.fg if look.pickable else _PALETTE.muted
    cell = _icons.make_tap(
        parent,
        CELL,
        command if look.pickable else _nothing,
        name=f"day{day.isoformat()}",
        bg=bg,
    )
    if look.asked:
        cell.configure(highlightbackground=_PALETTE.success, highlightthickness=5)
    cell.create_text(
        CELL / 2, CELL / 2, text=str(day.day), fill=ink, font=("Arial", 40, "bold")
    )
    return cell


def _nothing() -> None:
    """The tap of a day that cannot be picked."""


def build_grid(parent: tk.Misc, grid: Grid, pick: Callable[[date], None]) -> tk.Frame:
    """Seven columns Mon..Sun, two rows; days outside the window are dim."""
    frame = tk.Frame(parent, bg=_PALETTE.bg)
    monday = grid.saturday - timedelta(days=DAYS_BEFORE_SATURDAY)
    first, last = grid.window
    low, high = (grid.span[0], grid.span[-1]) if grid.span else (None, None)
    for offset in range(7 * WEEKS):
        day = monday + timedelta(days=offset)
        look = Look(
            pickable=first <= day <= last,
            inside=low is not None and high is not None and low <= day <= high,
            asked=day == grid.saturday,
        )
        cell = day_cell(frame, day, partial(pick, day), look)
        cell.grid(row=offset // 7, column=offset % 7, padx=6, pady=6)
    return frame
