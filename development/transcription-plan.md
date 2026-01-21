# Transcription Provider Strategy

Design reference for the provider-agnostic transcription layer. Captures how
each gameplay or notes workflow uses speech-to-text, what the latency targets
are, and how we pick between Gemini, OpenAI, or future providers.

## 1. Interaction Contexts

| Context       | Endpoint / Module                         | Audio Shape                    | Latency Target | Notes                                      |
|---------------|--------------------------------------------|--------------------------------|----------------|--------------------------------------------|
| `interaction` | `/narrative/interaction` (time-stop)       | Single WEBM upload (~1–3 s)    | < 2 s ideal    | Blocks UI; high accuracy.                  |
| `streaming`   | WebSocket `/stream/interaction` partials   | 200 ms chunks (<= ~12 KB)      | < 500 ms       | Needs fast partials; auto-finalize.        |
| `translate`   | `/narrative/translate` (make-your-own)     | Optional short WEBM or text    | < 1 s          | Safe zone; accuracy more important.        |
| `imitate`     | `/narrative/imitate` (repeat/score)        | Short WEBM (<= 2 s)            | < 1 s          | Used for scoring + hinting.                |
| `notes`       | `transcribe_and_save` background job       | Arbitrary audio (m4a/mp3/webm) | Async          | Accuracy priority; latency less critical.  |

## 2. Provider Capability Matrix

| Provider | Strengths                                 | Limitations / Flags                                    |
|----------|--------------------------------------------|--------------------------------------------------------|
| Gemini   | Good Japanese fidelity, supports hints     | REST latency ~2–3 s for multi-second clips; quota 429s |
| OpenAI   | Fast for short clips (<1.5 s), stable API  | Requires OpenSSL ≥1.1.1; per-minute quota applies      |
| Future OSS (placeholder) | On-device, offline-ready | Need manual deployment; likely higher CPU usage        |

Notes:
- Gemini streaming API is not yet integrated; revisit when stable.
- OpenAI transcription handles WEBM/OGG/MP3 via prompt hints for language.
- Keep `providers.transcribe_audio()` the single entry point so OSS models can be registered later.

## 3. Configuration Schema

Environment variables (comma-separated preference order):

```
# Default preference when no per-context override is set
TRANSCRIBE_PROVIDER_DEFAULT=auto

# Ordered preference per context (auto | gemini | openai)
TRANSCRIBE_INTERACTION_PROVIDER=gemini,openai
TRANSCRIBE_STREAMING_PROVIDER=openai,gemini
TRANSCRIBE_TRANSLATE_PROVIDER=auto
TRANSCRIBE_IMITATE_PROVIDER=openai,gemini
TRANSCRIBE_NOTES_PROVIDER=gemini,openai
```

Semantics:
- `auto` expands to all configured providers (Gemini first, then OpenAI) in availability order.
- Explicit lists enforce order; unknown tokens are ignored.
- If no providers are available after expansion, startup raises.

Expose these variables in `.env.example` and README (backend configuration section).

## 4. Logging & Telemetry Requirements

All call sites must log:
- `[context/provider] ... (transcription {duration_ms}ms)` or similar.
- `TranscriptionResult` provides `provider`, `model`, and optional `meta` (Gemini key index).
- Usage logging (`usage_log.log_usage`) should include provider + model.

## 5. Testing Strategy (Step 3 Preview)

Plan unit tests for `providers.transcribe_audio`:
- Preference order respected when first provider succeeds/fails.
- Fallback works when `invoke_google` raises rate-limit error.
- Unknown context defaults to `TRANSCRIBE_PROVIDER_DEFAULT`.

Integration tests:
- Monkeypatch provider function to assert per-context calls (already done in fixtures).

## 6. Migration Checklist (for Step 2)

1. Replace `_invoke_google` / `_transcribe_with_openai` usages with `providers.transcribe_audio` (done).
2. Ensure each caller passes `context` and instruction hints.
3. Remove legacy helper functions and unused imports in `services.py`.
4. Update tests to stub the new helper (done for core suites).
5. Document config changes (README + `.env.example`).

## 7. Step 2 – Detailed Refactor Plan

### 7.1 Global Preparation

- **Config Wiring**
  - Verify `TRANSCRIBE_*` values are loaded early (already in `config.py`). Add unit test to ensure defaults resolve correctly when env vars unset.
  - Provide `.env.example` snippet (done) and update backend README instructions for new knobs.
- **Provider Registry**
  - Ensure `providers.transcribe_audio()` exports contexts (`CONTEXT_*`) so callers do not hard-code strings.
  - Add helper in providers to expose available providers for debugging (`list_available_providers()` optional).

### 7.2 Module-by-Module Changes

1. **`backend/services.py`**
   - Interaction (`process_interaction`): call `transcribe_audio` with `context=CONTEXT_INTERACTION`, pass instructions/lang hints. Log `[interaction/{provider}]` with duration. Confirm usage logging uses provider/model from result.
   - Notes (`_transcribe_audio_bytes`, `transcribe_and_save`): route through `context=CONTEXT_NOTES` with instructions and MIME detection; remove residual `_invoke_google`/`_transcribe_with_openai`.
   - Imitate (`imitate_say`): call with `context=CONTEXT_IMITATE`; include expected language hint; capture provider in log.
   - Translation fallbacks (make-your-own) use `context=CONTEXT_TRANSLATE`.
   - Clean up unused imports (`ChatGoogleGenerativeAI`, `OpenAIWhisperParser`, `b64encode`) once direct calls removed.

2. **`backend/streaming.py`**
   - `transcribe_audio` wrapper: call `providers.transcribe_audio(..., context=CONTEXT_STREAMING)`; log partial duration + provider.
   - Consider exposing chunk size and MIN_PARTIAL_BYTES as config if future tuning needed (optional).

3. **`backend/main.py`**
   - Translation endpoint: use `providers.transcribe_audio` (already updated) and include provider info in future logs if needed.
   - WebSocket streaming finalize logic should remain unaffected but confirm `StreamingSession` uses new helper.

4. **`tests`**
   - Update fixtures (done) to stub `providers.transcribe_audio`.
   - Add targeted unit tests under `tests/providers_transcription_test.py`:
     1. Preference order obeyed when both providers available.
     2. Fallback invoked after simulated Gemini rate-limit error (`providers.invoke_google` raising `Exception("429 ...")`).
     3. Context override (e.g., streaming) respects env var via monkeypatched config.
   - Integration: ensure existing tests still pass referencing new logs.

### 7.3 Logging & Telemetry Verification

- Confirm every `transcribe_audio` call site wraps duration logging (`time.perf_counter()`).
- Usage log entries should include provider/model: verify by inspecting `backend/usage/daily-*.jsonl` after manual run.
- Optional: add structured logging hook (future) to emit JSON lines.

### 7.4 Manual QA Checklist

1. Start backend (with both keys) and run basic interaction & streaming scenario; check console for `[context/provider]` logs and reduced latency.
2. Temporarily unset Gemini key to verify OpenAI fallback works and logs provider change.
3. Flip env overrides (e.g., `TRANSCRIBE_STREAMING_PROVIDER=gemini`) and observe new provider usage in logs.

### 7.5 Future Extension Hooks

- Document expected API for adding an OSS provider (`register_provider("local_whisper", ...)`) so future work can plug in with minimal changes.
- Evaluate need for provider-specific retry/backoff (e.g., `max_attempts` per context).
