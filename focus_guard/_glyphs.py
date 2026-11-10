# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The glyph drawings: line art on a 100 x 100 grid, no text."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

    from focus_guard._icons import Pen


def _eye(pen: Pen) -> None:
    pen.curve(8, 50, 30, 28, 50, 24, 70, 28, 92, 50, 70, 72, 50, 76, 30, 72)
    pen.oval(36, 36, 64, 64)
    pen.oval(46, 46, 54, 54, fill=True)


def _suitcase(pen: Pen) -> None:
    pen.rect(12, 32, 88, 84)
    pen.rect(36, 16, 64, 32)
    pen.line(12, 56, 88, 56)
    pen.line(44, 52, 56, 52)


def _phone(pen: Pen) -> None:
    pen.rect(30, 8, 70, 92)
    pen.line(30, 22, 70, 22)
    pen.line(30, 74, 70, 74)
    pen.oval(46, 78, 54, 86)


def _webcam(pen: Pen) -> None:
    pen.oval(20, 8, 80, 68)
    pen.oval(36, 24, 64, 52)
    pen.oval(46, 34, 54, 42, fill=True)
    pen.line(50, 68, 50, 84)
    pen.line(30, 88, 70, 88)


def _calendar(pen: Pen) -> None:
    pen.rect(12, 20, 88, 88)
    pen.line(12, 40, 88, 40)
    pen.line(32, 10, 32, 28)
    pen.line(68, 10, 68, 28)
    for x in (30, 50, 70):
        for y in (54, 72):
            pen.oval(x - 3, y - 3, x + 3, y + 3, fill=True)


def _check(pen: Pen) -> None:
    pen.line(18, 54, 42, 78, 84, 26)


def _calendar_ok(pen: Pen) -> None:
    pen.rect(12, 20, 88, 88)
    pen.line(12, 40, 88, 40)
    pen.line(32, 10, 32, 28)
    pen.line(68, 10, 68, 28)
    pen.line(30, 66, 46, 80, 72, 50)


def _no_trip(pen: Pen) -> None:
    _suitcase(pen)
    pen.line(8, 92, 92, 8)


def _recheck(pen: Pen) -> None:
    pen.arc(18, 18, 82, 82, start=40, extent=280)
    pen.line(70, 14, 78, 30, 62, 32)


def _offline(pen: Pen) -> None:
    pen.arc(10, 30, 90, 110, start=50, extent=80)
    pen.arc(26, 46, 74, 94, start=50, extent=80)
    pen.oval(46, 76, 54, 84, fill=True)
    pen.line(14, 14, 86, 86)


def _file(pen: Pen) -> None:
    pen.rect(22, 10, 78, 90)
    pen.line(34, 36, 66, 36)
    pen.line(34, 54, 66, 54)


GLYPHS: Final[dict[str, Callable[[Pen], None]]] = {
    "rules": _eye,
    "trip_ask": _suitcase,
    "phone": _phone,
    "mock": _webcam,
    "slot": _calendar,
    "ok": _check,
    "calendar_ok": _calendar_ok,
    "trip": _suitcase,
    "no_trip": _no_trip,
    "recheck": _recheck,
    "offline": _offline,
    "file": _file,
}
