"""
Video and transcript-based scenario generation.
"""
from __future__ import annotations

import os
import re
from typing import Optional
import sys
import subprocess
import tempfile
import importlib.util
from langchain_core.messages import HumanMessage
import config
import providers
import usage_log as usage


def _is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube link."""
    if not isinstance(url, str):
        return False
    u = url.strip().lower()
    return (
        u.startswith("https://www.youtube.com/")
        or u.startswith("https://youtube.com/")
        or u.startswith("https://youtu.be/")
    )


def _ffmpeg_extract_audio_from_youtube(url: str, out_wav_path: str, sample_rate: int = 16000) -> None:
    """Extract audio using yt-dlp piped into ffmpeg."""
    if importlib.util.find_spec("yt_dlp") is None:
        raise RuntimeError("yt_dlp_not_installed (install with: pip install yt-dlp)")

    # Cap downloads to reduce abuse/cost
    try:
        max_bytes = int(getattr(config, "YTDLP_MAX_FILESIZE_BYTES", 52428800) or 0)
    except Exception:
        max_bytes = 52428800

    max_size_arg = None
    if max_bytes > 0:
        max_mib = max(1, int(round(max_bytes / (1024 * 1024))))
        max_size_arg = f"{max_mib}M"

    ytdlp_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist", "--no-progress",
        *(["--max-filesize", max_size_arg] if max_size_arg else []),
        "-f", "bestaudio/best",
        "-o", "-",
        url,
    ]

    try:
        max_seconds = int(getattr(config, "VIDEO_MAX_SECONDS", 300) or 0)
    except Exception:
        max_seconds = 300

    ffmpeg_cmd = ["ffmpeg", "-y", "-i", "pipe:0"]
    if max_seconds > 0:
        ffmpeg_cmd += ["-t", str(max_seconds)]
    ffmpeg_cmd += ["-vn", "-ac", "1", "-ar", str(sample_rate), out_wav_path]

    proc = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None

    try:
        subprocess.run(
            ffmpeg_cmd,
            stdin=proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        _, ytdlp_err = proc.communicate(timeout=60)
        if proc.returncode not in (0, None):
            snippet = (ytdlp_err or b"")[:400].decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"yt_dlp_failed: {snippet or 'unknown_error'}")


def _ffmpeg_extract_audio(url: str, out_wav_path: str, sample_rate: int = 16000) -> None:
    """Use ffmpeg to extract mono WAV audio from a video URL or file path."""
    if isinstance(url, str) and _is_youtube_url(url):
        _ffmpeg_extract_audio_from_youtube(url, out_wav_path, sample_rate=sample_rate)
        return

    try:
        max_seconds = int(getattr(config, "VIDEO_MAX_SECONDS", 300) or 0)
    except Exception:
        max_seconds = 300

    cmd = ["ffmpeg", "-y", "-i", url]
    if max_seconds > 0:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", str(sample_rate), out_wav_path]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return
    except subprocess.CalledProcessError as e:
        url_str = str(url or "")
        can_try_ytdlp = url_str.startswith("http://") or url_str.startswith("https://")
        if can_try_ytdlp and importlib.util.find_spec("yt_dlp") is not None:
            _ffmpeg_extract_audio_from_youtube(url_str, out_wav_path, sample_rate=sample_rate)
            return
        snippet = ((e.stderr or b"")[:400]).decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg_failed: {snippet or 'unknown_error'}") from e


def _transcribe_audio_bytes(audio_bytes: bytes, lang_hint: Optional[str] = None) -> str:
    """Transcribe bytes via Gemini, with OpenAI fallback."""
    try:
        instruction = "Transcribe this audio recording in the language you hear. Do not translate."
        if lang_hint:
            hint = lang_hint.strip()
            lower = hint.lower()
            if "japanese" in lower or lower == "ja":
                instruction = (
                    "Transcribe this audio recording. "
                    "If the speaker uses Japanese, write it in Japanese script without romanizing. "
                    "If another language is spoken, transcribe using that language's typical writing system. "
                    "Do not translate."
                )
            else:
                instruction = (
                    "Transcribe this audio recording. "
                    f"The expected language is {hint}, but always keep the language that is actually spoken. "
                    "Do not translate."
                )

        result = providers.transcribe_audio(
            audio_bytes,
            file_ext="wav",
            mime_type="audio/wav",
            instructions=instruction,
            language_hint=lang_hint,
            context=providers.CONTEXT_NOTES,
        )

        try:
            if result.provider == "gemini":
                key_index = int(result.meta.get("key_index", 0) or 0)
                usage.log_usage(
                    event="video_transcribe",
                    provider="gemini",
                    model=result.model,
                    key_label=usage.key_label_from_index(key_index, providers.GOOGLE_KEYS),
                    status="success",
                )
            elif result.provider == "openai":
                usage.log_usage(
                    event="video_transcribe",
                    provider="openai",
                    model=result.model,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
        except Exception:
            pass

        return result.text
    except Exception:
        return ""


def generate_scenarios_from_transcript(
    transcript: str,
    target_language: str = "Japanese",
    max_scenes: int = 5,
    usage_event: str = "scenario_compile",
) -> list:
    """Use an LLM to turn a transcript into a short branching scenario list."""
    prompt = (
        "You are a language learning scenario designer. Given this dialogue transcript, "
        "produce a compact branching scenario for beginners in JSON array format.\n\n"
        f"Target language: {target_language}.\n"
        f"Max scenes: {max_scenes}. Keep it simple and kid-friendly.\n\n"
        "Output JSON only (no markdown), where each item is:\n"
        "{\n  \"id\": number,\n  \"language\": string,\n  \"description\": string,\n  "
        "\"character_dialogue_jp\": string,\n  \"character_dialogue_en\": string,\n  "
        "\"options\": [ {\n    \"text\": string, \n    \"next_scenario\": number,\n    "
        "\"keywords\": [string...],\n    \"examples\": [ { \"native\": string, \"target\": string, "
        "\"pronunciation\": string } ]\n  } ... ]\n}\n\n"
        "Guidelines:\n- IDs must be sequential starting at 1.\n"
        "- Use Japanese in character_dialogue_jp when target_language is Japanese.\n"
        "- Provide 2-3 options in early scenes; terminal scenes can have empty options.\n"
        "- Include 1 example per option in the target language.\n"
        "- Keywords should include short target-language triggers.\n\n"
        "Transcript:\n" + transcript
    )

    provider_used = None
    model_used = None
    key_index = None

    try:
        resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": prompt}])])
        provider_used = "gemini"
        model_used = config.GOOGLE_MODEL
        text = str(getattr(resp, "content", resp))
    except Exception:
        provider_used = "openai"
        model_used = config.OPENAI_NARRATIVE_MODEL
        text = providers.openai_chat([HumanMessage(content=prompt)])

    try:
        usage.log_usage(
            event=str(usage_event or "scenario_compile"),
            provider=str(provider_used or "unknown"),
            model=str(model_used or "unknown"),
            key_label=(providers.key_label_from_index(key_index or 0) if provider_used == "gemini" else usage.OPENAI_LABEL),
            status="success",
        )
    except Exception:
        pass

    # Attempt to extract JSON array
    try:
        m = re.search(r"\[.*\]", text, flags=re.S)
        arr = m.group(0) if m else text
        import json
        data = json.loads(arr)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def generate_scenarios_from_video(url: str, target_language: str = "Japanese", max_scenes: int = 5) -> list:
    """Pipeline: ffmpeg audio extract -> transcribe -> LLM structure -> scenarios list."""
    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "audio.wav")
        _ffmpeg_extract_audio(url, wav_path)
        with open(wav_path, "rb") as f:
            audio_bytes = f.read()

    transcript = _transcribe_audio_bytes(audio_bytes, lang_hint=target_language)
    return generate_scenarios_from_transcript(
        transcript,
        target_language=target_language,
        max_scenes=max_scenes,
        usage_event="video_compile",
    )
