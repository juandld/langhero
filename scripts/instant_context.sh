#!/usr/bin/env bash
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
for doc in   README.md   development/README.md   development/task_board.md   development/current_plans.md   development/decision-board.md   development/open-questions.md   development/contracts.md   development/deployment.md   development/security-audit.md   project_updates/README.md   project_updates/UPGRADE.md   ; do
  if [[ -f "$doc" ]]; then
    echo "  - $doc"
  fi
done
echo

echo "Test entrypoints:"
for cmd in   "python3 scripts/workflow_check.py --strict"   "bash tests/test_all.sh"   ; do
  echo "  - $cmd"
done
