#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> str:
    try:
        out = subprocess.check_output(cmd, cwd=str(cwd), stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        return f"(error running {' '.join(cmd)}: {exc})"


def _read_stdin_note() -> str:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        return sys.stdin.read().strip()
    except Exception:
        return ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write an end-of-session artifact under development/session_artifacts/")
    parser.add_argument("--note", default="", help="Optional note (e.g., paste the assistant's final response).")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d__%H%MZ")
    out_dir = root / "development" / "session_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}__session.md"

    note = (args.note or "").strip() or _read_stdin_note()

    head = _run(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    status = _run(["git", "status", "-sb"], cwd=root)
    diff_stat = _run(["git", "diff", "--stat"], cwd=root)

    # Inline a brief status snapshot (same output as tools/status.py).
    status_snapshot = _run([sys.executable, str(root / "tools" / "status.py")], cwd=root)

    body = []
    body.append(f"# Session Artifact ({ts})")
    body.append("")
    body.append("## Snapshot")
    body.append(f"- UTC: `{ts}`")
    body.append(f"- HEAD: `{head}`")
    body.append("")
    body.append("## Status (brief)")
    body.append("```")
    body.append(status_snapshot)
    body.append("```")
    body.append("")
    body.append("## Git Status")
    body.append("```")
    body.append(status)
    body.append("```")
    body.append("")
    body.append("## Git Diff (stat)")
    body.append("```")
    body.append(diff_stat or "(no diff)")
    body.append("```")
    body.append("")
    body.append("## Notes / Final Response")
    if note:
        body.append(note)
    else:
        body.append("(paste the assistant's final response here, or run `python3 tools/close_session.py --note \"...\"`)")
    body.append("")

    out_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

