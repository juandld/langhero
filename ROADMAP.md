# LangHero Vision and Roadmap

This document captures the current product vision and the concrete steps to realize it, based on the ideas discussed so far. The goal is to teach speaking through immersive interaction: learners see and hear what to say in the target language, then try it themselves inside a living story.

## Why This Makes Sense

- Learners need actionable examples in context, not abstract drills. Dialog choices grounded in a scene (“What do you say to the kind man?”) make responses meaningful and memorable.
- Kids benefit from scaffolding: start with clear examples they can hear and repeat; later, fade to lighter hints and then free speech.
- AI enables dynamic, scene‑aware phrasing so learners always get examples aligned to the moment, tone, and language.
- Narrative structure sustains engagement and gives a reason to speak; choices matter and unlock the next scene.

## Core Principles

- Context first: content is anchored in scenes and characters.
- Language focus: examples always in the target language; same register/mood as the scene.
- Gradual release: Examples → Hints → Free speech.
- Audio‑first: every example can be heard (TTS) before speaking.
- Safety and clarity: short, positive, age‑appropriate phrasing.

## Current Capabilities (Implemented)

- Scenario interaction with microphone input and intent mapping via `/narrative/interaction`.
- AI‑generated, kid‑friendly example phrases per option via `/narrative/options`.
- Language focus and stage control: `lang=Japanese|English`, `stage=examples|hints`.
- Example audio synthesis using OpenAI TTS, served under `/examples/...mp3`.
- Frontend shows dialog, example chips, and play buttons; clicking advances the story.
- Scenario storage with import API to grow and revise content (`/api/scenarios`, `/api/scenarios/import`).

Relevant files

- Backend endpoints: `backend/main.py`
- Generation logic: `backend/services.py`
- Providers (Gemini/OpenAI/TTS): `backend/providers.py`
- Frontend scenario UI: `frontend/src/lib/components/ScenarioDisplay.svelte`
- Configs: `frontend/src/lib/config.ts`, `backend/config.py`

## Near‑Term Roadmap (Teaching Flow)

1) Examples (today)
- Show 2–4 short example phrases per option, in the focus language, with TTS.
- Learner may click a phrase or speak it; we map to the option and move on.

2) Hints
- Replace full phrases with “stems” and clue words (still in the target language).
- Keep TTS for hints (short prompt audio).
- Add a simple UI toggle for stage: Examples ↔ Hints.

3) Free Speech
- Classify the learner’s utterance to the closest option without showing any examples.
- Offer a small “Need a hint?” affordance to reveal a hint on demand.

4) Feedback and Recasts
- After speech, optionally play a very short recast (“You could say: …”) in the same language.
- Keep it optional to preserve flow and avoid over‑correction.

## Content Roadmap (Scenarios Database)

- Authoring first: we curate and expand our own scenarios.
- Import pipeline: accept structured JSON to append/replace scenario graphs.
- Reuse patterns: template common scenes (greetings, directions, shopping) and swap surface details.
- Difficulty tagging: mark nodes with level/band to guide example length and complexity.
- Versioning: keep track of scenario sets and allow safe edits over time.

## Future: From Any Video To Playable Scenes

Goal: take any internet video and turn it into an interactive story where the learner joins as a character.

- Ingest: retrieve transcript and speaker segments; detect language, tone, and relationships.
- Scene extraction: chunk highlights, identify conversational anchors, and infer “options” a learner could take.
- Attitudes: derive character mood and stance (friendly, rushed, confused) to condition example phrasing.
- Synthesis: auto‑draft scenario nodes from the video; a human editor reviews and publishes.
- Voices: optional character TTS to match the scene’s style for higher immersion.

## Technical Plan (High Level)

- Endpoints in place
  - `/narrative/interaction` — handle speech and map to next scene.
  - `/narrative/options` — generate example phrases per option, language‑aware; returns TTS URLs.
  - `/api/scenarios`, `/api/scenarios/import` — list/import scenario sets.
- Frontend
  - Render dialog, options, examples/hints with play buttons.
  - Toggle teaching stage and language (UI control to add).
- Models
  - Primary: Gemini 2.5 Flash with key rotation.
  - Fallback: OpenAI (chat, whisper, TTS) when configured.
- Content storage
  - JSON on disk now; can move to a simple DB when needed (same schema).

## Safety, Quality, and Fit for Kids

- Prompt rules enforce short, age‑appropriate, positive language.
- Hard cap phrase length; avoid edgy content; maintain friendly register.
- Guardrails on imports; human review before publishing new scenario packs.

## Measuring Success

- Engagement: time‑on‑scene, number of spoken attempts.
- Progression: how quickly learners move from Examples → Hints → Free Speech.
- Comprehensibility: teacher/parent ratings or light comprehension checks.
- Content coverage: number of vetted scenarios across topics and levels.

## Next Concrete Steps

- Add UI toggles for Stage (Examples/Hints) and Language focus per scene.
- Add optional “recast” playback after learner speech.
- Extend `/api/scenarios/import` with append/merge and validation.
- Prepare an authoring guide and a base pack of core scenes.

