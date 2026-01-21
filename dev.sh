#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stable, per-repo default ports so multiple projects can run concurrently.
if [ -z "${DEV_PORT_SEED+x}" ] || [ -z "${DEV_PORT_SEED:-}" ]; then
  DEV_PORT_SEED="$(printf '%s' "$ROOT_DIR" | cksum | awk '{print $1}')"
fi
PORT_OFFSET=$((DEV_PORT_SEED % 50))

FRONTEND_DEV_PORT=${FRONTEND_DEV_PORT:-$((5173 + PORT_OFFSET))}
BACKEND_DEV_PORT=${BACKEND_DEV_PORT:-$((8000 + PORT_OFFSET))}

FRONTEND_DEV_HOST=${FRONTEND_DEV_HOST:-0.0.0.0}
START_FAST_TUNNELS=${START_FAST_TUNNELS:-0}

is_port_free() {
  local port=$1
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$port" <<'PY'
import errno, socket, sys
port=int(sys.argv[1])
def try_connect(host):
    try:
        s=socket.create_connection((host, port), timeout=0.15); s.close(); return True
    except Exception:
        return False
for host in ("127.0.0.1","::1","localhost"):
    if try_connect(host):
        raise SystemExit(1)
for family,host in ((socket.AF_INET,"0.0.0.0"),(socket.AF_INET6,"::")):
    try:
        s=socket.socket(family, socket.SOCK_STREAM)
        if family==socket.AF_INET6:
            try: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            except OSError: pass
        s.bind((host, port)); s.listen(1); s.close()
    except OSError as e:
        if getattr(e, 'errno', None) in (errno.EADDRINUSE, 48, 98):
            raise SystemExit(1)
        raise SystemExit(1)
raise SystemExit(0)
PY
    return $?
  fi
  return 0
}

pick_port() {
  local start=${1:?}
  local limit=$((start+50))
  local p=$start
  while [ $p -le $limit ]; do
    if is_port_free $p; then echo $p; return 0; fi
    p=$((p+1))
  done
  echo $start
}

FE_PORT=$(pick_port ${FRONTEND_DEV_PORT})
BE_PORT=$(pick_port ${BACKEND_DEV_PORT})
if [ "$FE_PORT" != "$FRONTEND_DEV_PORT" ]; then
  echo "Note: Requested frontend :$FRONTEND_DEV_PORT busy; using :$FE_PORT"
fi
if [ "$BE_PORT" != "$BACKEND_DEV_PORT" ]; then
  echo "Note: Requested backend :$BACKEND_DEV_PORT busy; using :$BE_PORT"
fi

# Optional fast, per-session public tunnels (trycloudflare). Requires Docker.
DEV_PUBLIC_BACKEND_URL="${DEV_PUBLIC_BACKEND_URL:-}"
DEV_PUBLIC_FRONTEND_URL="${DEV_PUBLIC_FRONTEND_URL:-}"
BE_TUNNEL_CONTAINER="langhero-backend-tunnel"
FE_TUNNEL_CONTAINER="langhero-frontend-tunnel"

start_fast_tunnel_for_port() {
  local container_name="$1" port="$2" label="$3"
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker not found; skipping ${label} tunnel." >&2
    return 1
  fi
  docker rm -f "$container_name" >/dev/null 2>&1 || true
  echo "Starting fast dev tunnel (${label}) -> http://host.docker.internal:${port} ..." >&2
  if ! docker run -d --name "$container_name" cloudflare/cloudflared:latest \
    tunnel --no-autoupdate --url "http://host.docker.internal:${port}" >/dev/null; then
    echo "Warning: Failed to start tunnel container ${container_name}." >&2
    return 1
  fi
  local tries=0 url=""
  while [ $tries -lt 80 ]; do
    url="$(docker logs --tail 250 "$container_name" 2>&1 | rg -o 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -n 1 | tr -d '\r' || true)"
    if [ -n "$url" ]; then
      echo "$url"
      return 0
    fi
    tries=$((tries+1)); sleep 0.2
  done
  echo "Warning: Could not discover trycloudflare URL from ${container_name} logs." >&2
  return 1
}

if [ "${START_FAST_TUNNELS}" = "1" ]; then
  be_url="$(start_fast_tunnel_for_port "$BE_TUNNEL_CONTAINER" "$BE_PORT" backend || true)"
  fe_url="$(start_fast_tunnel_for_port "$FE_TUNNEL_CONTAINER" "$FE_PORT" frontend || true)"
  if [[ -n "${be_url:-}" && "${be_url:-}" == https://*.trycloudflare.com ]]; then
    DEV_PUBLIC_BACKEND_URL="${DEV_PUBLIC_BACKEND_URL:-$be_url}"
  fi
  if [[ -n "${fe_url:-}" && "${fe_url:-}" == https://*.trycloudflare.com ]]; then
    DEV_PUBLIC_FRONTEND_URL="${DEV_PUBLIC_FRONTEND_URL:-$fe_url}"
  fi
fi

# Write a stable "current dev URLs" file so an orchestrator (e.g. narritive-hero Telegram) can
# link to this project's frontend/backend from a phone.
DEV_URLS_JSON="${ROOT_DIR}/development/session_artifacts/dev_public_urls.json"
mkdir -p "$(dirname "$DEV_URLS_JSON")"
if command -v python3 >/dev/null 2>&1; then
  python3 - "$DEV_URLS_JSON" "$(basename "$ROOT_DIR")" "$FE_PORT" "$BE_PORT" <<'PY'
import json, os, sys
from datetime import datetime, timezone

path = sys.argv[1]
project_id = sys.argv[2]
fe_port = sys.argv[3]
be_port = sys.argv[4]

def clean(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'").rstrip("/")
    return s

payload = {
    "project_id": project_id,
    "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "tunneled": os.getenv("START_FAST_TUNNELS", "0").strip() == "1",
    "frontend_url": clean(os.getenv("DEV_PUBLIC_FRONTEND_URL", "")),
    "backend_url": clean(os.getenv("DEV_PUBLIC_BACKEND_URL", "")),
    "local_frontend_url": f"http://localhost:{fe_port}",
    "local_backend_url": f"http://localhost:{be_port}",
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
PY
fi

# Ensure frontend deps are installed
if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required to run the frontend. Install Node.js/npm first." >&2
  exit 1
fi
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
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
  if command -v docker >/dev/null 2>&1; then
    docker rm -f "$BE_TUNNEL_CONTAINER" "$FE_TUNNEL_CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting frontend dev server on :$FE_PORT ..."
(
  cd "$ROOT_DIR/frontend"
  export PUBLIC_BACKEND_URL="${DEV_PUBLIC_BACKEND_URL:-http://localhost:${BE_PORT}}"
  exec npm run dev -- --host "${FRONTEND_DEV_HOST}" --port "${FE_PORT}" --strictPort
) &
FRONTEND_PID=$!

echo "Starting backend dev server on :$BE_PORT ..."
(
  cd "$ROOT_DIR/backend"
  export PORT=${BE_PORT}
  export ALLOWED_ORIGIN_1="http://localhost:${FE_PORT}"
  export ALLOWED_ORIGIN_2="http://127.0.0.1:${FE_PORT}"
  if [ -n "${DEV_PUBLIC_FRONTEND_URL:-}" ]; then
    export ALLOWED_ORIGIN_3="${DEV_PUBLIC_FRONTEND_URL}"
  fi
  export NARRATIVE_PUBLIC_FRONTEND_URL="${DEV_PUBLIC_FRONTEND_URL:-}"
  export NARRATIVE_PUBLIC_BACKEND_URL="${DEV_PUBLIC_BACKEND_URL:-}"
  exec ./dev.sh
) &
BACKEND_PID=$!

if [ -n "${DEV_PUBLIC_BACKEND_URL:-}" ]; then
  echo "Dev public backend URL: ${DEV_PUBLIC_BACKEND_URL}"
fi
if [ -n "${DEV_PUBLIC_FRONTEND_URL:-}" ]; then
  echo "Dev public frontend URL: ${DEV_PUBLIC_FRONTEND_URL}"
else
  echo "Local frontend URL: http://localhost:${FE_PORT}"
fi

wait "$BACKEND_PID"
status=$?
wait "$FRONTEND_PID" >/dev/null 2>&1 || true
exit $status
