# Task Board

## Session Log
- 2025-12-28 01:24 UTC — Aligned dev workflow with narritive-hero: env-driven CORS, phone-first tunnel-ready dev, and frontend public backend URL handling. Updated `backend/config.py` + `backend/main.py` to accept `ALLOWED_ORIGIN_*`/`ALLOWED_ORIGIN_REGEX`; enhanced `frontend/src/lib/config.ts` to honor `PUBLIC_BACKEND_URL` and avoid self-probing; revamped root `dev.sh` to pick stable per-repo ports, optionally start fast Cloudflare tunnels, and print public URLs. Implications: multiple repos can run concurrently; phone access works via throwaway URLs; `/api/tts` contract unchanged; backend dev respects `PORT`. Validation: `bash tests/test_all.sh` (backend 43 passed; frontend 13 passed).
- 2025-12-28 01:09 UTC — Synced `project_updates/` with the current cross-project operator workflow from `narritive-hero` (phone-first fast tunnels, stable `/api/tts`, token-budget discipline, and upgrade prompt/pack). Implications: Codex can ramp on LangHero with the same standards used by the decision orchestrator. Validation: `bash tests/test_all.sh` (backend tests pass; frontend Vitest fails with EPERM writing under `frontend/node_modules/.vite-temp` in this environment).
- 2025-12-26 00:42 UTC — Added microphone device selector to the recording controls (choose input device, refresh list; selection persisted in localStorage). Implemented in `ScenarioControls` + `ScenarioDisplay` and releases mic tracks after recording to allow easy switching.
- 2025-12-25 03:40 UTC — Updated “next logical steps” on the task board (execution tasks + founder decisions) based on the most recent work (menu/import/share/devtools/security/cohesion/confidence/provider harness).
- 2025-12-25 03:32 UTC — Added founder-facing decision tracker: `development/decision-board.md` (what you need to decide, why it matters, options + recommendations). Linked from `development/README.md` and referenced from `development/open-questions.md`.
- 2025-12-25 03:25 UTC — Finished MVP cohesion + feedback improvements: run score/lives now persist per saved run and are carried into streaming init (no unintended resets when entering live mode). Added best-effort `confidence` + `match_type` to interaction results and a HUD confidence meter. Added provider benchmark harness (`backend/provider_benchmark.py`) + logbook (`development/notes/provider-benchmarks.md`). Updated contracts and security audit docs.
- 2025-12-25 02:17 UTC — Ran dependency vulnerability scans: `pip-audit` reports no known Python CVEs for `backend/requirements.txt`; `npm audit` flags `cookie@0.6.0` (via `@sveltejs/kit`) and `esbuild@0.21.5` (via `vite@5.4.19`). Logged next actions in `development/security-audit.md`.
- 2025-12-25 02:05 UTC — Started M6 security hardening pass and applied first safeguards: SSRF-safe validation is now enforced for URL/video imports (http/https only by default; block private hosts; validate redirects; size/time caps), and `/stream/interaction` now enforces per-chunk/per-session byte caps plus rolling buffer limits to reduce DoS risk. Added `development/security-audit.md` as the running vulnerability review + best-practices checklist.
- 2025-12-25 01:36 UTC — Added Security/Best-Practices audit milestone: threat model + vulnerability review focusing on URL/video ingest, publish/share, and WebSockets; add SSRF/DoS/resource caps, dependency audits, secrets/log hygiene, and CI guardrails. Logged as M6 in `development/north-star-execution.md` and queued as an active workstream below.
- 2025-12-25 01:06 UTC — Unified import UX: `/import` is now a single form (URL auto-detect is default; extra text optional). Added backend `POST /api/import/auto` to route URL→video pipeline vs URL→web-text fetch vs text-only compile; keeps rights attestation required and respects demo cache-only video mode.
- 2025-12-25 00:48 UTC — Made Dev Tools visibility code-controlled (no `?dev=1` requirement; toggle via `frontend/src/lib/devtools.ts`). Fixed menu card contrast (solid dark card backgrounds). Expanded URL ingestion: story import now supports `source_url` by fetching/extracting readable text (SSRF-safe allowlist), import UI adds a Web URL tab, and video ingest now falls back to yt-dlp piping for many non-YouTube video URLs when ffmpeg can’t open them.
- 2025-12-25 00:32 UTC — Wired “usage + estimated cost” dev tooling end-to-end: backend now exposes `GET /api/meta`, `GET /api/usage/weekly`, and `GET /api/usage/recent`; weekly rollups include `by_event_provider_model` for cost estimation. Frontend adds a global `Dev tools` dock (toggle in code via `frontend/src/lib/devtools.ts`) that shows backend demo flags, weekly usage breakdown, editable unit prices, and estimated totals. Import UI now supports YouTube/video URLs via `POST /api/scenarios/from_video` with required rights attestation, and menu/import/play pages show a demo-mode banner.
- 2025-12-24 23:58 UTC — Landed “marketing demo mode” cost controls: added backend flags (`DEMO_MODE`, `DEMO_VIDEO_CACHE_ONLY`, `DEMO_ALLOW_LLM_IMPORT`, `DEMO_DISABLE_STREAMING`) to keep free/demo runs cheap. Demo mode blocks uncached `/api/scenarios/from_video`, disables real streaming WS (`/stream/interaction`), and forces story import to deterministic fallback (no LLM). Added regression tests (`tests/demo_mode_test.py`) and updated north-star docs (`development/ux.md`, `development/north-star-execution.md`, `development/current_plans.md`).
- 2025-12-24 23:51 UTC — Added deployment guide (`development/deployment.md`) covering recommended single-origin Nginx reverse-proxy setup (REST + WebSockets), required persistent volumes (notes, scenarios, caches, published runs), YouTube prerequisites (ffmpeg + yt-dlp), and scaling notes (async jobs + shared cache/storage).
- 2025-12-24 23:49 UTC — Added exact-match caching for video imports: `/api/scenarios/from_video` now caches compiled Scenario[] keyed by normalized source id (YouTube id when present) + target language + max scenes, returning `cached: true` on cache hits. Added `backend/import_cache.py`, isolated cache dir in pytest, and added regression test `tests/video_import_cache_test.py`.
- 2025-12-24 23:46 UTC — Documented import scaling + waste reduction approach (`development/import-scaling.md`) covering resource hotspots (YouTube/video: download+ffmpeg+transcribe+LLM), caching/dedupe layers (download/audio/transcript/scenario/similarity), and privacy-friendly cache scoping (per-user/org vs global opt-in). Linked from `development/README.md`, added to `development/current_plans.md`, and added cache-scope question to `development/open-questions.md`.
- 2025-12-24 23:37 UTC — Implemented explicit publish/share flow for compiled runs: backend `POST/GET/DELETE /api/published_runs` (returns `public_id` + `delete_key`), frontend menu “Publish” + share details, and new `/share/[id]` route that loads published Scenario[] and lets users “Save to my runs & play”. Added pytest coverage (`tests/published_runs_test.py`) and updated contracts doc.
- 2025-12-24 23:31 UTC — Clarified Story Import intent + guardrails: import is a “story seed → playable run compiler” (not a content hosting feature). Privacy compliance (GDPR/HIPAA posture) ≠ IP shield; require user rights attestation (already in `POST /api/stories/import`) and keep imports private-by-default. Separate **Private practice** vs **Publish/share** flows; share links should not expose raw source by default (prefer compiled Scenario[] only). Add explicit “publish” confirmation if we ever make content publicly retrievable. Next decision: should `/play/<id>` be auth-gated private runs, or a published artifact with additional friction + takedown/abuse + retention controls.
- 2025-12-20 05:21 UTC — Ran `bash tests/test_all.sh` (backend+frontend: all pass) and a headless `/demo` smoke run (frontend `/demo` + `/import` 200; backend `/api/scenarios` + `/api/notes` 200; `/api/stories/import` now includes `mode` with an advanced scene; `/stream/mock` emits ready/partial/final). Added import normalization + regression test (`backend/story_import.py`, `tests/story_import_test.py`).
- 2025-12-20 23:55 UTC — Added judge focus slider + language override (wired through REST + streaming), added story import v0 (`/import`, `POST /api/stories/import`), added code-map/contracts docs, added `bash tests/test_all.sh`, refactored backend language/import modules, and re-ran backend + frontend test suites (all pass).
- 2025-12-20 04:01 UTC — Logged UTC start, captured instant context (`python3 operations/scripts/instant_context.py`), checked `git status -sb`, added SSR Vitest component tests for HUD pieces (`ScenarioStatus`, `ScenarioControls`, `ScenarioOptionsPanel`), added `/demo` smoke checklist (`development/demo-smoke.md`), and re-ran `./tests/test.sh` (19 pass) + `frontend/npm run test:run` (12 pass).
- 2025-12-18 03:06 UTC — Logged UTC start, captured instant context (`python3 operations/scripts/instant_context.py`), checked `git status -sb`, added `/demo` route + Vitest `storyStore` tests, and re-ran `./tests/test.sh` (19 pass).
- 2025-12-15 19:00 UTC — Logged UTC start, captured instant context (`python3 operations/scripts/instant_context.py`), checked `git status -sb`, and re-ran `bash tests/test.sh` (17 pass).
- 2025-12-10 16:50 UTC — Logged UTC start, captured instant context, checked git status, and re-ran `./tests/test.sh` (17 pass).
- 2025-12-05 03:20 UTC — Switched voice assets to UUID-backed canonical clips (manifest + scenario index), updated README/docs, and added pytest coverage for the new flow.
- 2025-12-05 03:05 UTC — Implemented manifest-backed voice dedupe + variant options, added pytest coverage (`tests/voice_generation_test.py`), and refreshed README/docs.
- 2025-12-05 02:51 UTC — Added `operations/scripts/generate_voices.py`, documented the workflow in README, and outlined how to synthesize scenario voices with OpenAI TTS.
- 2025-12-05 02:44 UTC — Added reusable beginner/advanced scenario fixtures for tests, expanded streaming session coverage, and re-ran `./tests/test.sh` (13 pass).
- 2025-12-05 02:40 UTC — Centralized scenario scoring defaults in backend config, documented the progression table, and re-ran `./tests/test.sh` (12 pass).
- 2025-12-04 13:07 UTC — Logged UTC start, captured instant context, reviewed docs, inspected git status, and ran `./tests/test.sh` (12 pass) for this session hand-off.
- 2025-11-30 22:19 UTC — Completed scenario mode toggle pass (streaming metadata, HUD copy/controls), updated docs, and re-ran `./tests/test.sh` (12 pass).
- 2025-11-30 22:10 UTC — Ran operator workflow touchpoints: logged UTC start, captured instant context (macOS cache warning persists), and re-ran `./tests/test.sh` (11 pass).
- 2025-11-30 19:40 UTC — Codex operator started Project Upgrade workflow and created baseline ops docs/scripts.
- 2025-11-30 19:41 UTC — Captured context via `operations/scripts/instant_context.py` (warning: macOS cache permission noise) and ran `./tests/test.sh` (all pass; FastAPI `@app.on_event` deprecation warning persists).
- 2025-11-30 19:46 UTC — Session resumed to migrate FastAPI startup hooks to lifespan handlers and re-run regression tests (`./tests/test.sh` now clean).

## Active Work
| Task | Owner | Status | Notes |
| --- | --- | --- | --- |
| MVP Cohesion Pass | frontend/backend | Completed | Run score/lives persist per saved run and survive mode changes; see `frontend/src/lib/runStore.js` and `frontend/src/lib/components/ScenarioDisplay.svelte`. |
| M4 Scenario Mode Toggle | frontend/backend | In Progress | `/demo` route + Vitest `storyStore` tests + HUD SSR component tests landed; remaining: run `/demo` smoke checklist and capture notes; see `development/scenario-progression.md`. |
| Story Import v0 | backend/frontend | Completed | Unified `/import` UI + `POST /api/import/auto` (web/video/text) with rights attestation; imports private-by-default and publish/share is explicit via `/api/published_runs`. |
| Dev Tools Usage + Cost Estimates | frontend/backend | Completed | In-app dock reads `/api/usage/*` logs and applies editable unit prices to estimate weekly cost (toggle via `frontend/src/lib/devtools.ts`). |
| M5 Confidence & Lives Feedback | frontend/backend | Completed | Added `confidence` + `match_type` to interaction results and a HUD confidence meter; lives/score persistence is part of cohesion. |
| M2 Provider Shoot-out Harness | backend | Completed | Added `backend/provider_benchmark.py` and `development/notes/provider-benchmarks.md` for repeatable latency logging. |
| Voice clip dedupe & reasoning tests | backend/ops | Completed | Manifest-backed caching + pytest coverage landed (`operations/scripts/generate_voices.py`, `tests/voice_generation_test.py`). |
| M6 Security + Abuse Hardening | frontend/backend/ops | In Progress | SSRF-safe URL fetch + import caps, streaming byte caps, video duration/filesize caps, and optional admin/rate-limit gates are in place; ongoing work tracked in `development/security-audit.md`. Next: CI security checks + production header checklist + real auth. |

## Decisions Needed (Founder)

Track and resolve these in `development/decision-board.md` (they unblock clean implementation choices):

| Decision | Why it matters | Status |
| --- | --- | --- |
| D1 Accounts + “Login” scope | determines cross-device saves, quotas, and auth strategy | Needs decision |
| D2 IP/content responsibility policy | determines what we store/serve and what’s shareable | Needs decision |
| D3 Cache/dedupe scope | biggest cost-saver + biggest privacy foot-gun | Needs decision |
| D4 Free vs trial vs paid knobs | keeps marketing cheap + prevents cost abuse | Needs decision |
| D5 `/play/<id>` vs `/share/<id>` semantics | defines private vs public sharing | Needs decision |
| D6 Streaming transcript retention | defines privacy posture + compliance surface | Needs decision |
| D8 URL ingestion scope | defines what “any URL” means and what we build first | Needs decision |

## Next Logical Steps (LLM / Engineering)

These are the next implementation tasks that follow directly from what’s already shipped:

1. **Run the `/demo` smoke checklist and log results** (`development/demo-smoke.md`) → close M4.
2. **Add CI guardrails for M6**: run `bash tests/test_all.sh`, `pip-audit`, `npm audit` on PRs; add basic secret scanning + minimal SAST.
3. **Finalize production hardening runbook**: document required proxy headers + WS origin strategy and add a deployment readiness checklist.
4. **URL ingest expansion v1 (after D8)**: define supported URL classes and add extraction support incrementally (HTML → video → PDFs → “complex sites”).
5. **Auth (after D1/D5)**: wire `/login` into real sessions and enforce auth/quotas on import/publish/stream endpoints (replace admin-key gating).

## Queue / Ideas
- Document deployment readiness checklist for M6 Production Hardening.
- Revisit notes UI wiring once backend endpoints stabilize.

## Operator Shortcuts

- Brief status: `python3 tools/status.py`
- Close a session artifact: `python3 tools/close_session.py`
