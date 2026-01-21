#!/bin/bash
set -euo pipefail

# Stop dev servers by ports (fallback utility)
FE_PORT=${FRONTEND_DEV_PORT:-5173}
BE_PORT=${BACKEND_DEV_PORT:-8000}
DEV_URLS_JSON="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/development/session_artifacts/dev_public_urls.json"

kill_by_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    local pids=$(lsof -t -i :$port || true)
    if [ -n "$pids" ]; then
      echo "Killing processes on :$port -> $pids"
      kill $pids 2>/dev/null || true
      sleep 1
      kill -9 $pids 2>/dev/null || true
    fi
  else
    echo "lsof not found; skipping port kill for :$port"
  fi
}

kill_by_port "$FE_PORT"
kill_by_port "$BE_PORT"

# If dev.sh auto-picked different ports, try the last recorded session URLs.
if [ -f "$DEV_URLS_JSON" ] && command -v python3 >/dev/null 2>&1; then
  read -r LAST_FE_PORT LAST_BE_PORT < <(
    python3 - "$DEV_URLS_JSON" <<'PY'
import json
import re
import sys
from urllib.parse import urlparse

path = sys.argv[1]
try:
    data = json.load(open(path, "r", encoding="utf-8"))
except Exception:
    print("")
    sys.exit(0)

def port_from_url(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""
    try:
        u = urlparse(s)
        if u.port:
            return str(u.port)
    except Exception:
        pass
    m = re.search(r":(\\d+)(?:/|$)", s)
    return m.group(1) if m else ""

fe = port_from_url(str(data.get("local_frontend_url") or ""))
be = port_from_url(str(data.get("local_backend_url") or ""))
print(f"{fe} {be}".strip())
PY
  )
  if [ -n "${LAST_FE_PORT:-}" ]; then
    kill_by_port "$LAST_FE_PORT"
  fi
  if [ -n "${LAST_BE_PORT:-}" ]; then
    kill_by_port "$LAST_BE_PORT"
  fi
fi

echo "Done."
