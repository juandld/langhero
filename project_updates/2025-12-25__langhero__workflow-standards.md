# LangHero Workflow Standards (2025-12-25)

This file captures **what changed in this project that improved the workflow**, so the same standardization can be applied to other repos.

## Context

- Source: this repo’s evolution (docs + ops + demo-cost posture + security hardening).
- Primary goal: make every future session/operator/agent produce consistent, auditable progress with minimal context re-load.

## Previous versions

- None (first archived version).

## What we standardized (portable)

### 1) Repo-wide “operator workflow” standardization

What we standardized:

- **Single source of truth docs folder**: `development/` holds the living docs, with an index at `development/README.md`.
- **LLM task board** (engineering execution): `development/task_board.md` (session log + active work table).
- **Founder decision board** (product/policy decisions): `development/decision-board.md` (decisions, options, recommendations).
- **Open questions** stays lightweight: `development/open-questions.md` links to decision board when a question is actually a decision.
- **North star → milestones**: `development/north-star-execution.md` is the “definition of done” and milestone order.
- **Contracts doc** to keep UI↔API stable: `development/contracts.md`.
- **Deployment guide**: `development/deployment.md` (single-origin proxy, volumes, WS notes).
- **Security audit as a living doc**: `development/security-audit.md` (threat model + findings + repeatable audit plan).

Why it’s valuable:
- New contributors can orient in minutes without tribal knowledge.
- We can track “what did we run / what changed / what’s left” with timestamps.
- Product decisions stop blocking implementation because they’re explicitly captured.

How to port to other repos:
- Copy the `development/` structure and keep `development/README.md` as the index.
- Add `development/task_board.md` + `development/current_plans.md` (or equivalent).
- Add `development/decision-board.md` to separate “founder decisions” from “engineering tasks”.

### 2) Test harness standardization (CI-style confidence)

What we added:
- A single command to run everything: `bash tests/test_all.sh`
  - runs backend tests (`./tests/test.sh`)
  - runs frontend unit tests (`frontend/npm run test:run`)

Why it’s valuable:
- One “green” signal before hand-off.
- Easy to drop into CI later.

How to port:
- Add `tests/test_all.sh` that calls backend + frontend tests in a consistent order.

### 3) “Marketing demo mode” cost controls (cheap trials)

What we standardized:
- Backend feature flags (env) to keep demo/trial near-zero marginal cost:
  - `DEMO_MODE`
  - `DEMO_VIDEO_CACHE_ONLY`
  - `DEMO_ALLOW_LLM_IMPORT`
  - `DEMO_DISABLE_STREAMING`
- Frontend exposes demo status via `GET /api/meta` and shows a banner (`DemoModeBanner`).

Why it’s valuable:
- We can run demos as “advertising” without accidentally burning transcription/LLM costs.

How to port:
- Add demo/trial flags to the backend (don’t rely on frontend switches).
- Add a simple `GET /api/meta` endpoint and a UI banner.

### 4) Dev tools standardization (usage + cost visibility)

What we standardized:
- Backend usage endpoints:
  - `GET /api/usage/weekly`
  - `GET /api/usage/recent`
- Frontend “Dev tools dock” (code-toggle only) showing usage + **estimated costs** with editable unit prices.

Why it’s valuable:
- Cost is visible during development, not after the bill.

How to port:
- Log provider/model events server-side.
- Expose summary endpoints and build a tiny in-app dock gated by a code constant.

### 5) Ingestion hardening + resource caps (safe “import anything” posture)

What we standardized:
- Unified import endpoint: `POST /api/import/auto`.
- SSRF-safe URL validation + fetch caps (centralized in a URL fetch module).
- Video ingest caps (duration/filesize).
- WebSocket DoS caps (chunk/session/buffer).
- Optional admin gating + rate limiting as an interim control.

Why it’s valuable:
- Import pipelines are the #1 cost/abuse surface; caps + SSRF protection are mandatory for public deploy.

How to port:
- Centralize SSRF-safe URL handling in one module.
- Make caps configurable via env with conservative defaults.
- Add rate-limits/gates even if auth isn’t built yet (then replace with real auth).

### 6) Shareability model: private runs vs publish/share artifacts

What we standardized:
- Private-by-default local runs (`/play/<id>` saved locally).
- Explicit publish/share flow for a compiled artifact (`/share/<public_id>`).

Why it’s valuable:
- Share links are stable and safe to distribute.
- Keeps raw imported sources out of public URLs by default.

How to port:
- Treat “publish” as a separate, explicit action with confirmation friction.
- Share derived artifacts, not raw media/text, by default.

### 7) UX standardization: global nav + breadcrumbs

What we standardized:
- Global top nav and breadcrumbs at the layout level.
- Main page becomes a game-like “menu” with save cards.

Why it’s valuable:
- Navigation never “falls off the bottom” of the page.

### 8) “Cohesion” standard: run-level state persistence

What we standardized:
- Score/lives persist at the run level (not reset on scene/mode changes).
- Streaming init carries prior score/lives to avoid resets when entering live mode.

Why it’s valuable:
- Prevents “it reset my run” bugs that kill the game feel.

## Why these decisions were made (traceability)

Primary evidence trails:
- `development/task_board.md` (timestamped implementation log)
- `development/north-star-execution.md` (definition of done + milestone order)
- `development/security-audit.md` (threat model + hardening plan)
- `development/decision-board.md` (founder decisions that unblock implementation)

## Quick checklist for upgrading another repo

- [ ] Add `development/` docs index + task board + current plans.
- [ ] Add `development/decision-board.md` for founder decisions.
- [ ] Add `tests/test_all.sh` as the single green check.
- [ ] Add demo/trial env flags and `GET /api/meta`.
- [ ] Add usage logging + weekly/recent endpoints + a dev dock.
- [ ] Add SSRF-safe URL fetch module + caps for ingest + WS caps.
- [ ] Add explicit publish/share artifact flow (compiled-only by default).
- [ ] Add layout-level top nav + breadcrumbs.
- [ ] Persist run-level score/lives across modes.

