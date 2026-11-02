# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The lock window's widgets: rendering only, palette from gatelock."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import TYPE_CHECKING, Final

from gatelock import LockConfig

from focus_guard import _text

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
    shared.title.set(_text.TITLE.format(name=verdict.name))
    shared.today.set(
        _text.TODAY.format(done=verdict.today_minutes, need=verdict.unlock_minutes)
    )
    shared.yesterday.set(
        _text.YESTERDAY.format(
            done=verdict.yesterday_minutes, need=verdict.daily_minutes
        )
    )
    need = max(verdict.unlock_minutes, 1)
    shared.fraction.set(min(verdict.today_minutes / need, 1.0))


def _label(
    parent: tk.Misc,
    *,
    fg: str,
    font: tuple[str, int] | tuple[str, int, str],
    var: tk.StringVar | None = None,
    text: str = "",
) -> None:
    label = tk.Label(parent, bg=_PALETTE.bg, fg=fg, font=font)
    if var is None:
        label.configure(text=text)
    else:
        label.configure(textvariable=var)
    label.pack(anchor="w", pady=(0, 16))


def build_status(parent: tk.Misc, shared: SharedVars) -> tk.Frame:
    """The read-only column every output shows; it has no input at all."""
    parent.configure({"bg": _PALETTE.bg})
    column = tk.Frame(parent, bg=_PALETTE.bg)
    column.place(relx=0.5, rely=0.5, anchor="center")
    _label(column, var=shared.title, fg=_PALETTE.accent, font=(_FONT, 32, "bold"))
    _label(column, var=shared.today, fg=_PALETTE.fg, font=(_FONT, 20))
    gauge = tk.Canvas(
        column,
        width=BAR_WIDTH,
        height=BAR_HEIGHT,
        bg=_PALETTE.field_bg,
        highlightthickness=0,
    )
    gauge.pack(anchor="w", pady=(0, 16))
    _draw_bar(gauge, shared.fraction)
    shared.fraction.trace_add("write", lambda *_a: _draw_bar(gauge, shared.fraction))
    _label(column, var=shared.yesterday, fg=_PALETTE.muted, font=(_FONT, 14))
    _label(column, text=_text.HINT, fg=_PALETTE.accent, font=(_FONT, 16))
    return column


def _draw_bar(gauge: tk.Canvas, fraction: tk.DoubleVar) -> None:
    gauge.delete("fill")
    width = int(BAR_WIDTH * fraction.get())
    gauge.create_rectangle(
        0, 0, width, BAR_HEIGHT, fill=_PALETTE.accent, width=0, tags="fill"
    )


def install_demo_close(parent: tk.Misc, on_close: Callable[[], None]) -> None:
    """A close button so a demo can never trap the developer."""
    tk.Button(parent, text=_text.DEMO_CLOSE, command=on_close).place(
        relx=0.98, rely=0.02, anchor="ne"
    )
