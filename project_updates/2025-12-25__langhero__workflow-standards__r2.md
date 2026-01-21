# LangHero Workflow Standards (2025-12-25 r2)

This revision keeps the same standards as `project_updates/2025-12-25__langhero__workflow-standards.md`, and adds **end-of-session artifacts** + a **brief status view** so it’s much easier to understand what’s going on.

## Previous versions

- `project_updates/2025-12-25__langhero__workflow-standards.md`

## Additions in r2 (what made the flow easier)

### A) Brief status view (one command)

- `python3 tools/status.py`

Why:
- Operators need a “what’s going on right now?” view without scrolling multiple long docs.

Output includes:
- Active work table (from `development/task_board.md`)
- Next logical steps
- Top 4 decide-now items (from `development/decision-board.md`)

### B) End-of-session artifact (one command)

- `python3 tools/close_session.py`

Why:
- We want a durable artifact that captures the state at hand-off (git status/diff, key next steps, and optionally the assistant’s final response).

Writes:
- `development/session_artifacts/YYYY-MM-DD__HHMMZ__session.md`

Repo hygiene:
- `development/session_artifacts/` is git-ignored (except `README.md`) to avoid committing every session snapshot.

### C) “Decide now” quick pick surfaced at top of decision board

- `development/decision-board.md` now has a top section listing D1–D4 so you can decide quickly which matters most.

## Everything else (unchanged from r1)

See `project_updates/2025-12-25__langhero__workflow-standards.md` for the full list of standardized practices (docs structure, tests, demo-mode cost controls, devtools cost visibility, ingest caps, publish/share model, nav/breadcrumbs, run-state cohesion).
