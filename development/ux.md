# UX Vision

## Snapshot

- Maintain the press-to-speak interaction, but flex its behavior by scenario difficulty.
- Communicate the fantasy: the learner is a time traveler relying on limited “time skip” lives to stay safe.
- Show learners what the system is hearing in real time (transcript, confidence, scenario hints).
- Keep translator and rehearsal tools clearly separated from the high-stakes response button so players always know when lives are on the line.
- Make the **free/demo experience** cheap enough to run as marketing: pre-baked content, mocked streaming, and strict gating on expensive imports.

## Temporal Tools

- **Time Stop** — freezes the moment so the traveler can rehearse safely (translator, examples, make-your-own phrase editor).
- **Time Rewind** — limited lives stored as rewind charges; a failed main-record attempt spends one and resets the scene.
- **Time Fast-Forward** — optional escape hatch to skip a volatile scenario when survival matters more than rewards or branching content.

## Voice & Reality Layers (North Star)

We’re time travelers stuck in hostile timelines: we only have our words, plus hidden time-machine utilities that can “freeze” a moment long enough to rehearse. Audio has to communicate which layer you’re in without requiring the player to read.

### Two Voice Personas

- **Time Machine Assistant (robotic)** — all safe prep tools: examples, translations, “make your own line”, coach prompts, retries, and system hints. This voice should feel synthetic and consistent (same cadence/texture everywhere).
- **World Characters (human)** — the scene and consequences: NPC dialogue, reactions, ambient narration, and any “you are here now” confirmations. These voices should sound grounded and characterful (chef/guard/friend), even when the UI is in time-stop.

### Audio Rule

If a line comes from a *tool*, it must sound like the assistant. If it comes from the *world*, it must sound like a person in that world.

## Implementation Plan (Testable)

1. **Define voice roles in schema** – add `speaker_id` + `voice_role` defaults in scenario JSON (examples default to `assistant`; NPC lines default to `npc:<speaker_id>`).
2. **Key the cache by role** – extend the voice manifest key to include `voice_role`/`speaker_id` so identical phrases don’t cross-contaminate voices.
3. **Role-aware TTS API** – extend `POST /api/tts` to accept `{ text, language, role, speaker_id }` and pick voice + effect from config; return `{ clip_id, url, role }`.
4. **Robotic assistant effect** – apply a deterministic “time machine” treatment (pitch/formant/bitcrush) for assistant audio; keep the NPC channel clean.
5. **Frontend routing** – examples + translations always call TTS with `role=assistant`; NPC dialogue uses `role=npc` with `speaker_id` from scenario.
6. **Ops batch generation** – expand `operations/scripts/generate_voices.py` to pre-render both roles for all scenario lines and examples, producing a single shared manifest.
7. **Pytest coverage** – add tests that the same phrase yields different `clip_id`s across roles, and that `/api/tts` returns stable URLs without network when a stub synthesizer is used.

## Destabilization Mechanics (Difficulty Scaling)

- **Shrinking Time Stop** — the longer the session runs (or the higher the difficulty), the smaller the preparation window before auto-submission.
- **Temporal Drift Meter** — repeated mistakes/rewinds fill an instability bar that injects glitches (static, UI distortion) and raises penalty severity until the player stabilizes with flawless turns.
- **Translator Cooldown** — advanced chapters add a cooldown/limited charges on safe rehearse tools, forcing deliberate planning.
- **Fast-Forward Fallout** — skipping forward creates “timeline debt” that reduces future rewards or spawns side quests to repair paradoxes.
- **Anchor Objectives** — occasional scenes require success without rewinds to re-lock the timeline, unlocking new branches or restoring tool strength.

## Decisions (locked)

- Early levels preserve “time-stop” planning: hold to think, release to submit, limited lives per attempt.
- Advanced levels drop time-stop: audio streams immediately, UI shifts to live comprehension cues.
- Lives mechanic continues across modes to reinforce deliberate speech.



## Guardrails

- The main record button represents a risky in-world action; once pressed, success or failure burns or saves lives (`time skip charges`).
- Translator / make-your-own tools are explicitly safe prep zones: no lives lost, no penalties, and the UI reinforces that distinction.
- Speaking in a language other than the target after pressing the main record button triggers an immediate miss (life loss plus retry prompt).
- Provide context messaging that explains the penalty in narrative terms (“The locals panic when they can’t understand you—try again in Japanese.”).

## MVP Experience

- **Beginner (time-stop)**: a short loop that lets learners rehearse, see examples, and submit when ready. Shows score/lives and stresses that lives are consumed only when the main record button is used.
- **Advanced (streaming)**: live transcript ticker, penalty callouts, and automatic lives/score updates that match the backend contract (`scoreDelta` / `livesDelta`). Translator tools remain clearly out-of-band, and time fast-forward affords a narrative skip when designers allow it.
- **Shared HUD**: scoreboard stays consistent between modes and resets when scenarios change; wrong-language prompts recommend the target phrase with pronunciation while framing the danger narrative (rewind spent, timeline reset).
- **Accessibility**: every penalty message is actionable (“Please answer in Japanese…”) and the HUD remains screen-reader friendly (`role="alert"` for penalties).

## Marketing / Trial Guardrails

We want free trials and demo scenarios to be sharable and abundant, but **cheap**:

- Default demo path is **zero-LLM / zero-transcribe**: pre-baked scenarios + mock streaming (`/stream/mock`).
- Expensive features (video import, real streaming ASR) are **metered** and/or require explicit enablement.
- Imports remain private-by-default; “publish” is explicit and shares compiled Scenario[] rather than raw media/text.

Implementation hooks:
- Backend demo mode env flags (`DEMO_MODE`, etc.) should gate uncached video imports and real streaming.
- Frontend can still show the UX, but the backend must be the cost authority.

## Action Items

- [ ] Prototype UI modules for live transcript, confidence meter, and hint surfacing.
- [ ] Define design tokens/variants for time-stop vs. streaming states.
- [ ] Sync with engineering on feasible latency thresholds (see [Streaming Architecture](./streaming-plan.md)).
- [ ] Add Vitest/Svelte unit tests for `ScenarioStatus` and penalty flows once the frontend test harness is in place.

## Links

- [Scenario Progression](./scenario-progression.md)
- [Streaming Architecture](./streaming-plan.md)
