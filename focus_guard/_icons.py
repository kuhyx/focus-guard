# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Line-art glyphs on a Tk canvas, plus the icon button. No text anywhere.

Every glyph is drawn on a 100 x 100 grid and scaled, so one function serves
the hero icon and the small buttons. The palette comes from gatelock.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Final

from gatelock import LockConfig

from focus_guard._glyphs import GLYPHS

if TYPE_CHECKING:
    from collections.abc import Callable

PALETTE: Final = LockConfig().palette
GRID: Final = 100
BUTTON_SIZE: Final = 240


def _tags(*, solid: bool) -> tuple[str, ...]:
    return ("shape", "solid") if solid else ("shape",)


class Pen:
    """Draws in 0..100 grid units onto a canvas."""

    def __init__(
        self,
        canvas: tk.Canvas,
        size: int,
        color: str,
        origin: tuple[float, float] = (0, 0),
    ) -> None:
        """Bind to ``canvas``; ``size`` is the glyph's pixel width and height."""
        self.canvas = canvas
        self.origin = origin
        self.scale = size / GRID
        self.color = color
        self.width = max(2, round(size / 24))

    def _px(self, coords: tuple[float, ...]) -> list[float]:
        return [c * self.scale + self.origin[i % 2] for i, c in enumerate(coords)]

    def line(self, *coords: float) -> None:
        """A round-capped polyline."""
        self.canvas.create_line(
            *self._px(coords),
            fill=self.color,
            width=self.width,
            capstyle="round",
            joinstyle="round",
            tags=("line",),
        )

    def rect(self, *coords: float, fill: bool = False) -> None:
        """A rectangle outline, or filled."""
        self.canvas.create_rectangle(
            *self._px(coords),
            outline=self.color,
            fill=self.color if fill else "",
            width=self.width,
            tags=_tags(solid=fill),
        )

    def oval(self, *coords: float, fill: bool = False) -> None:
        """An ellipse outline, or filled."""
        self.canvas.create_oval(
            *self._px(coords),
            outline=self.color,
            fill=self.color if fill else "",
            width=self.width,
            tags=_tags(solid=fill),
        )

    def curve(self, *coords: float) -> None:
        """A smoothed closed outline."""
        self.canvas.create_polygon(
            *self._px(coords),
            outline=self.color,
            fill="",
            width=self.width,
            smooth=True,
            tags=("shape",),
        )

    def arc(self, *coords: float, start: float, extent: float) -> None:
        """An open arc."""
        self.canvas.create_arc(
            *self._px(coords),
            start=start,
            extent=extent,
            style="arc",
            outline=self.color,
            width=self.width,
            tags=("shape",),
        )


def draw(
    canvas: tk.Canvas,
    glyph: str,
    size: int,
    color: str,
    origin: tuple[float, float] = (0, 0),
) -> None:
    """Draw ``glyph`` as a ``size`` px square with its corner at ``origin``."""
    GLYPHS[glyph](Pen(canvas, size, color, origin))


def recolor(canvas: tk.Canvas, color: str) -> None:
    """Repaint every stroke (and every filled shape) of a glyph in ``color``."""
    canvas.itemconfigure("line", fill=color)
    canvas.itemconfigure("shape", outline=color)
    canvas.itemconfigure("solid", fill=color)


def hero(
    parent: tk.Misc, glyph: str, size: int, *, color: str, name: str = ""
) -> tk.Canvas:
    """A packed, non-interactive glyph on the window's background."""
    canvas = tk.Canvas(
        parent, width=size, height=size, bg=PALETTE.bg, highlightthickness=0, name=name
    )
    draw(canvas, glyph, size, color)
    canvas.pack(pady=(0, 32))
    return canvas


def make_tap(
    parent: tk.Misc,
    size: int,
    command: Callable[[], None],
    *,
    name: str = "",
    bg: str = PALETTE.field_bg,
) -> tk.Canvas:
    """A square you tap: click, Space or Return. Its focus ring is the accent."""
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=bg,
        highlightthickness=3,
        highlightbackground=bg,
        highlightcolor=PALETTE.accent,
        takefocus=True,
        cursor="hand2",
        name=name,
    )
    for event in ("<Button-1>", "<Return>", "<KP_Enter>", "<space>"):
        canvas.bind(event, lambda _e: command())
    return canvas


def icon_button(
    parent: tk.Misc,
    glyph: str,
    command: Callable[[], None],
    *,
    color: str = PALETTE.fg,
    name: str = "",
) -> tk.Canvas:
    """A glyph you tap; the caller places it."""
    canvas = make_tap(parent, BUTTON_SIZE, command, name=name)
    draw(canvas, glyph, BUTTON_SIZE, color)
    return canvas
