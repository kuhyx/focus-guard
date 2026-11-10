# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
import re
import tkinter as tk
from typing import TYPE_CHECKING

import pytest

from focus_guard import _lock_view
from focus_guard._verdict import Verdict

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    window = tk.Tk()
    yield window
    window.destroy()


def _verdict(done: int = 15) -> Verdict:
    return Verdict(
        locked=True,
        reason="r",
        name="Exam",
        today_minutes=done,
        unlock_minutes=30,
        yesterday_minutes=10,
        daily_minutes=120,
    )


def test_fill_vars_shows_the_numbers(root: tk.Tk) -> None:
    shared = _lock_view.make_vars(root)
    _lock_view.fill_vars(shared, _verdict())
    assert shared.title.get() == "Exam"
    assert shared.today.get() == "15 / 30"
    assert shared.yesterday.get() == "◀ 10 / 120"
    assert shared.fraction.get() == 0.5


_WORD = re.compile(r"[^\W\d_]{2,}")


def _shown(widget: tk.Misc) -> str:
    has_text = isinstance(widget, (tk.Label, tk.Button))
    return str(widget.cget("text")) if has_text else ""


def test_no_widget_shows_a_word_but_the_project_name(root: tk.Tk) -> None:
    shared = _lock_view.make_vars(root)
    _lock_view.fill_vars(shared, _verdict())
    _lock_view.build_status(root, shared)
    _lock_view.install_demo_close(root, lambda: None)
    shown = {w.winfo_name(): _shown(w) for w in _widgets(root)}
    assert shown.pop("title") == "Exam"
    assert len(shown) >= 5
    assert [t for t in shown.values() if _WORD.search(t)] == []


def test_fraction_is_capped_and_survives_zero_need(root: tk.Tk) -> None:
    shared = _lock_view.make_vars(root)
    _lock_view.fill_vars(shared, _verdict(done=99))
    assert shared.fraction.get() == 1.0
    zero = Verdict(locked=True, reason="r", today_minutes=0, unlock_minutes=0)
    _lock_view.fill_vars(shared, zero)
    assert shared.fraction.get() == 0.0


def _widgets(parent: tk.Misc) -> list[tk.Misc]:
    found: list[tk.Misc] = []
    for child in parent.winfo_children():
        found.append(child)
        found.extend(_widgets(child))
    return found


def test_status_column_has_no_input_and_a_live_bar(root: tk.Tk) -> None:
    shared = _lock_view.make_vars(root)
    _lock_view.fill_vars(shared, _verdict())
    column = _lock_view.build_status(root, shared)
    kinds = {type(w) for w in _widgets(column)}
    assert kinds == {tk.Label, tk.Canvas}
    phone = column.nametowidget("phone")
    assert isinstance(phone, tk.Canvas)
    assert phone.find_withtag("body")
    bar = column.nametowidget("bar")
    shared.fraction.set(0.25)
    root.update_idletasks()
    (rect,) = bar.find_withtag("fill")
    assert bar.coords(rect)[2] == _lock_view.BAR_WIDTH * 0.25


def test_demo_close_button_calls_back(root: tk.Tk) -> None:
    called: list[int] = []
    _lock_view.install_demo_close(root, lambda: called.append(1))
    button = next(w for w in _widgets(root) if isinstance(w, tk.Button))
    button.invoke()
    assert called == [1]
