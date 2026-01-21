# Scenario Progression

## Summary

- The player is a time traveler relying on a finite set of “time skip” lives to survive awkward or dangerous encounters.
- Temporal gadgets map to mechanics: time stop for rehearsal, time rewind for limited lives, time fast-forward for optional scenario skips.
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
   - Surface explicit controls/affordances for time stop (prep), rewind (lives indicator), and fast-forward (skip affordance with clear trade-offs).

3. **Backend Behavior**
   - Time-stop mode keeps existing `/narrative/interaction` endpoint.
   - Streaming mode uses WebSocket pipeline from [Streaming Architecture](./streaming-plan.md).
   - Expose mode-aware responses (e.g., confidence thresholds, retry counts, scoring deltas).
   - Normalize transcripts with target-language hints so Japanese stays in script for partials.

4. **Progression Rules**
   - Define per-level sequencing (e.g., chapters 1–3 beginner, 4+ advanced).
   - Consider adaptive difficulty based on streaks or coach overrides.
   - Gate fast-forward availability based on narrative stakes and lives remaining; document skip consequences (reduced reward, branching loss).

5. **Destabilization Systems**
   - Gradually shorten time-stop windows as instability rises; expose a visible meter so players anticipate the cutoff.
   - Introduce translator cooldowns or charge-based usage at higher difficulties.
   - Track a “timeline debt” variable triggered by fast-forward use or excessive rewinds; feed it into scoring, branching unlocks, or surprise encounters.
   - Surface narrative anomalies (forced rapid prompts, limited rewinds, bonus objectives) when instability crosses thresholds.

## Scenario Authoring Cheatsheet

Scenarios are currently duplicated in two places:

- Frontend: `frontend/src/lib/test/scenarios.json` (demo UI + local examples)
- Backend: `backend/scenarios.json` (intent + options)

Core fields (recommended on every scenario):

- `mode`: `"beginner"` (time-stop) or `"advanced"` (streaming)
- `lives`: total rewind charges for this scenario (defaults: beginner=3, advanced=2)
- `reward_points`: points awarded on success (defaults: beginner=10, advanced=15)
- `penalties`: per-event overrides shared by both flows
  - `incorrect_answer.lives`: lives to burn when the learner answers incorrectly
  - `language_mismatch.lives` / `language_mismatch.points`: extra penalty when the learner speaks the wrong language after committing an attempt

Example:

```json
{
  "id": 4,
  "description": "First live response.",
  "mode": "advanced",
  "lives": 2,
  "reward_points": 15,
  "penalties": {
    "incorrect_answer": { "lives": 1 },
    "language_mismatch": { "lives": 2, "points": 10 }
  },
  "options": [{ "text": "Thank you!", "next_scenario": 5, "examples": [] }]
}
```

## Initial Progression Table

| Level Band | Scenario IDs / Examples | Mode | Lives | Notes |
| --- | --- | --- | --- | --- |
| Chapter 1 — Kitchen Greeting | `1-2` (Chef greets, ramen served) | `beginner` (time-stop) | 3 | Full prep controls enabled; translator + rehearsal unlimited, rewind costs 1 life per failed attempt. |
| Chapter 2 — Polite Declines | `3` | `beginner` (time-stop) | 3 | Reinforces polite exits; still time-stop but shortens prep window by ~10% to foreshadow instability. |
| Chapter 3 — First Live Response | `4-5` | `advanced` (streaming) | 2 | Live streaming starts; HUD shows confidence meter placeholder, auto-finalize on confident matches. |
| Chapter 4 — Requests & Payment | `6-8` | `advanced` (streaming) | 2 | Fast-forward unlocked; notes UI encourages tagging key phrases for review. |

Use this table when seeding future scenarios: early IDs (100-series, etc.) should mirror Chapters 1–2, while later arcs inherit the streaming defaults unless a designer explicitly opts into hybrid modes. Add new rows here whenever you introduce another progression beat so the Task Board always points to a single source of truth.

## Balancing Defaults

- Scoring/life defaults now live in `backend/config.py` as `DEFAULT_SUCCESS_POINTS` (points awarded on success) and `DEFAULT_FAILURE_LIFE_COST` (lives lost per failed attempt). They read from environment variables of the same name, so ops can tweak per deployment without touching code.
- Backend services import these config values directly; deleting or changing per-scenario overrides will automatically fall back to the shared defaults.
- Surface these numbers in design docs (like this file) whenever you negotiate difficulty so gameplay, backend, and HUD copy stay aligned.



## Guardrails

- The main record button is the only action that can cost lives; translator/rehearsal buttons must remain consequence-free prep tools.
- Detect non-target language speech after submission, decrement lives, and prompt a targeted retry or hint.
- Log language-mismatch events for telemetry and future tuning.
- Reward correct answers with scenario-defined points; deduct lives (not score) on incorrect answers, and optionally triple-penalize wrong language via `penalties.language_mismatch`.
- When lives reach zero, halt auto-repeat flow and surface a narrative warning (“Time anchor destabilized—rewind required”) before forcing reset.
- Fast-forward skips never cost lives but should trade off rewards/branch access; surface that consequence in the HUD/tooltips.
- Destabilization effects must be telegraphed: always show remaining prep window, translator charges/cooldowns, and instability status in HUD or tooltips.

## Action Items

- [x] Extend scenario schema with `mode` + migrate existing JSON files.
- [x] Update backend models and responses to surface mode information. (Streaming ready/reset/final events now carry `mode`, reward points, and penalty lives.)
- [x] Implement UI mode switch + visual states in `ScenarioDisplay` (time-stop vs. live streaming HUD, November 30, 2025).
- [x] Define initial progression table (level → mode) and document it here. (December 4, 2025)
- [x] Capture scoring/lives defaults in a shared config (`DEFAULT_SUCCESS_POINTS`, `DEFAULT_FAILURE_LIFE_COST`) and expose via docs for gameplay balancing. (December 4, 2025)
- [x] Autocomplete streaming turns once confidence + score thresholds met (no manual stop required).
- [x] Add scenario fixtures (one beginner, one advanced) with different rewards/penalties to drive integration tests. (December 5, 2025)
- [ ] Add Vitest or equivalent to cover `ScenarioStatus` and `ScenarioControls` state transitions with mocked event payloads.
- [x] Provide docs snippet for scenario authors explaining `mode`, `reward_points`, and `penalties` usage.
- [ ] Spec and prototype the fast-forward escape mechanic (UI cue, backend action, reward trade-offs).
- [ ] Design & implement instability meter + shrinking time-stop logic, including telemetry and tests.
- [ ] Evaluate translator cooldown UX (timer vs. charges) and update UI copy accordingly.

## Dependencies

- UX guidelines in [UX Vision](./ux.md).
- Streaming tech covered in [Streaming Architecture](./streaming-plan.md).

## Links

- [UX Vision](./ux.md)
- [Streaming Architecture](./streaming-plan.md)
- [Open Questions](./open-questions.md)
