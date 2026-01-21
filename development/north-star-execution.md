# North Star Execution Plan

This doc turns the north star into an executable MVP path: **import a story → time-stop rehearsal → live pressure → consequences → progress**.

## North Star (current)

- **Player**: isolated, regret-prone learner who needs a “game excuse” to practice speaking.
- **Promise**: words are the primary mechanic; dialogue is how you survive, escape, negotiate, and set boundaries.
- **Shape**: “BG3 with voice” (freeform speech) with two loops:
  - **Beginner (time-stop)**: repeat/translate/rehearse safely, then commit with mic.
  - **Advanced (streaming)**: speak live under pressure; system responds in real time.
- **Knobs**:
  - **Judge focus** slider: learning-first ↔ story-first.
  - **Language**: inferred from setting; user can override.

## MVP Definition (done when…)

- A user can **import a story seed** (text v0) and immediately play a scenario chain.
- The chain includes **at least one time-stop scene** and **at least one streaming scene**.
- Player can speak freely; system returns **coherent consequences** and advances to the next beat.
- Score/lives updates are consistent across both REST and streaming and **do not reset unintentionally**.
- UI shows a **confidence meter** after each turn (best-effort) so penalties feel actionable.
- A user can experience a **free/demo run** that is **cheap enough for marketing** (pre-baked scenarios + mock streaming), without requiring paid-tier AI.

## Core Contracts (must stay stable)

See `development/contracts.md`.

## Milestones (build order)

### M-1 — Marketing Demo Mode (cost-controlled)

Goal: make “try it” shareable at near-zero marginal cost.

- Ship pre-baked demo scenarios that exercise time-stop + live-mode UI without requiring real ASR/LLM.
- Default demo to `/stream/mock`; disable real streaming ASR in demo mode.
- In demo mode, block uncached `/api/scenarios/from_video` (download+ffmpeg+transcribe+LLM) and use deterministic fallback for story import.
- Provide a clear upgrade path: metered “AI trial” budgets and quotas for real imports/streaming.

### M0 — Cohesion + Run State

Goal: make “a run” feel like a run (progression, persistent score/lives).

- Separate **run state** from **scenario state**:
  - score, lives_remaining, lives_total, current_run_id
  - reset only on “new run” / “import story” / explicit reset
- Ensure mode transitions don’t wipe state (time-stop → streaming → back).
- Add a small HUD section: run progress (scene index / total) and a “New Run” button.

### M1 — Story Import v1 (text-only, deterministic)

Goal: imported text produces a usable playable chain without human tweaking.

- Extract minimal story seed:
  - setting, protagonist role, scene goals, key entities (names), tone
- Compile into 5–12 scenes with:
  - scene goal (what “success” means)
  - at least one **advanced** (streaming) beat by design (e.g., scene 2+)
  - 2–4 options per scene with examples (optional for later)
- Persist imported runs locally (first pass can be in-memory + localStorage for frontend).

### M2 — Interaction Engine v1 (freeform → structured)

Goal: player can say anything, but the world reacts through a stable intent layer.

- Convert speech → structured intent:
  - intent label (aligned to the scene goal)
  - confidence
  - tone (polite/hostile/neutral) and “in-character” score
- Map intent to outcome:
  - advance / retry / branch / stall
  - apply scoreDelta/livesDelta and a short feedback string
- Keep judge slider meaningful:
  - learning-first: stricter language + clearer coaching
  - story-first: more permissive advancement, fewer language gates

### M3 — Confidence + Feedback (M5)

Goal: show what the system heard, how sure it is, and what to do next.

- Add confidence payload on both paths:
  - REST interaction response
  - streaming partial/final events
- UI: confidence meter + “why penalty happened” copy
- Add “recast” option (one short better line) without breaking flow

### M4 — Interaction Taxonomy v0 (defense/escape)

Goal: make the “defend yourself with words” fantasy feel real.

Start with five archetypes:
- boundary-setting
- negotiation
- asking for help
- de-escalation
- refusal

For each archetype:
- define 3–5 canonical intents
- define escalation/resolution rules
- add scenario tags so import/compiler can choose patterns

### M5 — Import Expansion (authorized sources)

Goal: broaden story sources while keeping ingestion predictable.

- Direct media URLs (mp4/webm) via FFmpeg extraction (already present in backend image)
- “Paste transcript” remains the lowest-friction path
- Defer complex scraping (sites that require extra tooling) until after MVP stability

### M6 — Security, Abuse Prevention, and Best Practices

Goal: keep “import anything + share links” safe, cheap, and maintainable as we scale.

Deliverables:
- **Threat model + trust boundaries** for: URL/text import, video ingest (`ffmpeg`/`yt-dlp`), publish/share, local saves, and WebSockets.
- **SSRF + redirect safety**: block private/loopback/link-local hosts, validate redirects, cap bytes/time, and document allow/deny rules (esp. for free/demo tiers).
- **Resource controls** (cost + DoS): request size caps, timeouts, concurrency limits, and sane defaults for “free trial” behavior.
- **Web security posture**: tighten CORS for production, plan CSRF strategy (when auth lands), and add secure headers via reverse proxy (CSP/HSTS/XFO/etc.).
- **WebSocket hardening**: validate init payloads, apply origin checks (when feasible), chunk rate/size limits, and clean session teardown.
- **Secrets + logging hygiene**: ensure keys never reach the client, avoid logging sensitive content, define retention for caches/usage logs/published runs.
- **Supply-chain guardrails**: dependency audit, pinning strategy, and CI checks (secret scanning + basic SAST).

## Test Plan (minimum bar)

Use `bash tests/test_all.sh` for CI-style confidence.

- Contract tests:
  - import returns a chain with at least one advanced scene
  - language inference + override works (EN/ES/JA)
  - judge slider changes behavior (at least one measurable change)
- Regression tests:
  - score/lives do not reset across scenario transitions
  - streaming penalties honor judge slider thresholds
- Manual smoke:
  - follow `development/demo-smoke.md` and add an “import → play” path
