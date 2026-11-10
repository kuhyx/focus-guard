# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Helpers for driving a MilestonePanel on a real Tk root (xvfb-run, never :0)."""

from __future__ import annotations

import os
import tkinter as tk
from typing import TYPE_CHECKING

import focus_project

from focus_guard import _milestone_view, _thumbs
from focus_guard._verdict import decide
from focus_guard.tests import _interview_world as iw

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

SAT_ID = f"trip_ask:{iw.SATURDAY}"
SUN = iw.at("2026-11-15T09:00")
SUN_PM = iw.at("2026-11-15T13:00")
PHONE_NOW = iw.at("2026-11-13T14:00")


class Ctx:
    """One panel under test plus the calls it made."""

    def __init__(self, root: tk.Tk, now: datetime, pick_dirs: tuple[Path, ...]) -> None:
        self.root, self.now, self.done = root, now, 0
        verdict = decide(now.date(), now=now)
        assert verdict.locked
        self.milestone = verdict.milestone
        self.panel = _milestone_view.MilestonePanel(
            root,
            verdict,
            pick_dirs=pick_dirs,
            now=lambda: now,
            on_done=self._finished,
        )
        self.frame = self.add_surface()

    def _finished(self) -> None:
        self.done += 1

    def add_surface(self) -> tk.Frame:
        frame = tk.Frame(self.root, width=1200, height=900)
        frame.pack()
        self.panel.build(frame)
        return frame

    def widgets(self, parent: tk.Misc | None = None) -> list[tk.Misc]:
        found: list[tk.Misc] = []
        for child in (parent or self.frame).winfo_children():
            found.append(child)
            found.extend(self.widgets(child))
        return found

    def get(self, name: str, parent: tk.Misc | None = None) -> tk.Misc:
        (hit,) = [w for w in self.widgets(parent) if w.winfo_name() == name]
        return hit

    def has(self, name: str) -> bool:
        return any(w.winfo_name() == name for w in self.widgets())

    def tap(self, name: str) -> None:
        widget = self.get(name)
        self.root.update()
        widget.event_generate("<Button-1>")

    def pictures(self) -> list[Path]:
        found = (_thumbs.path_of(w) for w in self.widgets())
        return [path for path in found if path is not None]


def _png(root: tk.Misc, folder: Path, name: str, age: int = 0) -> Path:
    image = tk.PhotoImage(master=root, width=8, height=8)
    image.put("#336699", to=(0, 0, 8, 8))
    path = folder / name
    image.write(str(path), format="png")
    stamp = 1_700_000_000 - age
    os.utime(path, (stamp, stamp))
    return path


def _done(*pairs: tuple[str, str], now: datetime, folder: Path) -> None:
    """Complete earlier milestones (early, so none is late) so a later one is owed."""
    del now
    now = iw.TUE
    for mid, kind in pairs:
        if kind == "file":
            shot = iw.screenshot(folder)
            focus_project.record_evidence(iw.PID, mid, kind, file=shot, now=now)
        elif kind == "score":
            focus_project.record_evidence(iw.PID, mid, kind, 80, now=now)
        else:
            focus_project.answer_weekend(
                iw.PID, iw.SATURDAY, trip=kind == "trip", now=now
            )
