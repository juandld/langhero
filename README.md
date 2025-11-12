# LangHero

An interactive learning app (separated from Narrative Hero) that runs branching scenarios with voice input. It also ships a notes backend (upload, transcribe, title, tag, and generate narratives) that the current UI does not fully wire up yet. Tech stack: SvelteKit (frontend) + FastAPI (backend) + LangChain (Gemini/OpenAI).

## Features

- Branching scenarios with microphone input (scenario demo UI)
- In‑browser recording and server‑side transcription + title generation
- Gemini 2.5 Flash primary with OpenAI fallback and key rotation
- Notes API with tags, filtering fields, and narrative generation (backend)
- Simple scenario store loaded from JSON (frontend and backend)

## MVP Scope

Focus for the first playable slice:

- **Two guided scenarios**: one beginner (time-stop) and one advanced (streaming) that share the same reward/penalty contract via `reward_points` and `penalties.*` in scenario JSON.
- **Score & lives HUD**: the streaming WebSocket and the `/narrative/interaction` POST both emit `scoreDelta`/`livesDelta`; the Svelte UI mirrors those updates immediately.
- **Language coaching**: speaking in the wrong language triggers a retry prompt with life loss and a recommended line.
- **Regression tests**: pytest suites cover scoring/lives logic for both time-stop and streaming paths (`tests/process_interaction_test.py`, `tests/streaming_session_test.py`).
- **Next up (testing)**: add Vitest-based HUD/store tests, Playwright smoke runs, and a provider harness to benchmark streaming latency.
- Streaming auto-finalizes once the learner’s partial transcript confidently matches a scenario option; manual “stop” remains as a fallback.

Nice-to-haves after the MVP lands: streaming auto-finalize when confidence is high, confidence meter visuals, and Cypress/Playwright end-to-end smoke tests.

## Tech Stack

- Frontend: SvelteKit (TypeScript)
- Backend: FastAPI (Python) + LangChain (Gemini/OpenAI)
- Containerization: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose (recommended for prod)
- Node.js and npm (frontend dev)
- Python 3.9+ and pip (backend dev)
- API keys: Google AI (Gemini). Optional: OpenAI (fallback + narrative)
- Optional: FFmpeg (improves audio format handling locally)

## Running the Project

### Production (using Docker)

This is the recommended way to run the project.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd langhero
    ```

2.  **Create a `.env` file (backend):**
    ```ini
    # Primary Gemini key
    GOOGLE_API_KEY="your-gemini-key-A"
    # Optional extra Gemini keys for rotation
    GOOGLE_API_KEY_1="your-gemini-key-B"
    GOOGLE_API_KEY_2="your-gemini-key-C"
    GOOGLE_API_KEY_3="your-gemini-key-D"

    # Optional: OpenAI fallback (LangChain)
    OPENAI_API_KEY="your-openai-key"

    # Optional: override models
    # Default target is Gemini 2.5 Flash. You can specify human-friendly names
    # (e.g., "gemini 2.5 flash" or "gemini-2.5-flash-002"); the backend
    # normalizes spaces and version suffixes to a compatible form.
    # If you need an exact model id with no normalization, set GOOGLE_MODEL_EXACT.
    # GOOGLE_MODEL="gemini 2.5 flash"
    # GOOGLE_MODEL_EXACT="gemini-2.5-flash"
    # OPENAI_TRANSCRIBE_MODEL="whisper-1"
    # OPENAI_TITLE_MODEL="gpt-4o-mini"
    # OPENAI_NARRATIVE_MODEL="gpt-4o"
    ```

3.  **Build and run the application with Docker Compose:**
    ```bash
    docker compose up --build
    ```

4.  **Access the application:**
    The frontend will be available at `http://localhost`.

### Local Development

Run both services together or separately.

#### Run both (convenience)

From project root:

```bash
./dev.sh
```

#### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create `.env` (see example above).**

3.  **Run the development script:**
    ```bash
    ./dev.sh
    ```
    Starts FastAPI at `http://localhost:8000`.

#### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the frontend development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:5173`.
    Backend URL is configured in `frontend/src/lib/config.ts`.

## Testing

- Run `tests/test.sh` from the repo root to exercise the current streaming loop integration tests. The script picks a compatible Python (3.10+) and expects the FastAPI dependencies from `backend/requirements.txt`.
- The harness invokes `pytest` (configured in `pytest.ini`) and installs any extra tooling listed in `tests/requirements.txt` when needed.
- The streaming mock harness used in tests aligns with Milestone M1; as additional milestones land, extend the script so we keep regression coverage close to the plan.

## Project Structure

- `frontend/` SvelteKit app (scenario demo UI and components)
- `backend/` FastAPI app
  - `config.py` central env and models
  - `providers.py` Gemini/OpenAI helpers + key rotation
  - `services.py` transcription/title + notes listing logic
  - `main.py` API routes
- `voice_notes/` recorded audio files (uploads)
- `transcriptions/` JSON note metadata and text
- `narratives/` generated narrative `.txt` files
- `compose.yaml` Docker Compose services

## Note JSON Schema

Each audio file in `voice_notes/` (wav/ogg/webm/m4a/mp3) has a corresponding `transcriptions/<base>.json`:

```json
{
  "filename": "20250923_140154.wav",
  "title": "Quick standup notes",
  "transcription": "We discussed…",
  "date": "2025-09-23",
  "length_seconds": 42.5,
  "topics": ["standup", "team", "progress"],
  "tags": [{ "label": "work", "color": "#3B82F6" }]
}
```

On startup, any legacy `.txt`/`.title` are consolidated into JSON. Missing metadata is backfilled.

## Backend Behavior

- Transcription providers
  - Primary: Gemini via LangChain (key rotation on 429/quota)
  - Fallback: LangChain OpenAI Whisper/Chat (when configured)
- Startup backfill (non-blocking)
  - Migrates legacy files to JSON
  - Creates JSON for `.wav` lacking one
  - Does not re-transcribe if JSON exists (delete JSON to force refresh)
- Usage logging
  - Daily JSONL and weekly JSON in `backend/usage/` (git-ignored)

## API Overview

- Notes
  - GET `/api/notes` → list with metadata (title, transcription, date, length, topics, tags)
  - POST `/api/notes` (multipart: `file`) → save audio; transcribe/title in background
    - Accepts common audio types: wav, ogg, webm, m4a, mp3
  - POST `/api/notes/{filename}/retry` → queue reprocessing for a specific note
  - DELETE `/api/notes/{filename}` → delete audio + JSON
  - PATCH `/api/notes/{filename}/tags` → `{ "tags": [{"label":"…","color":"#…"}] }`
- Narratives
  - GET `/api/narratives` → list filenames
  - GET `/api/narratives/{filename}` → `{ content }`
  - DELETE `/api/narratives/{filename}`
  - POST `/api/narratives` → body `[{"filename":"…wav"}, …]` creates concatenated narrative (simple join)
  - POST `/api/narratives/generate` → generate via LLM
    - Body: `{ items: [{ filename: "…wav" }], extra_text?: string, provider?: "auto"|"gemini"|"openai", model?: string, temperature?: number, system?: string }`
    - Uses Gemini (with key rotation) by default and falls back to OpenAI when provider=`auto`
- Scenarios (demo)
  - POST `/narrative/interaction` → simple yes/no branching using speech intent
  - GET `/narrative/options?scenario_id=ID&n_per_option=3` → generate kid‑friendly example phrases for each option in the scenario
  - POST `/api/scenarios/from_video` → `{ url, target_language?: "Japanese", max_scenes?: 5, activate?: true }` extracts audio with FFmpeg, transcribes, and generates a branching scenario using the LLM; optionally activates it.

## Frontend Status

- Scenario demo UI lives at `frontend/src/routes/+page.svelte` and uses `ScenarioDisplay.svelte` with microphone input hitting `/narrative/interaction` and speaks options fetched from `/narrative/options`.
- Scenario JSON lives at `frontend/src/lib/test/scenarios.json` (frontend) and `backend/scenarios.json` (backend intent logic).
- `frontend/src/lib/config.ts` hosts `BACKEND_URL` (default `http://localhost:8000`).
- You can set per‑scenario language by adding `language` to each scenario; the frontend passes it to the backend for better transcription.

## Development Playbook

- High-level product direction lives in `ROADMAP.md`.
- Detailed design and engineering notes live under `development/`. Start with `development/README.md` for the latest index and action items.
- When you open a new plan or retire one, cross-link it in the development index so decisions stay connected.

### Planning Docs

- [development/ux.md](development/ux.md) — UX vision, including how time-stop versus streaming states should feel.
- [development/scenario-progression.md](development/scenario-progression.md) — schema changes and rules for moving learners between modes.
- [development/streaming-plan.md](development/streaming-plan.md) — WebSocket architecture, provider audit, and telemetry expectations.
- [development/testable-milestones.md](development/testable-milestones.md) — running checklist of engineering milestones and associated tests.
- [development/open-questions.md](development/open-questions.md) — research topics awaiting decisions; add owners as answers appear.

### Milestones Snapshot

- **M1 Mock Streaming Loop** (done) FastAPI WebSocket echo path with mocked transcript; dev-only UI flag to preview.
- **M2 Provider Shoot-out Harness** (planned) Stand up adapters and latency benchmarks for Gemini/OpenAI/Whisper and log results to `development/notes/provider-benchmarks.md` once that scratchpad file exists.
- **M3 Streaming Transcript Prototype** (done) Replace mocks with real streaming provider and surface live transcript in the HUD.
- **M4 Scenario Mode Toggle** (up next) Extend scenario JSON with `mode`, propagate through backend responses, and swap frontend controls based on mode.
- **M5 Confidence & Lives Feedback** (up next) Deliver confidence meter, lives UI, and logging for retries/success.
- **M6 Production Hardening** (up next) Add reconnection logic, rate limiting, health checks, and document deployment checklists.

Feel free to mark progress directly in `development/testable-milestones.md` as items land—tests and docs should move in lockstep.

### Open Questions To Track

- Streaming ASR provider trade-offs (latency, reliability, cost) and whether on-device fallback is needed.
- Privacy posture for storing streaming transcripts.
- UX treatments for communicating lives/confidence in live mode.
- Teacher/coach overrides for difficulty in real time.

Capture updates in [development/open-questions.md](development/open-questions.md) so we can resolve, assign owners, or archive decisions.

## Generate Scenarios from a Video

Backend can create a simple branching scenario from a video URL using FFmpeg + LLM:

```
curl -X POST http://localhost:8000/api/scenarios/from_video \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com/path/to/video.mp4",
    "target_language": "Japanese",
    "max_scenes": 5,
    "activate": true
  }'
```

Notes:
- FFmpeg is installed in the backend image. For YouTube or streaming sites, consider adding `yt-dlp` and piping bestaudio to FFmpeg in a future enhancement.
- Generated scenarios are activated by default; use `/api/scenarios` to inspect the active list or `/api/scenarios/import` to replace manually.
- Notes UI components (e.g., `NotesList.svelte`, `FiltersBar.svelte`, `BulkActions.svelte`, `NarrativesDrawer.svelte`) are present but not currently wired into a route. The backend APIs are ready when you choose to surface them.

## Tips

- Use multiple Gemini keys to smooth through quota spikes
- Add OpenAI key for reliable fallback (transcribe/title and narrative generation)
- To reprocess a note, use `/api/notes/{filename}/retry` or delete its JSON; backend will recreate it on startup or next upload
- FFmpeg with pydub improves audio format handling (pydub installed; add FFmpeg if needed)

## Scenario Progression UX

- See [development/scenario-progression.md](development/scenario-progression.md) for the latest rules and guardrails.
- **Early levels:** Players can pause (press-and-hold mic) to plan, translate, and rehearse before speaking. Audio is processed while they hold the button; releasing it commits the attempt. Limited “lives” per scenario emphasize accuracy.
- **Advanced levels:** The time-stop advantage disappears. Streaming kicks in as soon as the learner speaks, requiring faster recall and making live comprehension the core skill. Planning tools remain, but they must be used on the fly.
- This progression helps learners transition from deliberate practice to real-time conversation under gentle pressure.
- Scoring/lives: scenarios now specify `mode`, `lives`, `reward_points`, and `penalties` (e.g., `incorrect_answer.lives`, `language_mismatch.points`). Both the WebSocket stream and `/narrative/interaction` respond with `scoreDelta` / `livesDelta`, keeping the HUD in sync across modes.
