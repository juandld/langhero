"""
Provider utilities: Gemini (Google) and OpenAI fallbacks via LangChain.

Encapsulates key rotation, retry strategy decisions, and simple helpers for
transcription and title generation. Keeping this here makes services.py smaller
and easier to scan.
"""

from __future__ import annotations

import io
from base64 import b64encode
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

import config

# Initialize module logger early (before any usage)
logger = logging.getLogger("narrative.providers")


# Initialize Gemini clients (one per API key) for rotation
GOOGLE_KEYS = config.collect_google_api_keys()
GOOGLE_LLMS: List[ChatGoogleGenerativeAI] = [
    ChatGoogleGenerativeAI(model=config.GOOGLE_MODEL, api_key=k) for k in GOOGLE_KEYS
]

# Log configured model and key status for visibility
logger.info(
    "Gemini configured: model=%s, keys=%s",
    config.GOOGLE_MODEL,
    len(GOOGLE_KEYS),
)


def is_rate_limit_error(e: Exception) -> bool:
    s = str(e).lower()
    return (
        "429" in s
        or "rate limit" in s
        or "quota" in s
        or "exceeded your current quota" in s
    )


def key_label_from_index(index: int, keys: Optional[List[str]] = None) -> str:
    keys = keys if keys is not None else GOOGLE_KEYS
    try:
        key = keys[index]
    except Exception:
        return f"gemini_key_{index}"
    return f"gemini_key_{index}_{key[-4:] if key else '????'}"


@dataclass
class TranscriptionResult:
    text: str
    provider: str
    model: str
    meta: Dict[str, Any] = field(default_factory=dict)


# Transcription contexts
CONTEXT_INTERACTION = "interaction"
CONTEXT_STREAMING = "streaming"
CONTEXT_TRANSLATE = "translate"
CONTEXT_IMITATE = "imitate"
CONTEXT_NOTES = "notes"

_ALL_CONTEXTS = {
    CONTEXT_INTERACTION,
    CONTEXT_STREAMING,
    CONTEXT_TRANSLATE,
    CONTEXT_IMITATE,
    CONTEXT_NOTES,
}


def _available_providers() -> List[str]:
    providers: List[str] = []
    if GOOGLE_KEYS:
        providers.append("gemini")
    if config.OPENAI_API_KEY:
        providers.append("openai")
    return providers


def _expand_provider_order(prefs: List[str]) -> List[str]:
    order: List[str] = []
    available = _available_providers()
    if not available:
        return order
    tokens = prefs or ["auto"]
    for token in tokens:
        if token == "auto":
            for prov in available:
                if prov not in order:
                    order.append(prov)
            continue
        if token in available and token not in order:
            order.append(token)
    if not order:
        order.extend(available)
    return order


def _provider_order_for_context(context: str) -> List[str]:
    prefs = config.TRANSCRIBE_PROVIDER_OVERRIDES.get(context) or []
    if not prefs:
        prefs = config.TRANSCRIBE_PROVIDER_DEFAULT
    order = _expand_provider_order(prefs)
    if not order:
        raise RuntimeError("No transcription providers available. Configure API keys or provider preferences.")
    return order


def _mime_from_ext(file_ext: str) -> str:
    ext = (file_ext or "").lower()
    return {
        "webm": "audio/webm",
        "ogg": "audio/ogg",
        "mp3": "audio/mp3",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
    }.get(ext, "audio/wav")


def _transcribe_with_gemini(
    audio_bytes: bytes,
    instructions: str,
    mime_type: str,
    model: Optional[str] = None,
) -> TranscriptionResult:
    message = HumanMessage(
        content=[
            {"type": "text", "text": instructions},
            {
                "type": "file",
                "source_type": "base64",
                "mime_type": mime_type,
                "data": b64encode(audio_bytes).decode("utf-8"),
            },
        ]
    )
    response, key_index = invoke_google([message], model=model)
    text = str(getattr(response, "content", response))
    return TranscriptionResult(
        text=text,
        provider="gemini",
        model=model or config.GOOGLE_MODEL,
        meta={"key_index": key_index},
    )


def _transcribe_with_openai_result(
    audio_bytes: bytes,
    file_ext: str,
    language: Optional[str],
    prompt: Optional[str],
) -> TranscriptionResult:
    text = transcribe_with_openai(audio_bytes, file_ext=file_ext, language=language, prompt=prompt)
    return TranscriptionResult(
        text=text,
        provider="openai",
        model=config.OPENAI_TRANSCRIBE_MODEL,
    )


def transcribe_audio(
    audio_bytes: bytes,
    *,
    file_ext: str = "webm",
    mime_type: Optional[str] = None,
    instructions: Optional[str] = None,
    language_hint: Optional[str] = None,
    context: str = CONTEXT_INTERACTION,
) -> TranscriptionResult:
    if context not in _ALL_CONTEXTS:
        # Allow custom contexts but treat as default
        order = _expand_provider_order(config.TRANSCRIBE_PROVIDER_DEFAULT)
    else:
        order = _provider_order_for_context(context)
    if not order:
        raise RuntimeError("No transcription providers configured.")
    instruction_text = instructions or "Transcribe this audio recording."
    mime = mime_type or _mime_from_ext(file_ext)
    last_err: Optional[Exception] = None
    for provider_name in order:
        try:
            if provider_name == "gemini":
                return _transcribe_with_gemini(audio_bytes, instruction_text, mime)
            if provider_name == "openai":
                return _transcribe_with_openai_result(
                    audio_bytes,
                    file_ext=file_ext,
                    language=language_hint,
                    prompt=instruction_text if instruction_text else None,
                )
            raise RuntimeError(f"Unsupported transcription provider '{provider_name}'")
        except Exception as exc:  # noqa: PERF203
            last_err = exc
            logger.warning("Transcription via %s failed: %s", provider_name, exc)
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No transcription providers succeeded.")


def invoke_google(messages: List[HumanMessage], model: str | None = None) -> Tuple[object, int]:
    """Try Gemini clients in order (no internal retries). Returns (response, key_index).

    If `model` is provided, use a transient set of clients for that model.
    """
    last_err: Optional[Exception] = None
    llms: List[ChatGoogleGenerativeAI]
    if model and model != config.GOOGLE_MODEL:
        # Build a temporary rotation with the requested model
        llms = [ChatGoogleGenerativeAI(model=model, api_key=k) for k in GOOGLE_KEYS]
    else:
        llms = GOOGLE_LLMS
    for idx, llm in enumerate(llms):
        try:
            # Disable internal retries by overriding keyword
            return llm.invoke(messages, max_retries=0), idx
        except Exception as e:
            last_err = e
            logger.warning(
                "Gemini invoke failed on key_index=%s: %s", idx, str(e)
            )
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")


def title_with_openai(text: str) -> str:
    """Generate a short title via OpenAI (LangChain)."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.3)
    prompt = (
        "Return exactly one short title (5–8 words) for the transcription below. "
        "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
        "Output only the title on a single line.\n\n" + text
    )
    resp = llm.invoke(prompt)
    raw = str(getattr(resp, "content", resp))
    return normalize_title_output(raw)


def openai_chat(messages: list[HumanMessage], model: str | None = None, temperature: float = 0.2) -> str:
    """Generic OpenAI chat wrapper returning content text."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    use_model = model or config.OPENAI_NARRATIVE_MODEL
    llm = ChatOpenAI(model=use_model, api_key=config.OPENAI_API_KEY, temperature=temperature)
    resp = llm.invoke(messages)
    return str(getattr(resp, "content", resp))


def normalize_title_output(raw: str) -> str:
    """Coerce LLM output into a single, clean title line.

    - Removes markdown (bullets, bold/italics) and boilerplate prefaces
    - Picks the first plausible title line
    - Trims excessive punctuation and length
    """
    try:
        text = (raw or "").strip()
        if not text:
            return "Untitled"
        # Remove obvious prefaces
        lower = text.lower()
        if "here are" in lower and ":" in text:
            # Cut off everything up to and including the first colon
            text = text.split(":", 1)[-1].strip()
        # Split lines and scan for first candidate
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        candidates = []
        for line in lines:
            # Skip section headings that end with a colon
            if line.endswith(":"):
                continue
            # Remove common list markers
            l = line
            for prefix in ("- ", "* ", "• ", "1. ", "2. ", "3. ", "-", "*", "•"):
                if l.startswith(prefix):
                    l = l[len(prefix):].strip()
            # Strip markdown bold/italics markers
            l = l.replace("**", "").replace("__", "").replace("*", "").replace("_", "").strip()
            if l:
                candidates.append(l)
        if not candidates:
            candidates = [text]
        title = candidates[0]
        # If still contains multiple suggestions separated by bullets or semicolons, take first chunk
        for sep in [" • ", " | ", ";", "  -  ", "  *  "]:
            if sep in title:
                title = title.split(sep, 1)[0].strip()
        # Trim quotes and trailing punctuation
        title = title.strip().strip('"').strip("'")
        while title and title[-1] in [".", ":", "-", "|", ";"]:
            title = title[:-1].rstrip()
        # Limit length sensibly without cutting words mid-way
        if len(title) > 80:
            parts = title.split()
            out = []
            for p in parts:
                if len(" ".join(out + [p])) <= 80:
                    out.append(p)
                else:
                    break
            if out:
                title = " ".join(out)
        return title or "Untitled"
    except Exception:
        return "Untitled"


def transcribe_with_openai(
    audio_bytes: bytes,
    file_ext: str = "wav",
    language: Optional[str] = None,
    prompt: Optional[str] = None,
) -> str:
    """Transcribe audio using OpenAI Whisper via the official SDK.

    This avoids version mismatches in LangChain parsers and works reliably with bytes.
    """
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    bio = io.BytesIO(audio_bytes)
    bio.name = f"audio.{file_ext}"
    kwargs = {
        "model": config.OPENAI_TRANSCRIBE_MODEL,
        "file": bio,
        "response_format": "text",
    }
    hint = (language or "").strip()
    if prompt:
        kwargs["prompt"] = prompt
    elif hint:
        kwargs["prompt"] = (
            f"The speaker may be using {hint}. Transcribe in the language actually spoken using its usual writing system. "
            "Do not translate."
        )
    resp = client.audio.transcriptions.create(**kwargs)
    return resp if isinstance(resp, str) else getattr(resp, "text", "")


def tts_with_openai(text: str, voice: str = "alloy", fmt: str = "mp3") -> bytes:
    """Synthesize speech for a short phrase using OpenAI TTS.

    Returns raw audio bytes. Caller is responsible for persisting to a file.
    """
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI TTS not configured.")
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    # Prefer modern TTS model if available; fallback is handled via config
    model = config.OPENAI_TTS_MODEL
    # API accepts 'audio.speech.create' with input, voice, model
    # Some SDKs use 'format' or 'response_format'. We'll try 'format'.
    try:
        resp = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            format=fmt,
        )
        # Depending on SDK, resp could expose .read() or .content
        data = getattr(resp, "content", None)
        if data is None and hasattr(resp, "read"):
            data = resp.read()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    except Exception:
        # Fallback older shape
        try:
            resp = client.audio.speech.create(model=model, voice=voice, input=text)
            data = getattr(resp, "content", None)
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception as e:
            raise e
    # If all else fails
    raise RuntimeError("TTS synthesis failed.")


def translate_text(text: str, to_language: str, from_language: str | None = None) -> str:
    """Translate short text into the requested language using OpenAI chat.

    Returns only the translation, no quotes, no extra text.
    """
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI translation not configured.")
    llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.0)
    prompt = (
        (f"Translate this phrase from {from_language} to {to_language}:\n" if from_language else f"Translate this phrase into {to_language}:\n")
        + text
        + "\nReturn only the translation, no quotes, no notes."
    )
    resp = llm.invoke(prompt)
    return str(getattr(resp, "content", resp)).strip().strip('"').strip("'")


def romanize(text: str, language: str) -> str:
    """Return a simple pronunciation/romanization line for the target language.

    Currently optimized for Japanese (romaji). For other languages, returns text.
    """
    if not text:
        return ""
    lang = (language or "").strip().lower()
    if "japanese" in lang or "ja" == lang:
        if not config.OPENAI_API_KEY:
            return ""
        llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.0)
        prompt = (
            "Provide romaji for this Japanese phrase. Return only the romaji, no quotes or notes.\n" + text
        )
        try:
            resp = llm.invoke(prompt)
            return str(getattr(resp, "content", resp)).strip().strip('"').strip("'")
        except Exception:
            return ""
    return ""


def makes_sense(text: str, language: str | None = None) -> bool:
    """Classify whether the text is a simple, coherent utterance in the given language.

    Returns True/False. Uses OpenAI (low temperature) for a strict yes/no.
    """
    try:
        if not text:
            return False
        if not config.OPENAI_API_KEY:
            return bool(text.strip())
        llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.0)
        lang = (language or "").strip() or "the target language"
        prompt = (
            f"Answer yes or no: Is this a short, coherent, appropriate utterance in {lang}?\n"
            f"Text: {text}\n"
            "Answer strictly 'yes' or 'no'."
        )
        resp = llm.invoke(prompt)
        out = str(getattr(resp, "content", resp)).strip().lower()
        return out.startswith('y')
    except Exception:
        return False
