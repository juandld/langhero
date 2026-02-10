# UX Vision

## Snapshot

- Maintain the press-to-speak interaction, but flex its behavior by scenario difficulty.
- Communicate the fantasy: the learner is a time traveler relying on limited “time skip” lives to stay safe.
- Show learners what the system is hearing in real time (transcript, confidence, scenario hints).
- Keep translator and rehearsal tools clearly separated from the high-stakes response button so players always know when lives are on the line.
- Make the **free/demo experience** cheap enough to run as marketing: pre-baked content, mocked streaming, and strict gating on expensive imports.

## Temporal Tools

- **Time Stop** — freezes the moment so the traveler can rehearse safely (suggestion cards, Ask Bimbo translation, tap-to-hear).
- **Time Rewind** — lives represent narrative survival, not pronunciation retries. A life is spent when the player's words cause the characters or world to kill them. Speech quality alone never costs a life.
- **Time Fast-Forward** — optional escape hatch to skip a volatile scenario when survival matters more than rewards or branching content.
- **Dialogue Rewind** — during narrative sequences (intro, briefings, cutscenes), players can rewind to previous dialogue lines. This is a "free" time tool available at the start of the journey. As players advance deeper into hostile timelines, this luxury erodes:
  - **Tutorial/Intro**: Unlimited rewind (arrow key, back button)
  - **Early Story**: Limited rewind charges per scene
  - **Advanced Chapters**: No rewind — narrative plays forward only, reinforcing the danger and irreversibility of choices
  - The mechanic teaches players to pay attention and creates tension as they lose temporal safety nets

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



## Ask Bimbo — Creative Expression

Bimbo is the player's time-travel companion. When the player wants to say something creative or off-script, they type it in English and Ask Bimbo.

**Flow:**
1. Player types intent in English (e.g., "I am god reincarnated")
2. Single LLM call: Bimbo translates to natural Japanese + gives a funny, personality-driven remark + optionally matches to an existing option
3. Backend calls `providers.romanize()` for reliable romaji (never trusts LLM romaji)
4. Frontend shows a **pronunciation card**: Japanese (large, bold) + romaji (italic, purple) + English (gray) + tap-to-hear speaker icon
5. Audio auto-plays the Japanese translation in Bimbo's voice
6. If the intent happens to match an existing option, that card highlights too
7. Player speaks → result card shows what they said + how it landed (category) + Continue/Skip

**Key principle:** The suggestion cards are not "correct answers." They are helpful examples. The player can say anything. The result card never shows an "expected" answer — only what the player said and how it landed.

## Response Categories

Every spoken response is categorized by its narrative tone, not its pronunciation accuracy:

| Category | Icon | Color | Examples |
|---|---|---|---|
| Diplomatic | 🕊 | Green | polite, charming, humble, friendly |
| Pragmatic | ⚖ | Blue | cautious, honest, safe, vague, silent |
| Bold | ⚡ | Orange | direct, bold, desperate |
| Hostile | 🔥 | Red | hostile, defiant, threatening |
| History-Breaking | ✦ | Purple | insightful — changes the course of events |

The category appears on the result card after speaking, giving the player a sense of how their words landed in the story world. This connects language practice to narrative consequence.

## Result Card

After speaking, the result card shows:

**On success (good/perfect match):**
- Quality label ("Perfect!", "Great!", "Good!")
- What the player said (Japanese + English translation)
- Response category badge (e.g., "🔥 Hostile")
- **Continue →** button (no auto-advance — player reads and reflects)

**On non-success (any other result):**
- What the player said (Japanese + English translation)
- Response category badge
- **Try again or Skip →** button

**Never shown:** "expected" answers, pronunciation scores, lives lost from speech quality.

## Guardrails

- The main record button commits the player's words to the story world. The narrative reacts to what they say.
- **Lives are narrative consequences**: a life is lost when the player's words cause characters to kill them, betray them, or place them in a fatal situation. Speech recognition quality (match score, tier) never costs a life. The story decides who lives and dies, not the speech engine.
- Suggestion cards / Ask Bimbo / tap-to-hear are explicitly safe prep zones: no consequences, and the UI reinforces that distinction.
- Speaking in a language other than the target after pressing the main record button triggers a retry prompt with narrative framing ("The locals can't understand you — try again in Japanese.").

## MVP Experience

- **Beginner (time-stop)**: time freezes, suggestion cards appear, player can tap to hear examples or Ask Bimbo for creative translations. Press Speak when ready. Result shows what was said + how it landed. Continue when ready — no auto-advance.
- **Advanced (streaming)**: live transcript ticker, category callouts, and automatic score updates. Narrative consequences (including life loss) come from the story, not the speech engine.
- **Shared HUD**: scoreboard stays consistent between modes. Lives represent narrative survival. Score rewards effort and creativity.
- **Accessibility**: every result message is actionable and the HUD remains screen-reader friendly (`role="alert"` for results).

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
