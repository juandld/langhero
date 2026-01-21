#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Running backend tests"
(cd "$ROOT" && ./tests/test.sh)

echo
echo "==> Running frontend tests"
(cd "$ROOT/frontend" && npm run test:run)

echo
echo "==> All test suites passed"

