# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""The session guard that keeps test windows off the live display."""

from __future__ import annotations

import tkinter as tk
from typing import NoReturn

import pytest

from focus_guard.tests import _display_guard as guard

XVFB_AUTH = "/tmp/xvfb-run.AbC123/Xauthority.xYz"


@pytest.mark.parametrize(
    "env",
    [
        {"DISPLAY": ":0"},
        {"DISPLAY": ":0.0", "XAUTHORITY": "/home/u/.Xauthority"},
        {"DISPLAY": ":1", "XAUTHORITY": "/home/u/.Xauthority"},
        {"DISPLAY": ":102"},
        {"DISPLAY": ":102", "XAUTHORITY": "/tmp/other/Xauthority"},
        {"DISPLAY": ":102", "XAUTHORITY": "/home/u/xvfb-run.x/Xauthority"},
        {"DISPLAY": "host:10"},
    ],
)
def test_refuses_any_display_the_harness_did_not_start(env: dict[str, str]) -> None:
    message = guard.refusal(env)
    assert message is not None
    assert "xvfb-run" in message
    assert env["DISPLAY"] in message


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"DISPLAY": ""},
        {"DISPLAY": ":102", "XAUTHORITY": XVFB_AUTH},
    ],
)
def test_allows_no_display_or_an_xvfb_run_display(env: dict[str, str]) -> None:
    assert guard.refusal(env) is None


def test_guard_aborts_before_any_tk_root(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_root(*_a: object, **_k: object) -> NoReturn:
        msg = "a Tk root was created"
        raise AssertionError(msg)

    monkeypatch.setattr(tk, "Tk", no_root)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XAUTHORITY", "/home/u/.Xauthority")
    with pytest.raises(pytest.exit.Exception, match=r"DISPLAY=:0\b.*xvfb-run"):
        guard.enforce()
