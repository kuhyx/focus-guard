# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""One form per milestone kind: icons and fields, never a word.

A form fills the column under the hero icon (see :mod:`focus_guard._form_kit`
for the shared state and the tap plumbing).
"""

from __future__ import annotations

from datetime import date
from functools import partial
import tkinter as tk
from typing import TYPE_CHECKING, Final

from focus_guard import _actions, _daygrid, _thumbs
from focus_guard._form_kit import PALETTE, button, entry, ok, row, run

if TYPE_CHECKING:
    from pathlib import Path

    from focus_guard._form_kit import Ctx

FLASH_MS: Final = 600
_THUMB_COLUMNS: Final = 3
_FULL_RANGE: Final = 2


def _rescan(ctx: Ctx) -> None:
    ctx.state.pictures = _thumbs.recent_pictures(ctx.pick_dirs)
    ctx.state.chosen = None
    ctx.rerender()


def _choose(ctx: Ctx, path: Path) -> None:
    ctx.state.chosen = path
    ctx.rerender()


def rules(frame: tk.Misc, ctx: Ctx) -> None:
    """Pick the screenshot of the rules; tick to send it."""
    shelf = tk.Frame(frame, bg=PALETTE.bg)
    shelf.pack()
    for index, path in enumerate(ctx.state.pictures):
        cell = _thumbs.thumb(
            shelf,
            path,
            partial(_choose, ctx, path),
            selected=path == ctx.state.chosen,
            name=f"thumb{index}",
        )
        cell.grid(
            row=index // _THUMB_COLUMNS, column=index % _THUMB_COLUMNS, padx=8, pady=8
        )
    buttons = row(frame)
    button(buttons, "recheck", lambda: _rescan(ctx), name="rescan")
    chosen = ctx.state.chosen
    if chosen is not None:
        ok(
            buttons,
            lambda: run(
                ctx,
                lambda: _actions.submit_file(
                    ctx.project, ctx.milestone, chosen, ctx.now()
                ),
            ),
        )


def _answer_no(ctx: Ctx) -> None:
    run(
        ctx,
        lambda: _actions.submit_trip(ctx.project, ctx.milestone, None, ctx.now()),
    )


def _go(ctx: Ctx) -> None:
    ctx.state.trip = True
    ctx.rerender()


def _day(ctx: Ctx, picked: date) -> None:
    span = ctx.state.span
    if len(span) == 1:
        ctx.state.span = (min(span[0], picked), max(span[0], picked))
    else:
        ctx.state.span = (picked,)
    ctx.rerender()


def _send_trip(ctx: Ctx, span: tuple[date, date]) -> None:
    run(
        ctx,
        lambda: _actions.submit_trip(ctx.project, ctx.milestone, span, ctx.now()),
    )


def trip_ask(frame: tk.Misc, ctx: Ctx) -> None:
    """No trip, or a trip: pick the first and the last day, then tick."""
    if not ctx.state.trip:
        buttons = row(frame)
        button(buttons, "no_trip", lambda: _answer_no(ctx))
        button(buttons, "trip", lambda: _go(ctx))
        return
    saturday = date.fromisoformat(ctx.milestone.partition(":")[2])
    test_at = ctx.verdict.test_at
    window = (ctx.now().date(), test_at.date() if test_at else saturday)
    grid = _daygrid.Grid(saturday, window, ctx.state.span)
    _daygrid.build_grid(frame, grid, lambda picked: _day(ctx, picked)).pack(pady=16)
    span = ctx.state.span
    buttons = row(frame)
    button(buttons, "no_trip", lambda: _answer_no(ctx))
    if len(span) == _FULL_RANGE:
        ok(buttons, lambda: _send_trip(ctx, (span[0], span[1])))


def _recheck(ctx: Ctx) -> None:
    ctx.state.dot = _actions.recheck_phone(ctx.project, ctx.milestone, ctx.now())
    ctx.rerender()
    ctx.done()


def phone(frame: tk.Misc, ctx: Ctx) -> None:
    """The check's light, a re-run, and the offline tap."""
    light = {None: PALETTE.muted, True: PALETTE.success, False: PALETTE.danger}
    dot = tk.Canvas(
        frame, width=72, height=72, bg=PALETTE.bg, highlightthickness=0, name="dot"
    )
    dot.create_oval(6, 6, 66, 66, fill=light[ctx.state.dot], width=0)
    dot.pack(pady=16)
    buttons = row(frame)
    button(buttons, "recheck", lambda: _recheck(ctx))
    button(
        buttons,
        "offline",
        lambda: run(
            ctx,
            lambda: _actions.tap_phone(ctx.project, ctx.milestone, ctx.now()),
        ),
    )


def mock(frame: tk.Misc, ctx: Ctx) -> None:
    """The score, typed."""

    def send() -> None:
        run(
            ctx,
            lambda: _actions.submit_score(
                ctx.project, ctx.milestone, ctx.entry.get(), ctx.now()
            ),
        )

    entry(frame, ctx, send)
    ok(row(frame), send)


def _entered(ctx: Ctx) -> None:
    ctx.state.slot_entered = True
    ctx.rerender()


def slot(frame: tk.Misc, ctx: Ctx) -> None:
    """The slot's date and time, then the "no other duties" tap."""
    if ctx.state.slot_entered:
        button(
            row(frame),
            "calendar_ok",
            lambda: run(
                ctx,
                lambda: _actions.confirm_slot(ctx.project, ctx.milestone, ctx.now()),
            ),
            name="confirm",
            color=PALETTE.success,
        )
        return

    def send() -> None:
        run(
            ctx,
            lambda: _actions.submit_slot(
                ctx.project, ctx.milestone, ctx.entry.get(), ctx.now()
            ),
            lambda: _entered(ctx),
        )

    entry(frame, ctx, send)
    ok(row(frame), send)


FORMS: Final = {
    "rules": rules,
    "trip_ask": trip_ask,
    "phone": phone,
    "mock": mock,
    "slot": slot,
}
