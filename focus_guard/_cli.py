# Copyright (c) 2026 Krzysztof Rudnicki. MIT License.
"""Command line: ``lock`` (the gate) and ``status`` (the verdict, read-only)."""

from __future__ import annotations

import argparse
from datetime import date
import logging
import sys
from typing import TYPE_CHECKING

from focus_guard._gate import run_gate, verdict_for
from focus_guard._paths import paths

if TYPE_CHECKING:
    from collections.abc import Sequence


def _cmd_lock(args: argparse.Namespace) -> int:
    if args.today and args.production:
        sys.stderr.write("--today is for the sandbox, not --production\n")
        return 2
    return run_gate(paths(), production=args.production, today=args.today)


def _cmd_status(args: argparse.Namespace) -> int:
    verdict = verdict_for(args.today)
    if verdict is None:
        sys.stdout.write("unreadable\n")
        return 1
    sys.stdout.write(
        f"{'locked' if verdict.locked else 'open'}: {verdict.reason}"
        f" (today {verdict.today_minutes}/{verdict.unlock_minutes},"
        f" yesterday {verdict.yesterday_minutes}/{verdict.daily_minutes})\n"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="focus-guard")
    subs = parser.add_subparsers(dest="command", required=True)
    lock = subs.add_parser("lock", help="run the gate (locks only when owed)")
    lock.add_argument("--production", action="store_true")
    status = subs.add_parser("status", help="print the verdict, never lock")
    for sub in (lock, status):
        sub.add_argument("--today", type=date.fromisoformat, default=None)
    lock.set_defaults(func=_cmd_lock)
    status.set_defaults(func=_cmd_status)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the exit status."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    result: int = args.func(args)
    return result
