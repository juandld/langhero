# Security Audit & Best Practices (M6)

This doc is the running output of the M6 security workstream: code analysis, vulnerability review, and best-practice hardening for LangHero.

## Summary (current posture)

- The backend currently exposes powerful unauthenticated endpoints (import, publish, streaming). This is acceptable for local/dev, but **not safe to deploy publicly** without additional controls.
- Biggest risks are **SSRF**, **resource/cost amplification**, and **DoS** (especially via URL/video ingest and WebSockets).

## What we already hardened (recent changes)

### URL import SSRF safety

- URL fetching now blocks non-public targets (loopback/private/link-local/etc.) and validates redirects.
- Web page import uses strict caps (configurable):
  - `URL_FETCH_MAX_BYTES`
  - `URL_FETCH_TIMEOUT_S`

Relevant files:
- `backend/url_fetch.py`
- `backend/main.py`
- `backend/config.py`

### Streaming DoS caps

- WebSocket `/stream/interaction` now enforces:
  - per-chunk byte cap: `STREAM_MAX_CHUNK_BYTES`
  - per-session byte cap: `STREAM_MAX_SESSION_BYTES`
  - rolling buffer cap: `STREAM_MAX_BUFFER_BYTES` (prevents unbounded in-memory growth)

Relevant files:
- `backend/main.py`
- `backend/streaming.py`
- `backend/config.py`

### Import URL scheme restrictions

- Remote imports only allow `http`/`https` by default; local paths require explicit opt-in:
  - `ALLOW_LOCAL_IMPORT_PATHS=false` (default)

Relevant files:
- `backend/main.py`
- `backend/config.py`

### Admin gating + basic rate limiting (opt-in)

- Added optional admin API key gating for dangerous endpoints:
  - `REQUIRE_ADMIN_FOR_IMPORT`
  - `REQUIRE_ADMIN_FOR_PUBLISH`
  - `REQUIRE_ADMIN_FOR_STREAM`
- Added basic per-IP rate limits (disabled by default):
  - `RATE_LIMIT_ENABLED`
  - `RATE_LIMIT_IMPORT_PER_MIN`
  - `RATE_LIMIT_PUBLISH_PER_MIN`
  - `RATE_LIMIT_STREAM_CONN_PER_MIN`

Relevant files:
- `backend/main.py`
- `backend/config.py`

### Video ingest caps

- Added hard limits to reduce download/CPU spend and abuse:
  - `VIDEO_MAX_SECONDS` (ffmpeg extraction cap)
  - `YTDLP_MAX_FILESIZE_BYTES` (yt-dlp max filesize cap)

Relevant files:
- `backend/services.py`
- `backend/config.py`

## Top findings (prioritized)

### 1) Missing authentication / authorization (Critical)

Today, anyone who can reach the backend can:
- run imports (web/video) that trigger downloads/transcription/LLM,
- hit streaming endpoints that can burn provider quota,
- publish public artifacts.

Fix direction:
- Add auth (even simple API key for admin) and enforce it on:
  - `/api/import/auto`
  - `/api/scenarios/from_video`
  - `/api/stories/import`
  - `/api/published_runs` (create/delete at minimum)
  - `/stream/interaction`

### 2) Cost amplification (High)

Video ingest can be expensive (download + ffmpeg + transcription + LLM). Without quotas, an attacker can create runaway cost.

Fix direction:
- Per-IP / per-user quotas.
- Job queue + concurrency limits.
- Strict duration caps for extraction and provider calls (timeouts).
- Tiered behavior: demo/free -> cache-only / deterministic fallbacks (already partially implemented).

### 3) WebSocket abuse and resource exhaustion (High)

Even with byte caps, a public WS endpoint can be spammed with many short sessions.

Fix direction:
- Require auth token on WS init payload.
- Add origin checks / same-site enforcement when fronted by a single origin.
- Add rate limiting (connections per IP, messages per minute).

### 4) Supply chain and dependency hygiene (Medium)

Current repo uses unpinned dependencies; security audits are not automated.

Fix direction:
- Add CI steps:
  - Python: `pip-audit` (or equivalent) + minimal SAST (`bandit`)
  - Node: `npm audit` + lockfile checks
  - Secret scanning (`gitleaks` / GitHub Advanced Security)

### 5) Client-side secrets (Medium)

The UI stores the published-run delete key in browser storage for convenience. That’s OK for now, but it’s easy to leak via screenshots/screen-share or malicious browser extensions.

Fix direction:
- UX: “copy once” and warn; allow regeneration/rotation later.
- When auth exists: tie delete to account permissions rather than client-held key.

### 6) Production web security headers (Medium)

These are best handled in the reverse proxy (nginx/caddy):
- CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.

Fix direction:
- Add a “required headers” section to deployment docs and a smoke checklist.

## Recommended “audit run” procedure (repeatable)

1. **Entry-point inventory**
   - List every REST + WS route and label: public/admin/auth-required.
2. **Trust boundaries**
   - Identify all untrusted inputs (URLs, uploaded files, WS messages, localStorage).
3. **High-risk path review**
   - URL fetch + redirects + allow/deny logic.
   - yt-dlp/ffmpeg execution constraints + timeouts.
   - streaming chunk handling + buffer limits.
4. **Automated checks**
   - Add CI to run dependency + secret + SAST tooling.
5. **Fix + regression tests**
   - Write tests for each invariant (SSRF, caps, auth gates).

## Audit results (latest run)

### Node (frontend) — `npm audit`

Status:
- Resolved via dependency upgrades/overrides; `npm audit` now reports **0 vulnerabilities**.

### Python (backend) — `pip-audit`

- `pip-audit -r backend/requirements.txt`: **No known vulnerabilities found** at time of scan.

## Repeatable audit plan (thorough)

Use this checklist whenever we change import/stream/publish/auth.

1. **Map the attack surface**
   - Inventory every REST + WS route and classify it: public, trial, authenticated, admin-only.
   - For each endpoint, document untrusted inputs and the maximum work it can trigger (CPU/bandwidth/provider spend).
2. **Trust boundaries + data flows**
   - Identify where user data enters (URL, text, audio bytes, WS frames, localStorage).
   - Identify where it leaves (logs, published runs, caches, share links).
3. **High-risk path review**
   - URL ingest: SSRF, redirects, DNS rebinding considerations, response size/time caps, content-type handling.
   - Media ingest: ffmpeg/yt-dlp invocation safety, duration/size caps, concurrency limits, storage TTLs.
   - WebSockets: init validation, message size/rate, session teardown, origin checks behind proxy.
4. **Operational controls**
   - Quotas per user/IP/day (imports/minutes/day, publish rate).
   - Circuit breakers for provider errors/cost spikes.
   - Job queue for long-running imports (video) with worker concurrency limits.
5. **Supply chain**
   - Node: `npm audit` (CI gate) + lockfile review.
   - Python: `pip-audit` (CI gate) + pinned deps strategy.
   - Secret scanning (gitleaks) and basic SAST (bandit/semgrep) where feasible.
6. **Deployment posture**
   - One-origin reverse proxy with secure headers (CSP/HSTS/etc.).
   - Disable public exposure of dev servers (Vite).
   - Log hygiene + retention policy for caches/usage logs/published artifacts.
7. **Regression tests for invariants**
   - SSRF allow/deny + redirect validation.
   - URL/video max-bytes/max-seconds caps.
   - Streaming chunk/session byte caps and connection rate limit behavior.

## Next tasks (copy into task board)

- Replace admin-key gating with real auth (sessions/JWT) once `/login` is implemented.
- Add origin checks for WebSockets when fronted by a single origin.
- Add CI security checks: `pip-audit`, `npm audit`, secret scanning, minimal SAST.
- Add production header checklist (proxy config + verification steps) and a manual verification runbook.
- Add import concurrency limits + async jobs for video ingest before public exposure.
