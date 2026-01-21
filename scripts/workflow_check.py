#!/usr/bin/env python3
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
        if re.match(r"^#{1,6}\s+", lines[i]):
            end = i
            break
    return "\n".join(lines[start:end]).strip()

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
                "Repo contains root-owned files (strict). Fix with:
"
                f"  sudo chown -R "$(id -un)":"$(id -gn)" {' '.join(root_owned[:8])}{' ...' if len(root_owned) > 8 else ''}
"
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
