# Contracts (Frontend ↔ Backend)

Keep these payloads stable; add a regression test when they change.

## Scenario object (UI relies on these fields)

Minimum fields used today:
- `id: number`
- `mode: "beginner" | "advanced"` (defaults to `beginner`)
- `lives: number`
- `reward_points: number`
- `penalties: object` (shape varies; see below)
- `language?: string` (e.g., `"English"`, `"Spanish"`, `"Japanese"`)
- `character_dialogue_en?: string`
- `character_dialogue_jp?: string`
- `description?: string`
- `options?: Array<{ text: string, next_scenario?: number|null, keywords?: string[], examples?: Array<{native?:string,target?:string,pronunciation?:string}> }>`

## Interaction result (`POST /narrative/interaction`)

Frontend expects (subset):
- `heard?: string`
- `nextScenario?: object | number`
- `scoreDelta?: number`
- `livesDelta?: number`
- `confidence?: number` (0..1, match confidence)
- `match_type?: string` (best-effort label for how the match was chosen)
- `message?: string`
- `error?: string`
- `npcDoesNotUnderstand?: boolean`
- `repeatExpected?: string`
- `pronunciation?: string`
- `repeatNextScenario?: number`

Request fields:
- multipart form fields: `audio_file`, `current_scenario_id`, optional `lang`, optional `judge` (0..1)

## Streaming websocket (`WS /stream/interaction`)

Client → server init payload:
- `scenario_id?: number`
- `language?: string` (target language)
- `judge?: number` (0..1)
- `score?: number` (optional run score to carry across scenes)
- `lives_remaining?: number` (optional run lives to carry across scenes)

Server → client events:
- `ready`: `{ event, scenario_id, target_language, mode, lives_total, lives_remaining, score, ... }`
- `partial`: `{ event, seq, transcript, detected_language, target_language }`
- `penalty`: `{ event, type, lives_delta, lives_remaining, lives_total, score, message, ... }`
- `final`: `{ event, result, target_language, mode, score, lives_remaining, lives_total }`

## Story import (`POST /api/stories/import`)

Request JSON:
- `text?: string` (v0 supported)
- `source_url?: string` (web page URL; server fetches and extracts text)
- `setting?: string` (hint for language inference)
- `target_language?: string` (override)
- `max_scenes?: number` (1..12)
- `activate?: boolean` (write into backend scenario store)
- `attest_rights?: boolean` (required)

Response JSON:
- `scenarios: Scenario[]`
- `target_language: string`
- `activated: boolean`
- `source?: { url?: string, final_url?: string, title?: string, content_type?: string }`

## Unified import (`POST /api/import/auto`)

Request JSON:
- `url?: string` (recommended; auto-detect web vs video)
- `text?: string` (optional extra context/prompting)
- `setting?: string`
- `target_language?: string`
- `max_scenes?: number`
- `activate?: boolean`
- `attest_rights: true` (required)

Response JSON:
- `kind: "video" | "web" | "text"`
- `scenarios: Scenario[]`
- `target_language: string`
- `activated: boolean`
- `url?: string`
- `source?: { url?: string, final_url?: string, title?: string, content_type?: string }` (when kind is `web`)
- `cached?: boolean` and `cache_saved?: boolean` (when kind is `video`)

## Video import (`POST /api/scenarios/from_video`)

Request JSON:
- `url: string`
- `target_language?: string` (defaults server-side; UI should send an explicit value)
- `max_scenes?: number`
- `activate?: boolean` (keep `false` for “create run” UX; `true` replaces backend scenario store)
- `attest_rights: true` (required)

Response JSON:
- `scenarios: Scenario[]`
- `count: number`
- `activated: boolean`
- `cached: boolean` (true if served from cache)
- `cache_saved: boolean` (true if a cache entry was written)

## Dev meta + usage (dev tools)

### Meta (`GET /api/meta`)

Response JSON:
- `demo_mode: boolean`
- `demo_video_cache_only: boolean`
- `demo_allow_llm_import: boolean`
- `demo_disable_streaming: boolean`
- `utc_now: string` (ISO timestamp)

### Weekly usage (`GET /api/usage/weekly`)

Response JSON (subset):
- `totals.events: number`
- `providers: Record<string, number>`
- `events: Record<string, number>`
- `models: Record<string, number>`
- `by_event_provider_model: Record<"event|provider|model", number>`

### Recent usage (`GET /api/usage/recent?limit=200&days=7`)

Response JSON:
- `limit: number`
- `days: number`
- `events: Array<{ timestamp?: string, event?: string, provider?: string, model?: string, key?: string, status?: string }>`

## Published runs (explicit share flow)

Private-by-default runs may be published as a **compiled Scenario[] artifact** for sharing. This is not the same as story import: publishing makes content publicly retrievable via an id.

### Create (`POST /api/published_runs`)

Request JSON (minimum):
- `title: string`
- `target_language?: string`
- `scenarios: Scenario[]`
- `attest_rights: true` (required)
- `confirm_publish: true` (required)

Response JSON:
- `public_id: string`
- `delete_key: string` (secret; returned only on create)
- `title: string`
- `target_language: string`
- `created_at_ms: number`
- `scenarios: Scenario[]`

### Fetch (`GET /api/published_runs/{public_id}`)

Response JSON:
- `public_id: string`
- `title: string`
- `target_language: string`
- `created_at_ms: number`
- `scenarios: Scenario[]`

### Delete (`DELETE /api/published_runs/{public_id}`)

Request JSON:
- `delete_key: string` (required)

Response JSON:
- `{ status: "ok" }`

## Penalties config (scenario JSON)

Common shape:
- `penalties.language_mismatch.lives: number`
- `penalties.language_mismatch.points?: number`
- `penalties.incorrect_answer.lives: number`
