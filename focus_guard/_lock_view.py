# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The lock window's widgets: rendering only, palette from gatelock.

Text-free (textgate): the only word shown is the project name kuhy typed.
Today is the big ``done / need`` pair over the bar; yesterday is the small
muted pair behind a back triangle; a drawn phone says where to work.
"""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import TYPE_CHECKING, Final

from gatelock import LockConfig

if TYPE_CHECKING:
    from collections.abc import Callable

    from focus_guard._verdict import Verdict

_PALETTE: Final = LockConfig().palette
_FONT: Final = LockConfig().typography.font_family
BAR_WIDTH: Final = 640
BAR_HEIGHT: Final = 16


@dataclass
class SharedVars:
    """Tk variables mastered on the root, so every monitor shows one state."""

    title: tk.StringVar
    today: tk.StringVar
    yesterday: tk.StringVar
    fraction: tk.DoubleVar


def make_vars(root: tk.Misc) -> SharedVars:
    """Create the shared variables once."""
    return SharedVars(
        title=tk.StringVar(master=root),
        today=tk.StringVar(master=root),
        yesterday=tk.StringVar(master=root),
        fraction=tk.DoubleVar(master=root),
    )


def fill_vars(shared: SharedVars, verdict: Verdict) -> None:
    """Show ``verdict``'s numbers."""
    shared.title.set(verdict.name)
    shared.today.set(f"{verdict.today_minutes} / {verdict.unlock_minutes}")
    shared.yesterday.set(f"◀ {verdict.yesterday_minutes} / {verdict.daily_minutes}")
    need = max(verdict.unlock_minutes, 1)
    shared.fraction.set(min(verdict.today_minutes / need, 1.0))


def _label(
    parent: tk.Misc,
    *,
    fg: str,
    font: tuple[str, int] | tuple[str, int, str],
    var: tk.StringVar,
    name: str,
) -> None:
    label = tk.Label(
        parent, name=name, bg=_PALETTE.bg, fg=fg, font=font, textvariable=var
    )
    label.pack(anchor="w", pady=(0, 16))


def _draw_phone(parent: tk.Misc) -> None:
    """A phone outline (body, screen, home dot): work there to unlock."""
    phone = tk.Canvas(
        parent, name="phone", width=40, height=64, bg=_PALETTE.bg, highlightthickness=0
    )
    accent = _PALETTE.accent
    phone.create_rectangle(2, 2, 38, 62, outline=accent, width=3, tags="body")
    phone.create_rectangle(8, 9, 32, 48, fill=accent, width=0, tags="screen")
    phone.create_oval(17, 52, 23, 58, fill=accent, width=0, tags="dot")
    phone.pack(anchor="w")


def build_status(parent: tk.Misc, shared: SharedVars) -> tk.Frame:
    """The read-only column every output shows; it has no input at all."""
    parent.configure({"bg": _PALETTE.bg})
    column = tk.Frame(parent, bg=_PALETTE.bg)
    column.place(relx=0.5, rely=0.5, anchor="center")
    title_font = (_FONT, 32, "bold")
    _label(column, var=shared.title, fg=_PALETTE.accent, font=title_font, name="title")
    _label(column, var=shared.today, fg=_PALETTE.fg, font=(_FONT, 20), name="today")
    gauge = tk.Canvas(
        column,
        name="bar",
        width=BAR_WIDTH,
        height=BAR_HEIGHT,
        bg=_PALETTE.field_bg,
        highlightthickness=0,
    )
    gauge.pack(anchor="w", pady=(0, 16))
    _draw_bar(gauge, shared.fraction)
    shared.fraction.trace_add("write", lambda *_a: _draw_bar(gauge, shared.fraction))
    muted = _PALETTE.muted
    _label(column, var=shared.yesterday, fg=muted, font=(_FONT, 14), name="yesterday")
    _draw_phone(column)
    return column


def _draw_bar(gauge: tk.Canvas, fraction: tk.DoubleVar) -> None:
    gauge.delete("fill")
    width = int(BAR_WIDTH * fraction.get())
    gauge.create_rectangle(
        0, 0, width, BAR_HEIGHT, fill=_PALETTE.accent, width=0, tags="fill"
    )


def install_demo_close(parent: tk.Misc, on_close: Callable[[], None]) -> None:
    """A close button so a demo can never trap the developer."""
    tk.Button(parent, name="close", text="✕", command=on_close).place(
        relx=0.98, rely=0.02, anchor="ne"
    )
