# Streaming Architecture

## Goals

- Deliver near-live transcription and intent feedback during advanced scenarios.
- Keep latency low (sub-second updates) while handling network variability gracefully.
- Maintain compatibility with existing backend APIs for time-stop mode.
- Mirror time-stop scoring: reward correct turns, emit life-loss penalties for wrong language/answers, and surface the same `scoreDelta`/`livesDelta` contract over WebSocket events.

## Workstream Breakdown

1. **Provider Capability Audit**
   - Evaluate Gemini, OpenAI, and alternatives for streaming ASR + intent.
   - Identify per-chunk latency, token limits, and cost implications.

2. **Backend Transport**
   - Add FastAPI WebSocket endpoint for `/stream/interaction`.
   - Buffer audio chunks, run streaming transcription, emit events (partial transcript, confidence, intents).
   - Implement fallback to HTTP POST when streaming unavailable.
    - Session tracks `score`, `lives_total`, `lives_remaining`; applies scenario-configured reward/penalty values and pushes them with `ready`, `penalty`, and `final` events.

3. **Frontend Streaming Client**
   - Capture audio chunks via `MediaRecorder` (or AudioWorklet for tighter control).
   - Send chunks over WebSocket, render partial feedback, manage retries.
   - Synchronize with `storyStore` to trigger progression once confidence threshold met.
    - Update HUD when `penalty`/`final` events carry `score`/`lives` deltas; auto-disable repeat mode when lives hit zero.

4. **State Coordination**
   - Shared protocol: event types (`ready`, `partial`, `penalty`, `final`, `reset`, `error`).
   - Every event includes `score`, `lives_remaining`, `lives_total`; `penalty` exposes `type` (`wrong_language`, `incorrect_answer`) so UX can tailor messaging.
   - Store last-known transcript/confidence for later review or analytics.

5. **Resilience & Metrics**
   - Reconnect logic, jitter buffers, incremental backoff.
   - Log RTT, error rates; expose basic telemetry for tuning.
    - Emit telemetry for score/life changes to analyze per-scenario difficulty.

## Action Items

- [ ] Schedule provider shoot-out with latency + cost benchmarks.
- [ ] Design WebSocket message contract and document it.
- [ ] Build prototype FastAPI WebSocket handler with mocked transcription.
- [ ] Implement frontend streaming client (feature-flagged) and smoke test.
- [ ] Define monitoring/telemetry events for streaming sessions.
- [x] Auto-finalize when partial transcript confidence is high and lives remain (reduce stop gesture friction).
- [ ] Support per-scenario override for penalty severity (e.g., language mismatch costs more lives at higher difficulty).
- [ ] Add regression tests covering score/life propagation across both time-stop and streaming flows.
- [ ] Add unit tests for websocket session scoring (points, penalties) with scenario overrides.
- [ ] Instrument time-stop unit tests to cover language mismatch prompts and per-scenario reward fallbacks.

## Dependencies

- UX decisions from [UX Vision](./ux.md).
- Mode switching logic from [Scenario Progression](./scenario-progression.md).

## Open Questions

- Provider streaming API availability/cost.
- Whether to host fallback Whisper streaming locally.
- How to handle privacy/legal requirements for live audio.

## Links

- [UX Vision](./ux.md)
- [Scenario Progression](./scenario-progression.md)
- [Open Questions](./open-questions.md)
