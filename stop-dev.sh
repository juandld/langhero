#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_URLS_JSON="${ROOT_DIR}/development/session_artifacts/dev_public_urls.json"

# Derive the same per-project ports that dev.sh uses
DEV_PORT_SEED="$(printf '%s' "$ROOT_DIR" | cksum | awk '{print $1}')"
PORT_OFFSET=$((DEV_PORT_SEED % 50))
DEFAULT_FE_PORT=$((5173 + PORT_OFFSET))
DEFAULT_BE_PORT=$((8000 + PORT_OFFSET))

# Prefer actual ports from the last dev session, fall back to computed defaults
FE_PORT="$DEFAULT_FE_PORT"
BE_PORT="$DEFAULT_BE_PORT"

if [ -f "$DEV_URLS_JSON" ] && command -v python3 >/dev/null 2>&1; then
  read -r SAVED_FE SAVED_BE < <(
    python3 - "$DEV_URLS_JSON" <<'PY'
import json, sys, re
from urllib.parse import urlparse

path = sys.argv[1]
try:
    data = json.load(open(path, "r", encoding="utf-8"))
except Exception:
    print(""); sys.exit(0)

def port_from_url(value):
    s = (value or "").strip()
    if not s: return ""
    try:
        u = urlparse(s)
        if u.port: return str(u.port)
    except Exception: pass
    m = re.search(r":(\d+)(?:/|$)", s)
    return m.group(1) if m else ""

fe = port_from_url(str(data.get("local_frontend_url") or ""))
be = port_from_url(str(data.get("local_backend_url") or ""))
print(f"{fe} {be}")
PY
  ) || true
  [ -n "${SAVED_FE:-}" ] && FE_PORT="$SAVED_FE"
  [ -n "${SAVED_BE:-}" ] && BE_PORT="$SAVED_BE"
fi

PROJECT_NAME="$(basename "$ROOT_DIR")"
echo "Stopping ${PROJECT_NAME} dev servers (frontend :${FE_PORT}, backend :${BE_PORT}) ..."

kill_by_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    local pids=$(lsof -t -i :$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "  Killing processes on :$port -> $pids"
      kill $pids 2>/dev/null || true
      sleep 1
      kill -9 $pids 2>/dev/null || true
    else
      echo "  Nothing running on :$port"
    fi
  else
    echo "  lsof not found; skipping port kill for :$port"
  fi
}

kill_by_port "$FE_PORT"
kill_by_port "$BE_PORT"

echo "Done."
