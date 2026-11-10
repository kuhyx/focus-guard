# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The milestone lock window: common panel behaviour and the rules picker."""

from __future__ import annotations

import os
import tkinter as tk
from typing import TYPE_CHECKING

import pytest

from focus_guard import _milestone_forms, _thumbs
from focus_guard._verdict import decide
from focus_guard.tests import _interview_world as iw
from focus_guard.tests._panel_ctx import (
    PHONE_NOW,
    SAT_ID,
    SUN,
    SUN_PM,
    Ctx,
    _done,
    _png,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime
    from pathlib import Path


@pytest.fixture(autouse=True)
def _world(monkeypatch: pytest.MonkeyPatch) -> iw.IWorld:
    return iw.install(monkeypatch)


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    window = tk.Tk()
    yield window
    window.destroy()


_SCENARIOS = (
    (iw.TUE, ()),
    (iw.FRI, (("rules", "file"),)),
    (PHONE_NOW, (("rules", "file"), (SAT_ID, "trip"))),
    (SUN, (("rules", "file"), (SAT_ID, "no_trip"))),
    (SUN_PM, (("rules", "file"), (SAT_ID, "no_trip"), ("mock", "score"))),
)


@pytest.mark.parametrize(("now", "setup"), _SCENARIOS)
def test_no_milestone_window_shows_any_text(
    root: tk.Tk, tmp_path: Path, now: datetime, setup: tuple[tuple[str, str], ...]
) -> None:
    _done(*setup, now=now, folder=tmp_path)
    ctx = Ctx(root, now, ())
    for widget in ctx.widgets():
        assert not isinstance(widget, tk.Label | tk.Button | tk.Message)
        if isinstance(widget, tk.Canvas) and not widget.winfo_name().startswith("day"):
            assert "text" not in {str(widget.type(i)) for i in widget.find_all()}


def test_the_hero_is_the_missed_milestones_icon(root: tk.Tk) -> None:
    ctx = Ctx(root, iw.TUE, ())
    assert ctx.milestone == "rules"
    hero = ctx.get("hero")
    assert isinstance(hero, tk.Canvas)
    assert hero.find_all()


def test_rules_lists_newest_screenshots_and_submits_the_pick(
    root: tk.Tk, tmp_path: Path
) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    old = _png(root, pics, "old.png", age=500)
    new = _png(root, pics, "new.png", age=0)
    (pics / "notes.txt").write_text("not an image")
    ctx = Ctx(root, iw.TUE, (pics, tmp_path / "missing"))
    assert ctx.pictures() == [
        new,
        old,
    ]
    assert not ctx.has("ok")
    ctx.tap("thumb1")
    ctx.tap("thumb0")
    assert ctx.has("ok")
    assert ctx.done == 0
    ctx.tap("ok")
    assert ctx.done == 1
    assert decide(iw.TUE.date(), now=iw.TUE).locked is False


def test_an_undecodable_or_huge_image_is_a_placeholder(
    root: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    (pics / "x.jpg").write_bytes(b"junk")
    _png(root, pics, "big.png", age=10)
    monkeypatch.setattr(_thumbs, "MAX_BYTES", 10)
    ctx = Ctx(root, iw.TUE, (pics,))
    assert len(ctx.pictures()) == 2
    ctx.tap("thumb0")
    assert ctx.has("ok")


def test_rules_without_pictures_can_rescan(root: tk.Tk, tmp_path: Path) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    ctx = Ctx(root, iw.TUE, (pics,))
    assert not ctx.pictures()
    _png(root, pics, "late.png")
    ctx.tap("rescan")
    assert ctx.has("thumb0")


def test_a_refused_screenshot_flashes_and_keeps_the_lock(
    root: tk.Tk, tmp_path: Path
) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    (pics / "empty.png").write_bytes(b"")
    (pics / "ok.png").write_bytes(b"x")
    os.utime(pics / "empty.png", (1, 1))
    ctx = Ctx(root, iw.TUE, (pics,))
    # The empty file is not even offered.
    assert [path.name for path in ctx.pictures()] == ["ok.png"]
    (pics / "ok.png").unlink()
    ctx.tap("thumb0")
    ctx.tap("ok")
    assert ctx.done == 0
    assert ctx.panel.error


def test_every_output_shows_the_same_state(root: tk.Tk, tmp_path: Path) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    _png(root, pics, "a.png")
    ctx = Ctx(root, iw.TUE, (pics,))
    second = ctx.add_surface()
    ctx.tap("thumb0")
    assert ctx.has("ok")
    assert ctx.get("ok", second)
    second.destroy()
    ctx.tap("thumb0")  # the dark output's frame is forgotten, not rebuilt
    assert ctx.has("ok")


def test_focus_goes_to_the_entry_when_there_is_one(root: tk.Tk, tmp_path: Path) -> None:
    _done(("rules", "file"), (SAT_ID, "no_trip"), now=SUN, folder=tmp_path)
    ctx = Ctx(root, SUN, ())
    root.update()
    ctx.panel.focus()
    assert root.focus_get() is ctx.get("entry")


def test_focus_without_an_entry_does_nothing(root: tk.Tk) -> None:
    Ctx(root, iw.TUE, ()).panel.focus()


def test_the_error_tint_clears_itself(
    root: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_milestone_forms, "FLASH_MS", 1)
    _done(("rules", "file"), (SAT_ID, "no_trip"), now=SUN, folder=tmp_path)
    ctx = Ctx(root, SUN, ())
    ctx.tap("ok")
    assert ctx.panel.error
    root.update()
    root.after(50, root.quit)
    root.mainloop()
    assert not ctx.panel.error


def test_a_dangling_picture_is_skipped_and_logged(
    root: tk.Tk, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pics = tmp_path / "pics"
    pics.mkdir()
    (pics / "ghost.png").symlink_to(pics / "nowhere.png")
    ctx = Ctx(root, iw.TUE, (pics,))
    assert not ctx.pictures()
    assert "not offered" in caplog.text


def test_a_refusal_on_a_dark_output_only_tints_the_live_ones(
    root: tk.Tk, tmp_path: Path
) -> None:
    _done(("rules", "file"), (SAT_ID, "no_trip"), now=SUN, folder=tmp_path)
    ctx = Ctx(root, SUN, ())
    ctx.add_surface().destroy()
    ctx.tap("ok")
    assert ctx.panel.error
