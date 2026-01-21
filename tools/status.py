#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _extract_section(text: str, header: str) -> str:
    # Match a markdown section by exact header line, return until next ## header.
    pattern = re.compile(rf"(?m)^##\s+{re.escape(header)}\s*$")
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"(?m)^##\s+", text[start:])
    end = start + (nxt.start() if nxt else len(text[start:]))
    return text[start:end].strip()


def _top_decisions(decision_board: str, n: int = 4) -> list[str]:
    quick = _extract_section(decision_board, "Decide-now quick pick (top 4)")
    out: list[str] = []
    if quick:
        for line in quick.splitlines():
            line = line.strip()
            m = re.match(r"^\d+\.\s+\*\*(D\d+\s+—\s+.+?)\*\*\s*$", line)
            if m:
                out.append(m.group(1).strip())
            if len(out) >= n:
                return out

    decide_now = _extract_section(decision_board, "Decide Now (blocks clean MVP)")
    if decide_now:
        for line in decide_now.splitlines():
            line = line.strip()
            if line.startswith("### D") and "—" in line:
                out.append(line.lstrip("# ").strip())
                if len(out) >= n:
                    return out
    return out[:n]


def _active_work_rows(task_board: str) -> list[str]:
    sec = _extract_section(task_board, "Active Work")
    if not sec:
        return []
    lines = [ln.rstrip() for ln in sec.splitlines() if ln.strip()]
    rows = [ln for ln in lines if ln.startswith("|")]
    # Remove header + separator if present.
    if len(rows) >= 2 and ("---" in rows[1]):
        rows = rows[2:]
    return rows


def _next_steps(task_board: str) -> list[str]:
    sec = _extract_section(task_board, "Next Logical Steps (LLM / Engineering)")
    if not sec:
        return []
    steps: list[str] = []
    for ln in sec.splitlines():
        m = re.match(r"^\s*\d+\.\s+(.*)$", ln.strip())
        if m:
            steps.append(m.group(1).strip())
    return steps


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    task_board_path = root / "development" / "task_board.md"
    decision_board_path = root / "development" / "decision-board.md"

    task_board = _read(task_board_path)
    decision_board = _read(decision_board_path)

    print("== LangHero Status ==")
    print(f"Repo root: {root}")
    print()

    print("-- Active work --")
    rows = _active_work_rows(task_board)
    if not rows:
        print("(missing)")
    else:
        for r in rows:
            print(r)
    print()

    print("-- Next steps --")
    steps = _next_steps(task_board)
    if not steps:
        print("(missing)")
    else:
        for i, s in enumerate(steps, 1):
            print(f"{i}. {s}")
    print()

    print("-- Decide now (top 4) --")
    decisions = _top_decisions(decision_board, n=4)
    if not decisions:
        print("(missing)")
    else:
        for d in decisions:
            print(f"- {d}")
    print()
    print("Docs:")
    print(f"- Task board: {task_board_path.relative_to(root)}")
    print(f"- Decision board: {decision_board_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
