# Import Scaling & Waste Reduction

This doc describes what resources the import pipeline consumes, how it scales, and how to reduce waste when users import the same or similar stories.

Scope: story import (`POST /api/stories/import`) and video import (`POST /api/scenarios/from_video`), plus share/publish of compiled artifacts (`/api/published_runs`, `/share/[id]`).

## Why this matters

Import is intentionally a “story seed → playable run compiler,” not a content hosting feature. The expensive parts of that compiler (download/transcribe/LLM) must be budgeted, rate limited, and cached to avoid runaway cost and latency.

## Resource model (what costs what)

### Text import (`POST /api/stories/import`)

Main costs:
- **LLM compile**: tokens + latency.
- Minimal CPU/memory beyond JSON assembly.

Primary scaling limit:
- Provider quotas / concurrency (API-bound).

### Web page import (`POST /api/stories/import` with `source_url`)

Pipeline:
1. Fetch page bytes (bandwidth).
2. Extract visible text from HTML (CPU-light).
3. Compile text → Scenario[] (LLM).

Main costs:
- Bandwidth (typically small).
- LLM compile tokens + latency (dominant).

Primary scaling limit:
- Provider quotas / concurrency (API-bound), plus basic SSRF-safe URL validation.

### Video import (`POST /api/scenarios/from_video`)

Pipeline:
1. Resolve/obtain media (e.g., YouTube via `yt-dlp`).
2. Decode + resample audio (ffmpeg).
3. Transcribe audio to text.
4. Compile transcript → Scenario[] (LLM).

Guardrail:
- Require `attest_rights: true` (user confirms they have permission to use the URL/content).

Main costs:
- **Bandwidth** for downloading/streaming the source media.
- **CPU** for ffmpeg decode/resample.
- **Transcription** is usually the dominant cost.
- LLM compile is second-order but still meaningful.

Primary scaling limits:
- Download bandwidth + job concurrency.
- Transcription provider quotas + latency.
- Worker capacity (CPU + memory) for ffmpeg + transcription throughput.

### Publish/share compiled runs (`/api/published_runs`, `/share/[id]`)

Main costs:
- Storage + bandwidth for serving **compiled Scenario[] JSON**.
- Low compute. No transcription/LLM cost at share-time if we only share the compiled artifact.

Primary scaling limit:
- Storage and retrieval volume (generally cheap).

## Waste reduction (caching/dedupe layers)

Reduce cost by caching each stage with two fingerprints:
- **Content fingerprint**: “what was imported?”
- **Config fingerprint**: “how did we process it?” (language/model/max scenes/version)

### Layer 0 — Source download cache (video URLs)

Key:
- `source_provider + source_id + format`
  - Example: `youtube + video_id + bestaudio`

Saves:
- Bandwidth and repeated download/resolve overhead.

Notes:
- Storing raw media can increase policy/compliance burden; consider TTL caches and/or storing only derived artifacts.

### Layer 1 — Extracted audio cache

Key:
- `download_hash + sample_rate + channels + codec`

Saves:
- CPU time (ffmpeg decode/resample).

### Layer 2 — Transcript cache

Key:
- `audio_hash + provider + model + language_hint + transcript_version`

Saves:
- The biggest cost bucket (transcription).

### Layer 3 — Scenario compile cache

Key:
- `transcript_hash + target_language + max_scenes + compiler_prompt_version`

Saves:
- LLM compile tokens and latency.

### Layer 4 — Similar story reuse (approximate dedupe)

Technique:
- Embedding/similarity search over derived text (transcript or a redacted summary).
- Reuse a “scenario skeleton” (scene goals + option archetypes) and re-skin.

Saves:
- Further LLM work for highly similar imports.

Risk:
- Cross-user similarity reuse can leak sensitive/private content unless it is scoped or consented.

## Privacy/IP posture (how to share without increasing risk)

Privacy regimes (GDPR/HIPAA posture) are **not** an IP shield. To align with the product intent:

- Default is **private practice**: user content is not publicly retrievable.
- Publishing is **explicit**, with clear confirmation friction.
- Prefer sharing **compiled Scenario[]** rather than the raw imported source text/media.
- Maintain deletion controls (GDPR style) and a publish delete key for shared artifacts.

### Cache scope options (choose one, document it)

1. **Per-user cache (safest default)**
   - Dedup only within the same user’s account.
2. **Per-org cache**
   - Dedup within a workspace/org boundary.
3. **Global cache (highest savings)**
   - Only for *published* artifacts or opt-in de-identified templates.
   - Avoid cross-tenant reuse of raw text/transcripts.

## Operational controls required for scaling

At minimum:
- **Quotas**: imports per day, max minutes/day, concurrency per user.
- **Limits**: max duration, max size, timeouts, retry policies.
- **Job queue**: make video imports async; expose status to UI.
- **Budget controls**: provider concurrency, circuit breakers, and fallback behavior.
- **Telemetry**: stage timings + cache hit rates + provider usage.

## Recommended implementation order

1. **Async jobs** for video import (`from_video`): queue + status + result fetch.
2. **Transcript + scenario compile cache** (Layer 2/3) scoped per user/org first.
3. **Publish artifacts** only share compiled Scenario[] (already aligned with `/api/published_runs`).
4. Consider Layer 0/1 caching only if policy allows and if measured bandwidth/CPU becomes material.
5. Add optional global/opt-in “template reuse” only after privacy boundaries are locked.
