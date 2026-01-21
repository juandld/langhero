# Tools (Local Operator Helpers)

These scripts make it easier to see “what’s going on” and to capture a clean end-of-session artifact.

## Quick status

- `python3 tools/status.py`

Prints:
- Active work (from `development/task_board.md`)
- Next logical steps
- Top 4 “Decide now” founder decisions

## Close a session (writes an artifact file)

- `python3 tools/close_session.py`

Optionally paste the assistant’s final response into the artifact:

- `python3 tools/close_session.py --note "…" `
- `python3 tools/close_session.py < response.txt`

Artifacts are written under `development/session_artifacts/`.

