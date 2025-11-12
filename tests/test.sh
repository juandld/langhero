#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pick_python() {
  local venv_py="$ROOT_DIR/backend/venv/bin/python"
  if [ -x "$venv_py" ]; then
    echo "$venv_py"
    return 0
  fi

  local requested="${PYTHON_BIN:-}"
  if [ -n "$requested" ]; then
    if ! command -v "$requested" >/dev/null 2>&1; then
      echo "  Error: PYTHON_BIN='$requested' not found on PATH." >&2
      return 1
    fi
    echo "$requested"
    return 0
  fi

  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  echo ""; return 1
}

echo "==> Running backend test suite"
(
  cd "$ROOT_DIR"
  PY_CMD="$(pick_python)" || { echo "  Error: Python 3.10+ is required to run tests." >&2; exit 1; }

  PY_VERSION="$($PY_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  if ! $PY_CMD -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "  Error: Python 3.10+ is required, found $PY_VERSION at $PY_CMD." >&2
    echo "  Select a newer interpreter with PYTHON_BIN=/path/to/python3.11 tests/test.sh" >&2
    exit 1
  fi

  if ! $PY_CMD -m pytest --version >/dev/null 2>&1; then
    echo "  Error: pytest is required. Install it in the active environment (see tests/requirements.txt)." >&2
    exit 1
  fi

  PYTHONPATH="$ROOT_DIR/backend:$ROOT_DIR" $PY_CMD -m pytest tests
)

echo "==> All tests passed"
