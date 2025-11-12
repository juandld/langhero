#!/bin/bash
set -euo pipefail

# Ensure frontend deps are installed
if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm is required to run the frontend. Install Node.js/npm first." >&2
    exit 1
fi

if [ ! -d frontend/node_modules ]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

FRONTEND_PID=""
BACKEND_PID=""

cleanup() {
    trap - EXIT INT TERM
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        pkill -P "$FRONTEND_PID" >/dev/null 2>&1 || true
        kill "$FRONTEND_PID" >/dev/null 2>&1 || true
        wait "$FRONTEND_PID" >/dev/null 2>&1 || true
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        pkill -P "$BACKEND_PID" >/dev/null 2>&1 || true
        kill "$BACKEND_PID" >/dev/null 2>&1 || true
        wait "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM

echo "Starting frontend dev server..."
pushd frontend >/dev/null
npm run dev &
FRONTEND_PID=$!
popd >/dev/null

echo "Starting backend dev server..."
(cd backend && ./dev.sh) &
BACKEND_PID=$!

wait "$BACKEND_PID"
status=$?
wait "$FRONTEND_PID" >/dev/null 2>&1 || true
exit $status
