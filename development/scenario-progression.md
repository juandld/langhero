# Scenario Progression

## Summary

- Early levels operate in time-stop mode with planning aids and limited attempts.
- Advanced levels stream audio immediately, removing the pause safety net.
- Progression guides learners from deliberate rehearsal to real-time response.

## Implementation Outline

1. **Data Model**
   - Add a `mode` / `difficulty` field to scenario JSON (frontend + backend copies).
   - Default to `beginner`; mark advanced nodes explicitly.
   - Surface mode metadata through the API so the client can react instantly.
   - Support per-scenario `reward_points` and `penalties` (e.g., `incorrect_answer.lives`, `language_mismatch.points`) so streaming/time-stop flows share the same scoring contract.

2. **Frontend Logic**
   - `storyStore` carries the active mode.
   - `ScenarioDisplay` toggles between time-stop controls and streaming UI.
   - Show lives remaining, score, planning aids, and live feedback elements per mode.
   - Reset lives/score from scenario metadata when changing levels; respect `scoreDelta`/`livesDelta` emitted by the backend.

3. **Backend Behavior**
   - Time-stop mode keeps existing `/narrative/interaction` endpoint.
   - Streaming mode uses WebSocket pipeline from [Streaming Architecture](./streaming-plan.md).
   - Expose mode-aware responses (e.g., confidence thresholds, retry counts, scoring deltas).
   - Normalize transcripts with target-language hints so Japanese stays in script for partials.

4. **Progression Rules**
   - Define per-level sequencing (e.g., chapters 1–3 beginner, 4+ advanced).
   - Consider adaptive difficulty based on streaks or coach overrides.



## Guardrails

- Detect non-target language speech, decrement lives, and prompt a targeted retry or hint.
- Log language-mismatch events for telemetry and future tuning.
- Reward correct answers with scenario-defined points; deduct lives (not score) on incorrect answers, and optionally triple-penalize wrong language via `penalties.language_mismatch`.
- When lives reach zero, halt auto-repeat flow and surface coaching message so the learner must pick another option or reset.

## Action Items

- [ ] Extend scenario schema with `mode` + migrate existing JSON files.
- [ ] Update backend models and responses to surface mode information.
- [ ] Implement UI mode switch + visual states in `ScenarioDisplay`.
- [ ] Define initial progression table (level → mode) and document it here.
- [ ] Capture scoring/lives defaults in a shared config (`DEFAULT_SUCCESS_POINTS`, `DEFAULT_FAILURE_LIFE_COST`) and expose via docs for gameplay balancing.
- [x] Autocomplete streaming turns once confidence + score thresholds met (no manual stop required).
- [ ] Add scenario fixtures (one beginner, one advanced) with different rewards/penalties to drive integration tests.
- [ ] Add Vitest or equivalent to cover `ScenarioStatus` and `ScenarioControls` state transitions with mocked event payloads.
- [ ] Provide docs snippet for scenario authors explaining `mode`, `reward_points`, and `penalties` usage.

## Dependencies

- UX guidelines in [UX Vision](./ux.md).
- Streaming tech covered in [Streaming Architecture](./streaming-plan.md).

## Links

- [UX Vision](./ux.md)
- [Streaming Architecture](./streaming-plan.md)
- [Open Questions](./open-questions.md)
