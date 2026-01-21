# Session Artifacts

This folder stores **end-of-session snapshots** so you can recover context quickly later (or hand off to another agent/operator).

Artifacts are created by:
- `python3 tools/close_session.py`

Each artifact includes:
- UTC timestamp + git HEAD
- brief status snapshot (active work / next steps / top decisions)
- `git status` + `git diff --stat`
- optional pasted “final response” notes

