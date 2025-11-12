# Testable Milestones

Concrete checkpoints that unlock quick feedback and let us iterate safely. Each milestone includes a validation plan so we can demo or automate before moving on.

## M1. Mock Streaming Loop

- [x] Implement FastAPI WebSocket endpoint that echoes back chunk metadata and fake partial transcripts.
- [x] Add pytest to feed sample audio chunks and assert event sequence (`partial`, `final`).
- [x] Frontend (dev-only) client that streams microphone data to the mock endpoint and renders responses.
- **Test:** Run `bash tests.sh`; in the browser load `/?mockStream=1` to verify live mock updates while recording.

## M2. Provider Shoot-out Harness

- [ ] Create backend adapter interface with pluggable providers (Gemini, OpenAI, Whisper local).
- [ ] Write scripts to stream fixed test audio through each provider, recording latency and accuracy metrics.
- [ ] Store results in `development/notes/provider-benchmarks.md`.
- **Test:** Run harness, output CSV/JSON summary; add basic regression test ensuring harness exits 0 and produces metrics file.

## M3. Streaming Transcript Prototype

- [x] Swap mock transcription in WebSocket handler for chosen provider (or Whisper fallback) using small chunk windows.
- [x] Persist rolling transcript on backend; broadcast incremental updates to client.
- [x] Frontend renders live transcript in HUD while maintaining current time-stop UI for non-streaming levels.
- [x] **Test:** Integration test with prerecorded audio verifying transcript convergence; manual UI test to confirm live updates appear without stopping recording.

## M4. Scenario Mode Toggle

- [ ] Extend scenario JSON with `mode` field and per-mode defaults (`reward_points`, `penalties`).
- [ ] Update backend responses to surface `mode`, reward, and penalty metadata.
- [ ] Teach `storyStore` to expose `mode`, default lives, and reward values.
- [ ] Provide storybook/demo scenario to exercise both paths.
- **Test:** Unit tests for `storyStore` mode handling; Cypress (or Playwright) smoke test hitting both modes with stubbed backend.

## M5. Confidence & Lives Feedback

- Backend sends confidence scores with each update; define thresholds per mode.
- Frontend displays confidence meter and decrements lives on low-confidence outcomes.
- Log events for telemetry (success, retries, disconnects).
- **Test:** Vitest/Svelte component tests for `ScenarioStatus` (score/lives banner) and `ScenarioDisplay` penalty handling; integration test simulating low/high confidence and wrong-language responses.

## M6. Production Hardening

- Add reconnection logic, buffering, and error states to streaming client.
- Implement server-side rate limiting/logging + health checks.
- Document deployment checklist in `development/README.md`.
- **Test:** Automated chaos test (network toggle) ensuring client recovers; backend load test with concurrent sessions.
