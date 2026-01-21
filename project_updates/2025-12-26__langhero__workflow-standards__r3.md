# LangHero Workflow Standards (2025-12-26 r3)

This file captures **what changed in this project that improved the workflow**, so the same standardization can be applied to other repos.

## Context

- R3 goal: prevent “one small task consumes huge LLM context” by enforcing a context budget and separating stable context from decision-specific deltas.

## Previous versions

- `project_updates/2025-12-26__langhero__workflow-standards__r2.md`

- `project_updates/2025-12-25__langhero__workflow-standards__r8.md`

- `project_updates/2025-12-25__langhero__workflow-standards__r7.md`

## What we standardized (portable)

### 1) Fail fast if the repo contains root-owned files

Standard:
- In strict workflows, the repo must not contain root-owned files/directories (uid 0), especially under `.git/`.

Why:
- Root-owned `.git/objects` or `.git/refs` breaks basic operations (indexing, committing, sometimes even status).
- Root-owned caches in `tests/` or build artifacts create recurring “permission denied” flakiness.

How it’s enforced:
- `scripts/workflow_check.py --strict` now fails if it detects root-owned files (with a suggested `chown` fix).
- This carries through the portable upgrade pack so other repos get the same guardrail.

How to fix:
- From repo root: `sudo chown -R "$(id -un)":"$(id -gn)" .git/objects .git/refs`
- Confirm: `find . -maxdepth 4 -user root -print` (should be empty)

### 2) Stable per-repo dev ports (avoid collisions when starting many repos at once)

Standard:
- If a repo has a dev entrypoint, it must be collision-safe across many repos started at the same time.
- Port selection must be stable per repo (so concurrent boots don’t race for the same “first free” port), and must still auto-increment when busy.

Why:
- “Auto-pick a free port” alone is not enough when you start multiple repos concurrently; they can both pick the same port before either binds it.
- A stable per-repo base port reduces collisions dramatically without requiring manual port management.

How:
- Derive a per-repo port offset (examples: `DEV_PORT_SEED`, or hashing the repo path).
- Use that derived port as the default `FRONTEND_DEV_PORT` / `BACKEND_DEV_PORT` (or equivalents).
- Still probe for availability and auto-increment when the base port is occupied.
- Ensure the frontend is explicitly wired to the chosen backend port (example: export `PUBLIC_BACKEND_URL=http://localhost:<picked_backend_port>` before starting the frontend).

### 3) Context budget (avoid bureaucracy and token blowups)

Standard:
- Every recurring workflow must have a compact “general context” summary that stays stable across tasks/sessions.
- When switching focus (a different decision, thread, or subproblem), only send the small “specific context” delta.
- Treat written artifacts as memory: create/update files so the next session references the artifact instead of re-sending long chat logs.

Why:
- If a single task requires loading a giant backlog of boards, prompts, and chat logs, progress slows down and quality drops.
- A context budget forces clarity: what is stable, what changed, and what do we need next.

How:
- Use layered context in the UI and in prompts:
  - General: project briefing (state, next decisions, risks, needs clarity).
  - Specific: the chosen decision’s problem + follow-ups.
- Keep “general” deterministic (derived from docs) so it’s fast and does not spend model tokens.
- Persist decisions as paired artifacts (`__decision.json` + `__response.md`) and reference them as the canonical memory.
