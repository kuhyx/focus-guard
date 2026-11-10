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
