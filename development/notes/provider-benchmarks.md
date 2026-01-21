# Provider Benchmarks (Transcription)

This is the logbook for the M2 “provider shoot-out harness”: measure transcription latency + output quality on a fixed set of audio fixtures.

## Why

- We need predictable streaming latency and stable costs.
- Provider selection is context-specific (`interaction` vs `streaming` vs `notes`) via `TRANSCRIBE_*` env vars.

## Harness

Run the benchmark script against a local audio file:

- `python3 backend/provider_benchmark.py --file path/to/audio.webm --context streaming --runs 5`

Tips:
- Set provider order via env, e.g. `TRANSCRIBE_STREAMING_PROVIDER="openai,gemini"`.
- Use the same file, language hint, and context when comparing results.

## Fixture Set (target)

- 3–5 short “clean” clips (2–6s)
- 3–5 “noisy” clips (background noise / reverb)
- 3 clips per target language we support in MVP (EN/ES/JA)

Store fixtures outside git if needed; only commit public-domain or self-recorded samples.

## Log Template

Date:

Env:
- `TRANSCRIBE_PROVIDER_DEFAULT=...`
- `TRANSCRIBE_STREAMING_PROVIDER=...`
- `TRANSCRIBE_INTERACTION_PROVIDER=...`

Run:
- file:
- language_hint:
- context:
- runs:

Results (paste summary):
- providers:
- ms mean/p50/min/max:
- transcript notes:

