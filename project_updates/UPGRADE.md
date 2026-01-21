# Portable Upgrade Pack

Goal: you can copy `project_updates/` into *any* repo, run a single command (manually or via an LLM), and get a **project-aware** baseline upgrade (docs + boards + enforcement + tests entrypoint) without overwriting existing work.

## Use (human or LLM)

From the target repo root (where you copied `project_updates/`):

1. Preview what will change:
   - `python3 project_updates/upgrade_repo.py`
2. Apply the upgrades:
   - `python3 project_updates/upgrade_repo.py --apply`
3. Validate:
   - `bash tests/test_all.sh`

## Multi-project dev (run many repos concurrently)

If you regularly boot multiple projects at once, make sure each repo’s dev entrypoint is collision-safe:

- **Ports**: frontend and backend must auto-pick a free port when the default is occupied (IPv4 + IPv6 safe checks; don’t rely on `127.0.0.1` only).
- **Stable defaults**: when you start multiple repos at once, avoid races by deriving a per-repo default port (example: `DEV_PORT_SEED` or hashing the repo path) and *then* auto-increment if that base port is taken.
- **Frontend → backend wiring**: when the backend port changes, the frontend must explicitly target it (example: export `PUBLIC_BACKEND_URL=http://localhost:<picked_port>` before starting the frontend).
- **Backend CORS**: if the frontend port is dynamic, the backend must allow `http://localhost:<any>` and/or `http://127.0.0.1:<any>` (via an allowlist *or* an origin regex) and must expose any custom debug headers you rely on in the UI.
- **Tunnels/containers**: any long-lived Docker resources (e.g. Cloudflare tunnel containers) must have unique names per repo (or be overridable via env).

## Token + memory efficiency (avoid bureaucracy)

When you copy `project_updates/` into another repo, the goal is not to add more hoops. The goal is to reduce repeated context load for humans and LLMs:

- Keep “general context” stable and small (briefing snapshot), and only swap “specific context” when the decision focus changes.
- Prefer deterministic recaps + paired artifacts (`__decision.json` + `__response.md`) so the next session references files instead of re-sending long chat logs.

## Avoid root-owned repo artifacts (prevents git permission errors)

If you ever see errors like:
- `insufficient permission for adding an object to repository database .git/objects`
- `failed to insert into database`

It almost always means something in the repo was created as `root` (common causes: running `git`/scripts with `sudo`, or containers writing into bind-mounted folders as root).

Fix (from the repo root):
- `sudo chown -R "$(id -un)":"$(id -gn)" .git/objects .git/refs`
- `find . -maxdepth 4 -user root -print` (should be empty)

Prevention:
- Do not run `git` inside the repo with `sudo`.
- Avoid running repo scripts with `sudo` unless you’re intentionally changing ownership/permissions.

## Decision artifacts must be paired

If your repo uses decision artifacts under `development/decisions/`, keep them in pairs so they’re easy to review and discuss:

- `*__decision.json` (machine/audit artifact)
- `*__response.md` (human-readable companion)

If you already have decision JSONs without response files, generate the missing companions:

- Preview: `python3 project_updates/tools/ensure_decision_pairs.py`
- Apply: `python3 project_updates/tools/ensure_decision_pairs.py --apply`

## Publish new learnings (keeps the system updating itself)

- `bash project_updates/tools/new_revision.sh workflow-standards`
- `bash project_updates/tools/new_revision.sh project-upgrade-prompt`

Then edit the new `project_updates/*__rN.md` file and commit it (plus the updated `project_updates/README.md`).
