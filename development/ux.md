# UX Vision

## Snapshot

- Keep the press-to-speak interaction, but flex its behavior by scenario difficulty.
- Show learners what the system is hearing in real time (transcript, confidence, scenario hints).
- Let translation and rehearsal tools exist alongside live feedback so practice scaffolding remains useful.

## Decisions (locked)

- Early levels preserve “time-stop” planning: hold to think, release to submit, limited lives per attempt.
- Advanced levels drop time-stop: audio streams immediately, UI shifts to live comprehension cues.
- Lives mechanic continues across modes to reinforce deliberate speech.



## Guardrails

- Speaking in a language other than the target triggers an immediate miss (life loss or repeat prompt).
- Provide context messaging that explains the penalty and encourages retry in the right language.

## MVP Experience

- **Beginner (time-stop)**: a short loop that lets learners rehearse, see examples, and submit when ready. Shows score/lives and translations for recovery.
- **Advanced (streaming)**: live transcript ticker, penalty callouts, and automatic lives/score updates that match the backend contract (`scoreDelta` / `livesDelta`).
- **Shared HUD**: scoreboard stays consistent between modes and resets when scenarios change; wrong-language prompts recommend the target phrase with pronunciation.
- **Accessibility**: every penalty message is actionable (“Please answer in Japanese…”) and the HUD remains screen-reader friendly (`role="alert"` for penalties).

## Action Items

- [ ] Prototype UI modules for live transcript, confidence meter, and hint surfacing.
- [ ] Define design tokens/variants for time-stop vs. streaming states.
- [ ] Sync with engineering on feasible latency thresholds (see [Streaming Architecture](./streaming-plan.md)).
- [ ] Add Vitest/Svelte unit tests for `ScenarioStatus` and penalty flows once the frontend test harness is in place.

## Links

- [Scenario Progression](./scenario-progression.md)
- [Streaming Architecture](./streaming-plan.md)
