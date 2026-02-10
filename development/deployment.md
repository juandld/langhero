# Deployment Guide (Current + Recommended)

This doc describes what a production deployment looks like for LangHero (SvelteKit SPA + FastAPI backend), including persistence, WebSockets, and what breaks when scaling.

## Components

- **Frontend**: static SPA build served by Nginx (SvelteKit SSR is disabled in this repo).
- **Backend**: FastAPI (Uvicorn) serving:
  - REST (`/api/*`, `/narrative/*`)
  - WebSockets (`/stream/*`)
  - Static media mounts (`/voice_notes`, `/examples`)
- **Workers (recommended next)**: async job runner for video imports (download/ffmpeg/transcribe/LLM) and long-running tasks.

## Baseline (single-host Docker Compose)

`compose.yaml` currently builds:
- `backend` exposed on `:8000`
- `frontend` exposed on `:80`

This is fine for local use, but production usually wants **one origin** (same domain) to avoid CORS complexity and to support WebSockets cleanly.

## Recommended production topology (one origin)

Run Nginx as the public entrypoint and reverse-proxy to the backend:

- `https://app.example.com/` → frontend static SPA
- `https://app.example.com/api/*` → backend `:8000`
- `https://app.example.com/narrative/*` → backend `:8000`
- `wss://app.example.com/stream/*` → backend `:8000` (upgrade headers)
- `https://app.example.com/voice_notes/*` → backend `:8000`
- `https://app.example.com/examples/*` → backend `:8000`

Benefits:
- No CORS headaches.
- Share links (`/play/...`, `/share/...`) work as normal SPA routes.
- WebSockets work behind a single proxy with proper upgrade configuration.

## Persistent storage (what must survive restarts)

LangHero currently writes important state to the filesystem. In production, mount these as volumes (or move to object storage/DB later):

- **Uploads/notes**
  - `voice_notes/` (audio files)
  - `transcriptions/` (JSON note metadata + transcript text)
  - `narratives/` (generated narrative `.txt`)
- **Scenario authoring/admin**
  - `backend/scenarios.json` (active scenario store)
  - `backend/scenario_versions/` (version snapshots)
- **Examples / TTS**
  - `examples_audio/` (voice clip cache + manifest)
- **Import caching**
  - `backend/import_cache/` (video import Scenario[] cache)
- **Published share artifacts**
  - `backend/published_runs/` (published Scenario[] JSON + delete-key hash)

If you run multiple backend replicas, any filesystem-backed store must be moved to **shared storage** (object store, NFS, etc.) or replaced with a DB/cache service.

## Environment / secrets

Backend needs:
- `GOOGLE_API_KEY` (Gemini) and optional rotation keys
- Optional `OPENAI_API_KEY` (fallback + some features)
- Optional provider preferences (`TRANSCRIBE_*` vars)

In production, prefer container secrets/managed env vars over committing `.env`.

## YouTube / video import prerequisites

- `ffmpeg` in the backend image (already installed via apt in `backend/Dockerfile`).
- `yt-dlp` installed in Python deps (now in `backend/requirements.txt`).

Operationally:
- Video import is bandwidth- and transcription-heavy; add quotas and async jobs before enabling for many users.

## WebSockets behind a proxy

Reverse proxy must include upgrade headers. Example Nginx snippet:

```
location /stream/ {
  proxy_pass http://backend:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}
```

Also proxy `/api/`, `/narrative/`, `/voice_notes/`, `/examples/`.

## Scaling notes (what changes when load increases)

### What scales poorly today
- `/api/scenarios/from_video` is synchronous and can take tens of seconds (download + transcribe + LLM).
- Video imports are compute+network heavy; they will saturate worker capacity and/or provider quotas quickly.
- Caches (`import_cache`) are local filesystem; multiple replicas won’t share hits.

### What to do to scale
1. Convert video import into **async jobs** (API enqueues, UI polls job status).
2. Add **rate limits and quotas** (per user/day, minutes/day, concurrent jobs).
3. Move caches to shared services:
   - transcript/scenario compile cache in Redis/DB (exact match)
   - media artifacts in object storage
4. If you need multiple backend replicas:
   - use sticky routing for WebSockets or a dedicated WS service.

## Security/privacy expectations (operational)

- Imports are private-by-default; publishing is explicit.
- Published artifacts are compiled Scenario[]; avoid exposing raw imported text/media by default.
- Add request limits for publishing endpoints and video import endpoints.
- Avoid logging raw user content; log event metadata (durations, cache hits, status codes).

## Reverse proxy security headers (recommended)

Prefer setting these at the edge (nginx/caddy) rather than in-app:

- `Strict-Transport-Security` (HSTS) once HTTPS is stable
- `Content-Security-Policy` (start restrictive, loosen as needed)
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer` (or `strict-origin-when-cross-origin`)
- `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`)

Also pass standard proxy headers so the backend sees the public scheme/host:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

## WebSocket origin strategy (production)

When you front LangHero with a single public origin, treat that origin as the only valid WS origin:

- Set backend allowlist env vars (e.g. `ALLOWED_ORIGIN_1=https://app.example.com` or `ALLOWED_ORIGIN_REGEX`) to the production domain.
- If you control the reverse proxy, block unexpected `Origin` headers for `/stream/*` before they hit the app.
- Avoid exposing the backend directly on the public internet; keep it behind the proxy.

## Deployment readiness checklist

- HTTPS enabled at the edge; HSTS set only after TLS is stable.
- Reverse proxy passes `/api/*`, `/narrative/*`, `/voice_notes/*`, `/examples/*`, and `/stream/*` to the backend with upgrade headers for WebSockets.
- Security headers applied and validated against the SPA (menu/import/play/share).
- Backend allowlist env vars set for the production origin (CORS + WS origin checks).
- Persistent volumes mounted for notes, scenarios, caches, and published runs.
- Demo mode flags and admin gating set appropriately for the environment.
- Smoke check: `/stream/*` websocket upgrade succeeds through the proxy.
