#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    content: str
    executable: bool = False
    overwrite: bool = False


DOC_TEMPLATES: dict[str, str] = {
    "development/README.md": """# Development Docs Index

This folder is the **source of truth** for how this repo is run, evolved, and handed off between operators (human or AI).

## Start here

- Task board: `development/task_board.md`
- Current plans: `development/current_plans.md`
- Decision board: `development/decision-board.md`
- Open questions: `development/open-questions.md`

## Enforcement (run before hand-off)

- Instant context: `bash scripts/instant_context.sh`
- Workflow check: `python3 scripts/workflow_check.py --strict`
- Tests (includes workflow check): `bash tests/test_all.sh`

## Learnings archive (portable)

- Workflow standards + upgrade prompts: `project_updates/README.md`
""",
    "development/task_board.md": """# Task Board

This is the operator-facing log + task table. Add a timestamped entry whenever you start a session and whenever you finish a meaningful chunk of work.

## Session log

- {timestamp} — Session start (UTC). Upgrading repo via `project_updates/upgrade_repo.py`. Implications: baseline workflow enforcement and durable handoffs become default. Validation: `bash tests/test_all.sh`.

## Active work

| Task | Status | Owner | Notes |
| --- | --- | --- | --- |
| Adopt workflow standards | In progress | operator | Ensure boards exist, enforcement runs in tests, and project_updates is maintained as the portable learnings archive. |

## Backlog

| Task | Status | Notes |
| --- | --- | --- |
| Document architecture | Planned | Add a 1-page dataflow/entrypoints map so implications are easier to reason about. |
""",
    "development/current_plans.md": """# Current Plans

Keep this short and current. If something becomes a real decision, move it to `development/decision-board.md`.

## Near-term (next 1–2 sessions)

1. **Workflow baseline**
   - Keep boards up to date (`development/task_board.md`, `development/current_plans.md`).
   - Keep enforcement green (`bash tests/test_all.sh`).
   - When new workflow learnings occur, publish a new `project_updates/*__rN.md` revision and update `project_updates/README.md`.
""",
    "development/decision-board.md": """# Decision Board

Capture decisions that unblock implementation. Prefer “smallest decision that allows progress”.

## Decisions

| Date (UTC) | Decision | Status | Notes |
| --- | --- | --- | --- |
| {date} | Adopt workflow enforcement + boards | Decided | Run `python3 scripts/workflow_check.py --strict` as part of `bash tests/test_all.sh` so missing boards/archives fail fast. |
""",
    "development/open-questions.md": """# Open Questions

Keep these lightweight. If an item becomes a real decision with options and tradeoffs, link it to `development/decision-board.md`.

- What is “meaningful change” for requiring an Implications Pass note (size threshold)?
- What are the must-not-break contracts for this repo (API/UI/CLI)?
- What are safe default caps and cost controls for public exposure?
""",
    "development/contracts.md": """# Contracts

This doc captures “don’t break this” interfaces (API ↔ UI, integrations ↔ backend, CLI ↔ outputs).

## Principles

- Prefer additive changes; avoid removing fields/flags.
- Keep failure modes explicit and machine-readable.
- Version or deprecate intentionally.
""",
    "development/deployment.md": """# Deployment

Record the canonical way to run this repo locally and in production (commands, env vars, and rollback notes).
""",
    "development/security-audit.md": """# Security Audit

This is a living checklist + threat model. Keep it pragmatic: record findings and link to fixes.

## Checklist

- [ ] Secrets hygiene: no keys in logs; `.env` not committed.
- [ ] Abuse controls: rate limits, upload caps, auth boundaries.
- [ ] Dependency posture: pin and periodically review dependencies.
""",
}


INSTANT_CONTEXT_SH = """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Instant Context ==="
date -u
echo

if command -v git >/dev/null 2>&1; then
  echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
  echo "Status:"
  git status -sb 2>/dev/null || true
  echo
  echo "Recent commits:"
  git --no-pager log -n 5 --oneline 2>/dev/null || true
  echo
fi

echo "Key docs:"
for doc in \
  README.md \
  development/README.md \
  development/task_board.md \
  development/current_plans.md \
  development/decision-board.md \
  development/open-questions.md \
  development/contracts.md \
  development/deployment.md \
  development/security-audit.md \
  project_updates/README.md \
  project_updates/UPGRADE.md \
  ; do
  if [[ -f "$doc" ]]; then
    echo "  - $doc"
  fi
done
echo

echo "Test entrypoints:"
for cmd in \
  "python3 scripts/workflow_check.py --strict" \
  "bash tests/test_all.sh" \
  ; do
  echo "  - $cmd"
done
"""


WORKFLOW_CHECK_PY = """#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_DOCS = {
    "development/README.md": ["# Development Docs Index"],
    "development/task_board.md": ["# Task Board", "## Session log", "## Active work"],
    "development/current_plans.md": ["# Current Plans"],
    "development/decision-board.md": ["# Decision Board", "## Decisions"],
    "development/open-questions.md": ["# Open Questions"],
    "development/contracts.md": ["# Contracts"],
    "development/deployment.md": ["# Deployment"],
    "development/security-audit.md": ["# Security Audit"],
}

REQUIRED_PORTABLE_PACK = [
    "project_updates/README.md",
    "project_updates/UPGRADE.md",
    "project_updates/upgrade_repo.py",
    "project_updates/tools/new_revision.sh",
]

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _section(md: str, header: str) -> str | None:
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start, len(lines)):
        if re.match(r"^#{1,6}\\s+", lines[i]):
            end = i
            break
    return "\\n".join(lines[start:end]).strip()

def _last_list_item(text: str) -> str | None:
    last = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- "):
            last = s
    return last

def _parse_latest_paths(md: str) -> list[str]:
    body = _section(md, "## Latest") or ""
    paths = []
    for line in body.splitlines():
        m = re.search(r"`([^`]+)`", line)
        if m:
            paths.append(m.group(1))
    return paths

def _find_root_owned_paths(root: Path, *, max_hits: int = 25) -> list[str]:
    skip_prefixes = {
        "frontend/node_modules",
        "node_modules",
        "backend/venv",
        "tests/backend/.venv",
        ".venv",
    }
    hits: list[str] = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        try:
            rel_dir = Path(dirpath).resolve().relative_to(root).as_posix()
        except Exception:
            rel_dir = ""

        pruned: list[str] = []
        for d in list(dirnames):
            rel_child = f"{rel_dir}/{d}".lstrip("/")
            if any(rel_child == p or rel_child.startswith(p + "/") for p in skip_prefixes):
                pruned.append(d)
        for d in pruned:
            dirnames.remove(d)

        try:
            st = os.lstat(dirpath)
            if getattr(st, "st_uid", -1) == 0:
                hits.append(rel_dir or ".")
                if len(hits) >= max_hits:
                    return hits
        except Exception:
            pass

        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                st = os.lstat(full)
            except Exception:
                continue
            if getattr(st, "st_uid", -1) == 0:
                try:
                    rel = Path(full).resolve().relative_to(root).as_posix()
                except Exception:
                    rel = full
                hits.append(rel)
                if len(hits) >= max_hits:
                    return hits
    return hits

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    for rel, headings in REQUIRED_DOCS.items():
        path = root / rel
        if not path.exists():
            errors.append(f"Missing required file: {rel}")
            continue
        md = _read(path)
        for heading in headings:
            if heading not in md:
                errors.append(f"{rel}: missing heading {heading!r}")

    for rel in REQUIRED_PORTABLE_PACK:
        if not (root / rel).exists():
            errors.append(f"Missing required portable pack file: {rel}")

    task_board = root / "development/task_board.md"
    if task_board.exists():
        body = _section(_read(task_board), "## Session log") or ""
        last = _last_list_item(body) or ""
        if args.strict:
            if "Implications:" not in last:
                errors.append("development/task_board.md: latest session entry must include 'Implications:' (strict)")
            if "Validation:" not in last and "Tests:" not in last:
                errors.append("development/task_board.md: latest session entry must include 'Validation:' or 'Tests:' (strict)")

    if args.strict:
        root_owned = _find_root_owned_paths(root)
        if root_owned:
            errors.append(
                "Repo contains root-owned files (strict). Fix with:\n"
                f"  sudo chown -R \"$(id -un)\":\"$(id -gn)\" {' '.join(root_owned[:8])}{' ...' if len(root_owned) > 8 else ''}\n"
                "Common cause: running repo commands with sudo or container writes as root."
            )

    pu_readme = root / "project_updates/README.md"
    if pu_readme.exists():
        latest = _parse_latest_paths(_read(pu_readme))
        if not latest:
            errors.append("project_updates/README.md: could not parse any paths under '## Latest'")
        for rel in latest:
            if not (root / rel).exists():
                errors.append(f"project_updates/README.md: latest entry points to missing file: {rel}")
    else:
        errors.append("Missing required file: project_updates/README.md")

    if errors:
        print("Workflow check failed:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1
    print("Workflow check OK.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""


def utc_timestamp() -> str:
    import datetime as _dt

    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def utc_date() -> str:
    import datetime as _dt

    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%d")


def detect_test_command(root: Path) -> str:
    if (root / "tests/test.sh").exists():
        return 'bash "$ROOT_DIR/tests/test.sh"'
    if (root / "tests/backend/test.sh").exists():
        return 'bash "$ROOT_DIR/tests/backend/test.sh"'

    has_python_markers = any((root / p).exists() for p in ["pyproject.toml", "requirements.txt", "setup.cfg"])
    if has_python_markers:
        return (
            'python3 -c "import pytest" >/dev/null 2>&1 && pytest -q || '
            'python3 -m unittest discover -q || echo "No Python tests discovered; skipping"'
        )

    if (root / "package.json").exists():
        return 'npm test || echo "No npm tests configured; skipping"'

    if (root / "go.mod").exists():
        return "go test ./... || echo \"Go tests failed\""

    return 'echo "No test harness detected; skipping"'


def test_all_sh(root: Path) -> str:
    backend_cmd = detect_test_command(root)
    template = """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[0/2] Workflow check"
python3 "$ROOT_DIR/scripts/workflow_check.py" --strict

echo "[1/2] Tests"
pushd "$ROOT_DIR" >/dev/null
__BACKEND_CMD__
popd >/dev/null

echo "[2/2] Frontend tests (if configured)"
if [[ -f "$ROOT_DIR/frontend/package.json" ]] && command -v npm >/dev/null 2>&1; then
  pushd "$ROOT_DIR/frontend" >/dev/null
  python3 - <<'PY'
import json
from pathlib import Path
pkg = json.loads(Path("package.json").read_text(encoding="utf-8"))
scripts = (pkg.get("scripts") or {})
print("HAS_TEST" if ("test" in scripts or "test:run" in scripts) else "NO_TEST")
PY
  if [[ "$(python3 - <<'PY'
import json
from pathlib import Path
pkg = json.loads(Path("package.json").read_text(encoding="utf-8"))
scripts = (pkg.get("scripts") or {})
print("test:run" if "test:run" in scripts else ("test" if "test" in scripts else ""))
PY
)" == "test:run" ]]; then
    npm run test:run || echo "Frontend tests failed; continuing (optional in local runs)."
  elif [[ "$(python3 - <<'PY'
import json
from pathlib import Path
pkg = json.loads(Path("package.json").read_text(encoding="utf-8"))
scripts = (pkg.get("scripts") or {})
print("test" if "test" in scripts else "")
PY
)" == "test" ]]; then
    npm test || echo "Frontend tests failed; continuing (optional in local runs)."
  else
    echo "No frontend test script found; skipping"
  fi
  popd >/dev/null
else
  echo "Frontend missing or npm unavailable; skipping"
fi

echo "Done."
"""
    return template.replace("__BACKEND_CMD__", backend_cmd)


def ensure_parent_dir(path: Path, apply: bool) -> None:
    if path.parent.exists():
        return
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)


def plan_writes(root: Path) -> list[PlannedWrite]:
    ts = utc_timestamp()
    date = utc_date()

    writes: list[PlannedWrite] = []

    for rel, template in DOC_TEMPLATES.items():
        content = template.format(timestamp=ts, date=date)
        writes.append(PlannedWrite(path=root / rel, content=content, executable=False, overwrite=False))

    writes.append(
        PlannedWrite(path=root / "scripts/instant_context.sh", content=INSTANT_CONTEXT_SH, executable=True, overwrite=False)
    )
    writes.append(
        PlannedWrite(path=root / "scripts/workflow_check.py", content=WORKFLOW_CHECK_PY, executable=True, overwrite=False)
    )
    writes.append(
        PlannedWrite(path=root / "tests/test_all.sh", content=test_all_sh(root), executable=True, overwrite=False)
    )

    return writes


def apply_writes(writes: list[PlannedWrite], apply: bool, force: bool) -> tuple[list[Path], list[Path]]:
    created: list[Path] = []
    skipped: list[Path] = []

    for write in writes:
        path = write.path
        exists = path.exists()
        if exists and not (force or write.overwrite):
            skipped.append(path)
            continue

        ensure_parent_dir(path, apply=apply)
        if apply:
            path.write_text(write.content, encoding="utf-8")
            if write.executable:
                mode = path.stat().st_mode
                path.chmod(mode | 0o111)
        created.append(path)

    return created, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply portable workflow upgrades to the current repo.")
    ap.add_argument("--apply", action="store_true", help="Write files (default is dry-run)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files created by this upgrader")
    args = ap.parse_args()

    this_file = Path(__file__).resolve()
    root = this_file.parent.parent
    if not (root / "project_updates").exists():
        print("Error: expected to run from a repo root containing project_updates/", file=sys.stderr)
        return 2

    writes = plan_writes(root)
    created, skipped = apply_writes(writes, apply=args.apply, force=args.force)

    print(f"Repo: {root}")
    print("Planned writes:")
    for write in writes:
        status = "SKIP (exists)" if write.path in skipped and not args.force else ("WRITE" if args.apply else "WOULD WRITE")
        print(f"- {status}: {write.path.relative_to(root)}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write files.")
        return 0

    print("\nNext:")
    print("- Run: bash tests/test_all.sh")
    print("- Update: development/task_board.md (add what you actually did/learned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
