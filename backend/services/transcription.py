"""
Audio transcription utilities.
"""

import os
import asyncio
from langchain_core.messages import HumanMessage
import config
import providers
import note_store
import usage_log as usage


async def transcribe_and_save(wav_path: str):
    """Transcribes and titles an audio file, saving the results."""
    base_filename = os.path.basename(wav_path)
    ext = os.path.splitext(base_filename)[1].lower().lstrip('.') or 'wav'
    print(f"Starting transcription process for {base_filename}...")

    try:
        # Read audio bytes
        with open(wav_path, "rb") as af:
            audio_bytes = af.read()

        # Transcribe with provider rotation & fallback
        print(f"Transcribing {base_filename} from local file bytes...")
        mime = {
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "mp3": "audio/mp3",
            "m4a": "audio/mp4",
        }.get(ext, "audio/wav")

        result = await asyncio.to_thread(
            providers.transcribe_audio,
            audio_bytes,
            file_ext=ext,
            mime_type=mime,
            instructions="Transcribe this audio recording.",
            context=providers.CONTEXT_NOTES,
        )
        transcribed_text = result.text
        print(f"Successfully transcribed {base_filename} via {result.provider}.")

        # Log usage
        if result.provider == "gemini":
            key_index = int(result.meta.get("key_index", 0) or 0)
            usage.log_usage(
                event="transcribe",
                provider="gemini",
                model=result.model,
                key_label=usage.key_label_from_index(key_index, providers.GOOGLE_KEYS),
                status="success",
            )
        elif result.provider == "openai":
            usage.log_usage(
                event="transcribe",
                provider="openai",
                model=result.model,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )

        # Generate title
        print(f"Generating title for {base_filename}...")
        try:
            title_message = HumanMessage(
                content=[{
                    "type": "text",
                    "text": (
                        "Return exactly one short title (5-8 words) for the transcription below. "
                        "Use the same language as the transcription. Do not include quotes or markdown. "
                        "Output only the title on a single line.\n\n" + transcribed_text
                    ),
                }]
            )

            # Try Gemini briefly, else fallback to OpenAI
            gemini_ok = False
            last_key_index = None

            for attempt in range(2):
                try:
                    title_response, key_index = await asyncio.to_thread(
                        providers.invoke_google, [title_message]
                    )
                    last_key_index = key_index
                    title_text = providers.normalize_title_output(title_response.content)
                    gemini_ok = True
                    break
                except Exception as ge:
                    print(f"Gemini title attempt {attempt+1} failed for {base_filename}: {ge}")
                    if providers.is_rate_limit_error(ge):
                        break
                    continue

            if gemini_ok:
                usage.log_usage(
                    event="title",
                    provider="gemini",
                    model=config.GOOGLE_MODEL,
                    key_label=providers.key_label_from_index(last_key_index or 0),
                    status="success",
                )
            else:
                raise RuntimeError("Gemini unavailable for title")

        except Exception as e:
            try:
                print(f"Falling back to OpenAI title for {base_filename}: {e}")
                title_text = providers.title_with_openai(transcribed_text)
                usage.log_usage(
                    event="title",
                    provider="openai",
                    model=config.OPENAI_TITLE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            except Exception:
                title_text = "Title generation failed."

        print(f"Successfully generated title for {base_filename}.")

        payload = note_store.build_note_payload(base_filename, title_text, transcribed_text)
        note_store.save_note_json(os.path.splitext(base_filename)[0], payload)
        print(f"Successfully saved transcription and title for {base_filename}.")

    except Exception as e:
        print(f"Error during transcription/titling for {wav_path}: {e}")
        if os.path.exists(wav_path):
            payload = note_store.build_note_payload(base_filename, "Title generation failed.", "Transcription failed.")
            note_store.save_note_json(os.path.splitext(base_filename)[0], payload)
