# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""What every milestone form shares: state, context, and word-free widgets.

Every tap goes through :func:`run`: accepted evidence re-evaluates the lock
(``ctx.done``), a refusal tints the hero (``ctx.fail``); the lock itself
decides when to close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import tkinter as tk
from typing import TYPE_CHECKING, Final

from focus_guard import _icons

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date, datetime
    from pathlib import Path

    from focus_guard._verdict import Verdict

PALETTE: Final = _icons.PALETTE
_ENTRY_FONT: Final = ("Arial", 56)


@dataclass
class State:
    """What the forms share across outputs; the panel owns the one instance."""

    pictures: list[Path] = field(default_factory=list)
    chosen: Path | None = None
    trip: bool = False
    span: tuple[date, ...] = ()
    slot_entered: bool = False
    dot: bool | None = None
    error: bool = False


@dataclass
class Ctx:
    """Everything a form needs, injected by the panel (and by tests)."""

    verdict: Verdict
    entry: tk.StringVar
    now: Callable[[], datetime]
    pick_dirs: tuple[Path, ...]
    state: State
    rerender: Callable[[], None]
    done: Callable[[], None]
    fail: Callable[[], None]
    entries: list[tk.Entry] = field(default_factory=list)

    @property
    def project(self) -> str:
        """The interview project's id."""
        return self.verdict.project_id

    @property
    def milestone(self) -> str:
        """The missed milestone's id."""
        return self.verdict.milestone


def run(
    ctx: Ctx, work: Callable[[], bool], after: Callable[[], None] | None = None
) -> None:
    """Do ``work``; accepted: ``after`` then re-evaluate, refused: tint the hero."""
    if not work():
        ctx.fail()
        return
    if after is not None:
        after()
    ctx.done()


def row(parent: tk.Misc) -> tk.Frame:
    """A packed horizontal strip for buttons."""
    strip = tk.Frame(parent, bg=PALETTE.bg)
    strip.pack(pady=16)
    return strip


def button(
    strip: tk.Misc,
    glyph: str,
    command: Callable[[], None],
    *,
    name: str = "",
    color: str = PALETTE.fg,
) -> None:
    """A glyph button in ``strip``, named after its glyph unless told otherwise."""
    _icons.icon_button(strip, glyph, command, color=color, name=name or glyph).pack(
        side="left", padx=24
    )


def ok(strip: tk.Misc, command: Callable[[], None]) -> None:
    """The tick that sends what the form holds."""
    button(strip, "ok", command, color=PALETTE.success)


def entry(parent: tk.Misc, ctx: Ctx, submit: Callable[[], None]) -> None:
    """The typed field (shared across outputs); Return sends."""
    box = tk.Entry(
        parent,
        textvariable=ctx.entry,
        width=18,
        justify="center",
        font=_ENTRY_FONT,
        bg=PALETTE.field_bg,
        fg=PALETTE.fg,
        insertbackground=PALETTE.accent,
        highlightthickness=3,
        highlightbackground=PALETTE.field_bg,
        highlightcolor=PALETTE.accent,
        relief="flat",
        name="entry",
    )
    box.bind("<Return>", lambda _e: submit())
    box.bind("<KP_Enter>", lambda _e: submit())
    box.pack(pady=16)
    ctx.entries.append(box)
