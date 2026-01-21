# LangHero Workflow Standards (2025-12-28)

This revision syncs LangHero’s operator workflow with the **current cross-project process** being driven from `narritive-hero` (Telegram-first decision capture + phone-first dev access + token-budget discipline).

## Context

- Narrative Hero now acts as the “orchestrator” for decision sessions (including Telegram) and uses LangHero primarily as a **TTS backend**.
- Operators should be able to run LangHero and interact with it from a phone (external access) during a dev session, without creating long-lived public endpoints.

## Previous versions

- `project_updates/2025-12-26__langhero__workflow-standards__r3.md`
- `project_updates/2025-12-25__langhero__workflow-standards__r2.md`
- `project_updates/2025-12-25__langhero__workflow-standards.md`

## What changed (portable)

### 1) Phone-first dev access uses fast, per-session tunnels

Standard:
- Prefer **throwaway** tunnels (e.g. `trycloudflare.com`) for dev sessions so you can open the running UI from a phone anywhere.

Why:
- You get “works from my phone” without maintaining a permanent hostname or widening your firewall surface.
- The URL rotates per session, which is a meaningful security improvement vs a stable public endpoint.

Expectations:
- Dev scripts should print a clear **Frontend URL** when a tunnel is enabled.
- Frontend must call the **public backend URL** when accessed via a public tunnel (never `localhost`).

### 2) Keep LangHero TTS stable for orchestration (Narrative Hero depends on it)

Standard:
- Treat `/api/tts` as a stable contract and keep it easy to run on dynamic ports.

Why:
- Narrative Hero proxies to LangHero and may auto-discover ports in dev; stability beats cleverness.

Expectations:
- Respect `PORT` (or equivalent) for the backend dev server.
- Avoid logging secrets in URLs (bot tokens, API keys) at debug level.

### 3) Token-budget discipline: store full threads, but compute on compressed state

Standard:
- Keep full conversation/audit trails in files, but make “live LLM calls” rely on compact summaries + explicit gaps.

Why:
- It prevents “one small task consumes huge context” and keeps decisions reproducible.

Expectations:
- Store the full raw inputs (transcripts, prompts, intermediate notes) in repo files.
- For any LLM call, pass only a compact per-topic summary + “open gaps” list, not the entire history.

### 4) Operator sanity: fix ownership before strict checks

Standard:
- If running tests/tools fails due to permission errors (often from prior `docker` or `sudo` runs), fix file ownership first.

Why:
- Codex-driven automation depends on being able to read/write within the repo deterministically.

Expectations:
- Before running strict checks, verify the repo has no root-owned files under `tests/`, `development/`, or `scripts/`.
