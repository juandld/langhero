# Current Plans

 _Last updated: 2025-12-25 03:25 UTC_

## North Star (UX)

See `development/ux.md` for the full vision. The working north-star checklist:

1. **Two difficulty loops**: time-stop rehearsal (beginner) → live streaming response (advanced).
2. **Clear risk boundary**: only the main mic action can burn lives; prep tools are always safe.
3. **Live comprehension cues**: show what the system hears (transcript + confidence) and make penalties actionable.
4. **Two voice personas**: assistant voice for tools; NPC/world voice for in-scene lines (no cross-contamination).
5. **Cheap demo loop**: free runs stay near-zero marginal cost (pre-baked scenarios + mock streaming; strict gating on expensive imports/ASR).

## What’s In Dev Now

- M4 “mode toggle” exists end-to-end: scenario JSON carries `mode`/`lives`/`reward_points`/`penalties`; backend streaming events + REST include `scoreDelta`/`livesDelta`; UI swaps between time-stop and streaming HUD states.
- Run state (score/lives) now persists per saved run (localStorage-backed) and is carried into streaming session init so it doesn’t reset when switching modes.
- Interaction responses now include best-effort `confidence` + `match_type`; UI renders a confidence meter in the HUD.
- Manual demo route added: `/demo` jumps between beginner + advanced scenarios.
- Frontend unit test harness started (Vitest) with `storyStore` coverage.
- Story import v0 exists: `/import` route posts to `POST /api/stories/import` (text-only) and swaps `storyStore` to the returned scenario list.
- “North star knobs” landed: judge focus slider (learning ↔ story) plus target language override (auto/EN/ES/JA) wired through both REST and streaming.
- Voice clip pipeline exists (manifest-backed cache + ops generator + pytest reasoning tests); role-aware voices are the next step.
- Codebase orientation + contracts docs exist: `development/code-map.md`, `development/contracts.md`. Test runner exists: `bash tests/test_all.sh`.

## Current Focus (Next 1–3 chunks)

1. **MVP Cohesion Pass (north star progression)**
   - Stop resetting run state on scenario changes (score should persist across a run; lives behavior should be explicit and consistent across modes).
   - Ensure imported stories start with a time-stop scene and then introduce streaming pressure (at least one `advanced` node).
   - Expand the `/demo` and `/import` smoke flow to cover: judge slider extremes + language override + streaming on/off.
   - Use `development/north-star-execution.md` as the canonical milestone breakdown.

1b. **Import Scaling + Waste Reduction (ops posture)**
   - Define caching scope (per-user vs per-org vs global opt-in for published artifacts only).
   - Move video import (`/api/scenarios/from_video`) to async jobs with quotas and clear status reporting.
   - Add transcript + scenario compile caching (start per-user) to reduce repeated transcription/LLM spend.
   - Keep imports private-by-default; publish/share remains explicit and shares compiled Scenario[] only.
   - See `development/import-scaling.md`.

2. **M5 Confidence & Lives Feedback (north-star cue loop)**
   - Define confidence thresholds + payload shape for both `/narrative/interaction` and streaming “final” events.
   - Implement confidence meter + retry messaging in the HUD; ensure safe tools never decrement lives.
   - Add regression tests for “wrong language burns lives”, “translate does not”, and “streaming auto-finalize updates deltas”.

3. **Interaction Taxonomy v0 (defense/escape dialog)**
   - Add `archetype` tags to options/scenes (boundary-setting, negotiation, asking for help, de-escalation, refusal).
   - Teach the judge to prefer outcomes consistent with the selected archetype and current scene goal.

4. **Voice Personas (north-star audio rule)**
   - Extend schema + APIs to carry `voice_role`/`speaker_id`; make `/api/tts` role-aware.
   - Key the voice cache/manifest by role so assistant/NPC voices never reuse the same clip id.
   - Expand `operations/scripts/generate_voices.py` to pre-render both roles; add pytest ensuring identical text yields different `clip_id`s across roles.

5. **M2 Provider Shoot-out Harness**
   - Create `development/notes/provider-benchmarks.md` (logbook target) and a harness script that outputs latency/accuracy summaries for fixed audio fixtures.

## Operator Notes
- Project Upgrade workflow kicked off; `operations/scripts/instant_context.py` now prints this plan plus the task board.
- Use `./tests/test.sh` before every hand-off to keep regression coverage honest.
- Use `npm run test:run` under `frontend/` for the frontend unit suite.
- Capture session timestamps in `development/task_board.md` and summarize outstanding risks in chat + docs.
- FastAPI now uses lifespan events (no more `@app.on_event` warning); update any future routes to follow the same pattern.
- 2025-12-20 — Added HUD SSR component tests + `/demo` smoke checklist; re-verified `./tests/test.sh` (19 pass) and `npm run test:run` under `frontend/` (12 pass).
- 2025-12-18 — Added `/demo` route + Vitest `storyStore` tests; re-verified `./tests/test.sh` (19 pass).
- 2025-12-05 — Centralized scenario scoring defaults in `backend/config.py` and documented the initial progression table; see `development/scenario-progression.md`.
- 2025-12-05 — Added reusable beginner/advanced scenario fixtures (`tests/fixtures/scenarios.py`) and expanded streaming session tests (13 pass).
- 2025-12-05 — Created `operations/scripts/generate_voices.py` + README notes so scenario voice clips can be batch-generated with OpenAI TTS.
- Voice clip dedupe/variation plan lives in `development/voice-generation.md`; task is tracked on the board (manifest reuse, ≤4 variants, reasoning tests).
- 2025-12-05 — Manifest-backed voice caching + pytest coverage (`tests/voice_generation_test.py`) landed; canonical clips now have UUID `clip_id`s with scenario mappings in `examples_audio/scenario_clips.json`.

## Blockers / Needs
- Need final UX acceptance for HUD states + penalty copy before the M5 work can be merged.
- Provider benchmarking needs a `development/notes/` scratchpad target (create + start logging results).
  - Added `development/notes/provider-benchmarks.md` and a harness script: `python3 backend/provider_benchmark.py --file ...`.
