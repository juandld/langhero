#!/usr/bin/env python3
"""
Quick context dump for operators.

Prints the current task board and plan docs plus SOP reminders so every
session starts from the same baseline.
"""

from __future__ import annotations

import sys
from pathlib import Path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    docs = [
        ("Task Board", root / "development" / "task_board.md"),
        ("Current Plans", root / "development" / "current_plans.md"),
    ]

    print("== LangHero Instant Context ==")
    print(f"Repo root: {root}")
    print()

    for label, path in docs:
        print(f"-- {label}: {path.relative_to(root)} --")
        text = read_text(path)
        if not text:
            print("(missing)")
        else:
            print(text)
        print()

    print("Workflow reminders:")
    print("1. Log UTC start time in the task board.")
    print("2. Note active plan, queued work, and blockers.")
    print("3. Record what you run plus test results before hand-off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
