# Code Map (Quick Orientation)

This is a short “where do I look?” guide for LangHero so changes don’t get lost across frontend/backend.

## Frontend

**Routes**
- `frontend/src/routes/+page.svelte` — main entry (plays the active story).
- `frontend/src/routes/import/+page.svelte` — import story text into playable scenarios.
- `frontend/src/routes/demo/+page.svelte` — dev-only mode toggle demo (beginner vs advanced).

**Core state**
- `frontend/src/lib/storyStore.js`
  - `storyStore.loadScenarios(list)` swaps the active scenario list (imported story).
  - `storyStore.useBuiltInScenarios()` returns to bundled demo scenarios.

**Main gameplay UI**
- `frontend/src/lib/components/ScenarioDisplay.svelte`
  - Orchestrates mic recording, REST calls, streaming websocket, and renders HUD.
  - Persists `JUDGE_FOCUS` and `LANGUAGE_OVERRIDE` in `localStorage`.
- `frontend/src/lib/components/scenario/ScenarioOptionsPanel.svelte`
  - Prep tools + “judge focus” slider + “target language override” dropdown.

**Backend connectivity**
- `frontend/src/lib/config.ts` — resolves backend URL + streaming mode flags.

## Backend

**API entry points**
- `backend/main.py`
  - `POST /api/stories/import` — text import (v0) → scenarios list.
  - `POST /narrative/interaction` — time-stop interaction judging.
  - `WS /stream/interaction` — streaming interaction loop (partial/penalty/final).

**Core logic**
- `backend/services.py`
  - `process_interaction(...)` — transcribe + option match + score/lives result.
  - `generate_scenarios_from_transcript(...)` — LLM scenario generation (best-effort).
- `backend/streaming.py`
  - `StreamingSession` — manages chunk buffering, partial transcript, penalties, auto-finalize.

## Tests

**Backend**
- `tests/process_interaction_test.py` — scoring/lives + judge slider regression.
- `tests/story_import_test.py` — import contract + language inference/override.
- `tests/streaming_session_test.py` / `tests/streaming_interaction_test.py` — websocket loop behavior.
- Run all suites: `bash tests/test_all.sh`

**Frontend**
- `frontend/src/lib/storyStore.test.js` — store behavior for imports and history.
- `frontend/src/lib/components/scenario/*.test.js` — SSR render tests for HUD pieces.
