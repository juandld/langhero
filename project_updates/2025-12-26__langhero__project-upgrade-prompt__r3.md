# Project Upgrade Prompt (2025-12-26 r3)

Companion:
- `project_updates/2025-12-26__langhero__workflow-standards__r3.md`

```
You are the on-call operator for this repo.

Apply the portable upgrades and make sure the repo can run concurrently with other local projects.

1) Run the portable upgrade pack
   - Preview: `python3 project_updates/upgrade_repo.py`
   - Apply: `python3 project_updates/upgrade_repo.py --apply`

2) Validate (enforced)
   - `bash tests/test_all.sh`

3) Multi-project dev check (required)
   - Confirm frontend and backend auto-pick free ports (IPv4 + IPv6 safe).
   - Confirm stable per-repo default ports (e.g. derived from repo path or `DEV_PORT_SEED`), then auto-increment if busy.
   - Confirm the frontend is explicitly wired to the chosen backend port (e.g., `PUBLIC_BACKEND_URL` or equivalent).
   - Confirm tunnels/containers have unique or configurable names.

4) Root-owned artifact check (required)
   - `find . -maxdepth 4 -user root -print` (must be empty)
   - If not empty: `sudo chown -R "$(id -un)":"$(id -gn)" .git/objects .git/refs`

5) Decision pairing check (required if the repo uses decisions)
   - Preview: `python3 project_updates/tools/ensure_decision_pairs.py`
   - Apply: `python3 project_updates/tools/ensure_decision_pairs.py --apply`

6) Record what happened
   - Update `development/task_board.md` with `Implications:` + `Validation:`

7) Context budget check (required)
   - Ensure the repo has a stable “general briefing” and a small “specific context” delta for decisions.
   - Ensure workflows don’t require reloading long chat logs; rely on paired artifacts and short recaps instead.
```
