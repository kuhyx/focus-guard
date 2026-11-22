# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
import tkinter as tk
from typing import TYPE_CHECKING

import pytest

from focus_guard import _glyphs, _icons

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    window = tk.Tk()
    yield window
    window.destroy()


@pytest.mark.parametrize("glyph", sorted(_glyphs.GLYPHS))
def test_every_glyph_draws_shapes_and_no_text(root: tk.Tk, glyph: str) -> None:
    canvas = _icons.hero(root, glyph, 96, color="#fff", name="hero")
    kinds = {str(canvas.type(item)) for item in canvas.find_all()}
    assert kinds
    assert "text" not in kinds
    assert canvas.winfo_name() == "hero"


def test_a_tap_runs_the_command_by_click_space_and_return(root: tk.Tk) -> None:
    calls: list[int] = []
    button = _icons.icon_button(root, "ok", lambda: calls.append(1), name="ok")
    button.pack()
    root.update()
    button.event_generate("<Button-1>")
    button.focus_force()
    root.update()
    for key in ("<Return>", "<KP_Enter>", "<space>"):
        button.event_generate(key)
    assert calls == [1, 1, 1, 1]


def test_an_unnamed_button_still_gets_a_name(root: tk.Tk) -> None:
    button = _icons.icon_button(root, "ok", lambda: None)
    assert button.winfo_name()


@pytest.mark.parametrize("word", _icons.TIPS.values())
def test_tip_words_are_single_and_short(word: str) -> None:
    assert word.isalpha() and len(word) <= 20


def _tips(top: tk.Misc) -> list[tk.Label]:
    return [
        w
        for w in top.winfo_children()
        if isinstance(w, tk.Label) and w.winfo_name() == "tip"
    ]


def test_hover_places_the_tip_inside_the_lock_window(root: tk.Tk) -> None:
    # A separate Toplevel sinks under gatelock's lift loop; a child of the
    # lock window rides on top of it.
    root.geometry("800x600+0+0")
    frame = tk.Frame(root)
    frame.pack()
    canvas = _icons.icon_button(frame, "recheck", lambda: None)
    canvas.pack()
    root.update()
    canvas.event_generate("<Enter>", x=1, y=1)
    root.update()
    assert not [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
    (tip,) = _tips(root)
    assert tip.cget("text") == "Recheck"
    assert tip.winfo_manager() == "place"
    assert tip.winfo_ismapped()
    canvas.event_generate("<Leave>")
    root.update()
    assert not _tips(root)


def test_the_tip_uses_the_lock_font(root: tk.Tk) -> None:
    canvas = _icons.icon_button(root, "trip", lambda: None)
    canvas.pack()
    root.update()
    canvas.event_generate("<Enter>", x=1, y=1)
    root.update()
    (tip,) = _tips(root)
    font = root.tk.splitlist(tip.cget("font"))
    assert tuple(map(str, font)) == tuple(map(str, _icons.TIP_FONT))


def test_the_tip_follows_the_pointer_and_stays_inside(root: tk.Tk) -> None:
    root.geometry("400x400+0+0")
    canvas = _icons.icon_button(root, "trip", lambda: None)
    canvas.place(x=150, y=150)
    root.update()
    canvas.event_generate("<Enter>", x=1, y=1)
    canvas.event_generate("<Motion>", x=239, y=239)
    root.update()
    (tip,) = _tips(root)
    assert tip.winfo_x() + tip.winfo_width() <= root.winfo_width()
    assert tip.winfo_y() + tip.winfo_height() <= root.winfo_height()


def test_destroying_the_button_drops_its_tip(root: tk.Tk) -> None:
    canvas = _icons.icon_button(root, "trip", lambda: None)
    canvas.pack()
    root.update()
    canvas.event_generate("<Enter>", x=1, y=1)
    root.update()
    canvas.destroy()
    root.update()
    assert not _tips(root)


def test_a_glyph_without_a_tip_shows_nothing_on_hover(root: tk.Tk) -> None:
    canvas = _icons.icon_button(root, "rules", lambda: None)
    canvas.pack()
    root.update()
    canvas.event_generate("<Enter>", x=1, y=1)
    root.update()
    assert not _tips(root)
