# Voice Generation Plan

Guidelines for producing scenario audio clips with OpenAI TTS. The goal is to keep costs low, avoid regenerating identical phrases, and ensure future scenarios can reuse existing clips without extra work.

## Goals

1. **One-click batch generation** – `operations/scripts/generate_voices.py` walks every scenario and emits audio files into `examples_audio/`.
2. **Stable assets** – Once a phrase is synthesized, it should be reused forever (unless manually overwritten) so production builds keep deterministic audio.
3. **Minimal duplication** – Many options recycle the same expressions (“Yes, please.”); we should never pay to generate them twice.
4. **Limited variety** – Allow up to four alternates for the *same* phrase to avoid monotony, but cap the number so the cache stays manageable.

## Reuse & Variation Strategy

- Normalize phrases before lookup (trim whitespace, collapse spaces, lowercase for ASCII, keep language-specific script intact).
- Manifest (`examples_audio/manifest.json`) maps `normalized_phrase → {phrase_id, variants[]}`. Each variant now carries a UUID `clip_id`, `voice`, `format`, and canonical file (`phrases/phrase-<hash>-vN.mp3`).
- When a phrase appears again:
  - Default path: reuse the earliest variant (round-robin once multiple exist) and simply record a new link entry (no duplicated audio bytes).
  - Opt-in `--expand-variants` to synthesize up to N alternates (cap defaults to 4) for variety; round-robin assigns them across scenarios.
- Link index (`examples_audio/scenario_clips.json`) records `{scenario-<id>-opt<idx>-ex<idx>.mp3 → clip_id}` so the UI/API can reference canonical clips via stable IDs—no local filenames required.
- Optional `--write-copies` flag emits the legacy per-scenario MP3s if you still need them during the transition.
- Keep per-language subfolders if we introduce multiple locales (`examples_audio/ja/`, `examples_audio/en/`) to prevent collisions when identical phonetics occur in different scripts.

## Reasoning Tests

These pytest cases keep the reuse/variant logic honest (`tests/voice_generation_test.py`):

1. ✅ **Deduplication** – identical phrases reuse cached variants (no extra synth calls).
2. ✅ **Variant cap** – with `--expand-variants --max-variants=2`, only two canonical clips are synthesized even when phrases repeat five times.
3. ✅ **Round-robin reuse** – scenario-specific copies alternate between existing variants once the cap is reached.
4. ✅ **Dry-run mode** – `--dry-run` touches neither disk nor the synthesizer stub.
5. ⏳ **Manifest crash safety** – ensure resumability after partial runs (still to add).
6. ⏳ **Language isolation** – verify normalization keeps scripts scoped per language.
7. ⏳ **Error propagation** – confirm failed synth calls don’t corrupt manifest entries.

## Open Questions

- Do we want separate voices per scenario mode (e.g., calmer voice for time-stop, energetic for streaming)?
- Should translators/prep phrases share the same cache directory, or do they need their own pipeline?
- Manifest format: JSON, SQLite, or hashed folder structure?
- Should we allow per-phrase metadata (speaker name, tempo) to help authors pick specific vibes later?

Capture future answers here so the TTS workflow remains a single source of truth.

## Python Unit Testing Methodology

We’ll back the generator with targeted pytest coverage. Key principles:

- **Temp workspace fixture** – use `tmp_path` to isolate `examples_audio/` and the manifest; point environment variables/config to those directories via monkeypatch so the script under test never touches real assets.
- **Scenario fixture** – construct small JSON payloads inline (e.g., two beginner options, one advanced) and write them to a temp `scenarios.json`. Each test can tweak phrases/languages without polluting other cases.
- **Provider stub** – monkeypatch `providers.tts_with_openai` to record inputs and return deterministic byte payloads (`b"audio-<counter>"`). This removes OpenAI dependency and lets tests assert call counts & parameters.
- **Helper runner** – import `generate_voices.main` (or refactor into a callable) and invoke it with `argparse` arguments using `pytest.MonkeyPatch` to manipulate `sys.argv`. Alternatively, expose a pure function (`generate_clips(...)`) to call directly for easier assertions.

Test matrix:

1. **Basic generation** – one scenario/phrase -> verify single file creation, manifest entry, stub called once.
2. **Reuse without overwrite** – same phrase referenced twice -> stub called once, both scenario-specific filenames point to same underlying clip (symlink or file copy). Assert manifest contains single entry with `count == 2`.
3. **Overwrite flag** – add `--overwrite`; ensure existing file replaced (e.g., compare timestamps or stored byte markers).
4. **Variant cap enforcement** – run generator 5 times for same phrase with `max_variants=4`; expect stub invoked 4 times, fifth call reuses earlier files. Validate rotation order.
5. **Round-robin selection** – simulate multiple requests after variants exist; ensure returned file names cycle through manifest entries evenly (verify recorded order per call).
6. **Language isolation** – identical ASCII string but different script (e.g., `"ありがとう"` vs `"ありがとう"` transliterated) should produce distinct manifest keys; confirm both files exist though normalized ASCII text matches.
7. **Manifest resume safety** – pre-populate manifest with one phrase + file; rerun generator and ensure stub not invoked again, even after partial run (simulate by manually touching manifest + file, then executing main).
8. **Dry-run mode** – `--dry-run` should not write files but should log intent; assert stub not called and output counts reflect pending work.
9. **Error propagation** – force stub to raise; generator should continue (logging error) but not crash overall. Ensure manifest not updated for failed phrase.

All tests run offline, deterministic, and fast. Integrate into `tests/voice_generation_test.py` with fixtures for stubbed providers and scenario JSONs so CI can assert caching/variant logic without relying on external APIs.
