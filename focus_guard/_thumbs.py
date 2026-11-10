# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Recent pictures as tappable thumbnails: the lock window's file picker.

A picker inside the grabbed window, because a separate file-dialog toplevel
can open behind an override-redirect lock. Tk 8.6 decodes PNG/GIF only; any
other picture (or one too large to decode quickly) shows as a file glyph.
"""

from __future__ import annotations

import logging
from pathlib import Path
import tkinter as tk
from typing import TYPE_CHECKING, Final

from focus_guard import _icons

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_logger: Final = logging.getLogger(__name__)
SUFFIXES: Final = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})
LIMIT: Final = 6
MAX_BYTES: Final = 8_000_000
WIDTH: Final = 480
HEIGHT: Final = 300
_PALETTE: Final = _icons.PALETTE


def recent_pictures(folders: Iterable[Path]) -> list[Path]:
    """The newest non-empty pictures across ``folders`` (a missing one is skipped)."""
    found: list[tuple[float, Path]] = []
    for folder in folders:
        try:
            entries = list(folder.iterdir())
        except OSError:
            _logger.warning("picture folder %s unreadable, skipped", folder)
            continue
        for path in entries:
            try:
                info = path.stat()
            except OSError:
                _logger.warning("cannot stat %s, not offered", path)
                continue
            if path.suffix.lower() in SUFFIXES and path.is_file() and info.st_size:
                found.append((info.st_mtime, path))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return [path for _, path in found[:LIMIT]]


_IMAGES: dict[str, tk.PhotoImage] = {}
"""Tk drops an image nobody references: keep each thumbnail until its canvas dies."""
_PATH_TAG: Final = "path:"


def path_of(widget: tk.Misc) -> Path | None:
    """The picture a thumbnail canvas stands for, or None for any other widget."""
    if not isinstance(widget, tk.Canvas):
        return None
    for item in widget.find_all():
        for tag in widget.gettags(item):
            if tag.startswith(_PATH_TAG):
                return Path(tag.removeprefix(_PATH_TAG))
    return None


def _load(master: tk.Misc, path: Path) -> tk.PhotoImage | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        full = tk.PhotoImage(master=master, file=str(path))
    except OSError, tk.TclError:
        _logger.warning("cannot decode %s, showing a glyph", path)
        return None
    step = max(1, -(-full.width() // WIDTH), -(-full.height() // HEIGHT))
    return full.subsample(step) if step > 1 else full


def thumb(
    parent: tk.Misc,
    path: Path,
    command: Callable[[], None],
    *,
    selected: bool,
    name: str,
) -> tk.Canvas:
    """One picture, scaled down (or a file glyph when Tk cannot decode it)."""
    canvas = _icons.make_tap(parent, WIDTH, command, name=name)
    canvas.configure(
        width=WIDTH,
        height=HEIGHT,
        highlightthickness=6,
        highlightbackground=_PALETTE.accent if selected else _PALETTE.field_bg,
    )
    image = _load(canvas, path)
    if image is None:
        half = HEIGHT // 2
        _icons.draw(
            canvas, "file", half, _PALETTE.muted, (WIDTH / 2 - half / 2, half / 2)
        )
    else:
        canvas.create_image(WIDTH // 2, HEIGHT // 2, image=image)
        _IMAGES[str(canvas)] = image
        canvas.bind("<Destroy>", lambda _e: _IMAGES.pop(str(canvas), None), add="+")
    canvas.addtag_all(f"{_PATH_TAG}{path}")
    return canvas
