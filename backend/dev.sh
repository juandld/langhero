#!/bin/bash
set -euo pipefail

# Resolve python command (prefer 3.12/3.11/3.10 automatically)
REQUESTED_BIN="${PYTHON_BIN:-}"
if [ -n "$REQUESTED_BIN" ]; then
    if ! command -v "$REQUESTED_BIN" >/dev/null 2>&1; then
        echo "Error: PYTHON_BIN='$REQUESTED_BIN' not found on PATH." >&2
        exit 1
    fi
    CANDIDATES=("$REQUESTED_BIN")
else
    CANDIDATES=("python3.12" "python3.11" "python3.10" "python3" "python")
fi

PYTHON_BIN=""
PY_VERSION=""
LOWEST_BIN=""
LOWEST_VERSION=""

for candidate in "${CANDIDATES[@]}"; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
        continue
    fi
    path=$(command -v "$candidate")
    version=$("$candidate" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        PYTHON_BIN="$path"
        PY_VERSION="$version"
        break
    fi
    if [ -z "$LOWEST_VERSION" ]; then
        LOWEST_VERSION="$version"
        LOWEST_BIN="$path"
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    if [ -n "$LOWEST_VERSION" ]; then
        echo "Error: Python 3.10+ is required. Closest found $LOWEST_VERSION at $LOWEST_BIN." >&2
    else
        echo "Error: Python 3 is required. Install python3.10+ or set PYTHON_BIN." >&2
    fi
    echo "Select a newer interpreter with PYTHON_BIN=/path/to/python3.10 ./dev.sh" >&2
    exit 1
fi

echo "Using Python $PY_VERSION at $PYTHON_BIN"

# Create virtual environment if missing
if [ -d venv ]; then
    VENV_PY="venv/bin/python"
    TARGET_ABI=$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [ ! -x "$VENV_PY" ]; then
        echo "Existing virtual environment missing python executable, recreating..."
        rm -rf venv
    else
        VENV_ABI=$("$VENV_PY" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "")
        if [ "$VENV_ABI" != "$TARGET_ABI" ]; then
            echo "Recreating virtual environment for Python $TARGET_ABI (was $VENV_ABI)..."
            rm -rf venv
        fi
    fi
fi

if [ ! -d venv ]; then
    echo "Creating Python virtual environment..."
    "$PYTHON_BIN" -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists, if not, copy from example
if [ ! -f .env ] && [ -f .env.example ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Install/update dependencies
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

# Pick a dev port (fallback if 8000 is busy)
PORT=${PORT:-8000}
PORT=$(python - <<'PY'
import socket, os
start=int(os.environ.get('PORT','8000'))
def free(p):
    s=socket.socket();
    try:
        s.bind(('127.0.0.1',p))
        s.close()
        return True
    except OSError:
        return False
p=start
for _ in range(0,50):
    if free(p):
        break
    p+=1
print(p)
PY
)
echo "Starting backend on port $PORT"
uvicorn main:app --host 0.0.0.0 --port $PORT --reload
