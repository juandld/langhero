# Project Upgrade Prompt (2025-12-28)

Companion:
- `project_updates/2025-12-28__langhero__workflow-standards.md`

Goal: a Codex instance can open this repo, read the docs, and apply the **same current process** being exercised in `narritive-hero` (decision capture, bounded-context iteration, and phone-first dev access).

```
You are the on-call operator for this repo.

Objective: bring this repo up to date with the operator workflow being used in `narritive-hero` today, without breaking LangHero’s TTS contract.

1) Read the sources of truth
   - `README.md`
   - `development/README.md`
   - `development/task_board.md`
   - `development/current_plans.md`
   - `development/decision-board.md`
   - `project_updates/README.md`
   - (cross-project context) skim `../narritive-hero/development/task_board.md` for the latest process changes.

2) Ensure the portable upgrade pack is present
   - `project_updates/UPGRADE.md`
   - `project_updates/upgrade_repo.py`
   - `project_updates/tools/*`
   - If the repo is missing shared scripts, run: `python3 project_updates/upgrade_repo.py --apply`

3) Verify dev is phone-first (tunnel-ready)
   - Prefer fast, per-session tunnels (throwaway URLs).
   - Ensure the dev entrypoints print the public frontend URL when enabled.
   - Ensure frontend uses the public backend URL when accessed via tunnel (never `localhost`).

4) Keep the TTS contract stable
   - `/api/tts` remains stable.
   - The backend respects `PORT` for dev (so orchestrators can adapt to port changes).
   - Avoid self-probing loops when doing dev service discovery (e.g., don’t “discover” your own port).

5) Validation (required)
   - `bash tests/test_all.sh`
   - If validation fails due to permissions, fix root-owned files in the repo before retrying.

6) Record what happened (required)
   - Add a new entry to `development/task_board.md` that includes:
     - UTC timestamp
     - what changed
     - `Implications:` and `Validation:`
```
