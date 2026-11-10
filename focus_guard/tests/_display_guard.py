# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Fail closed when a test session could open windows on a live display.

The Tk tests need a private X server. `xvfb-run` is the harness: it exports
its own DISPLAY plus an XAUTHORITY inside a `/tmp/xvfb-run.*` directory, which
no desktop session has. Any other DISPLAY (`:0`, `:0.0`, a remote host, a
hand-started server) is treated as live and aborts the session before a test,
and so before a Tk root, runs. No DISPLAY at all is safe: Tk just fails.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

_HARNESS_DIR_PREFIX = "xvfb-run."


def refusal(env: Mapping[str, str]) -> str | None:
    """Return the abort message when DISPLAY is not an xvfb-run display."""
    display = env.get("DISPLAY", "")
    if not display:
        return None
    auth_dir = Path(env.get("XAUTHORITY", "")).parent
    in_tmp = auth_dir.parent == Path(tempfile.gettempdir())
    if in_tmp and auth_dir.name.startswith(_HARNESS_DIR_PREFIX):
        return None
    return (
        f"refusing to run: DISPLAY={display} is not a private xvfb-run display "
        "(tests would open windows on a live desktop). "
        "Run: env -u DISPLAY xvfb-run -a <python> -m pytest ..."
    )


def enforce() -> None:
    """Abort the whole pytest session when the display is not the harness's."""
    message = refusal(os.environ)
    if message is not None:
        pytest.exit(message, returncode=2)
