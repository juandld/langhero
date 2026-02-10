"""
Centralized configuration and paths for the backend.

This module exists to keep magic strings and environment reading in one place
so the rest of the codebase can import from here without repeating logic.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Base application directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_NOTES_DIR = os.path.join(BASE_DIR, "voice_notes")
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "transcriptions")
EXAMPLES_AUDIO_DIR = os.path.join(BASE_DIR, "examples_audio")

# Scenario/scoring defaults (override via env vars if desired)
DEFAULT_SUCCESS_POINTS = int(os.getenv("DEFAULT_SUCCESS_POINTS", "10"))
DEFAULT_FAILURE_LIFE_COST = int(os.getenv("DEFAULT_FAILURE_LIFE_COST", "1"))

# Models and providers
def _normalize_google_model(name: str) -> str:
    """Normalize Gemini model names to compatible forms for Google Generative AI.

    Some environments/sdks reject explicit version suffixes like "-002". Prefer
    base or "-latest" variants to maximize compatibility.
    """
    if not name:
        return "gemini-2.5-flash"
    lowered = name.strip().lower().replace(" ", "-")
    # If user provided an explicit version (e.g., -001/-002), prefer -latest
    for suffix in ("-001", "-002", "-003"):
        if lowered.endswith(suffix):
            base = lowered[: -len(suffix)]
            return base + "latest" if base.endswith("-") else base + "-latest"
    return lowered

# Allow an exact override that bypasses normalization.
_GOOGLE_MODEL_EXACT = os.getenv("GOOGLE_MODEL_EXACT")
if _GOOGLE_MODEL_EXACT:
    GOOGLE_MODEL = _GOOGLE_MODEL_EXACT.strip()
else:
    GOOGLE_MODEL = _normalize_google_model(os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"))
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
OPENAI_TITLE_MODEL = os.getenv("OPENAI_TITLE_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_NARRATIVE_MODEL = os.getenv("OPENAI_NARRATIVE_MODEL", "gpt-4o")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")

def collect_google_api_keys() -> list[str]:
    keys = []
    for name in [
        "GOOGLE_API_KEY",
        "GOOGLE_API_KEY_1",
        "GOOGLE_API_KEY_2",
        "GOOGLE_API_KEY_3",
    ]:
        val = os.getenv(name)
        if val and val not in keys:
            keys.append(val)
    return keys


def _parse_provider_pref(raw: Optional[str]) -> list[str]:
    """Parse a comma-separated provider preference list.

    Accepted tokens: 'auto', 'gemini', 'openai'. Returns normalized lowercase entries.
    """
    if not raw:
        return []
    prefs: list[str] = []
    for token in raw.split(","):
        tok = token.strip().lower()
        if not tok:
            continue
        if tok in {"auto", "gemini", "openai"}:
            prefs.append(tok)
    return prefs


# Provider preference order per transcription context
TRANSCRIBE_PROVIDER_DEFAULT = _parse_provider_pref(os.getenv("TRANSCRIBE_PROVIDER_DEFAULT", "auto"))
TRANSCRIBE_PROVIDER_OVERRIDES = {
    "interaction": _parse_provider_pref(os.getenv("TRANSCRIBE_INTERACTION_PROVIDER", "openai,gemini")),
    # Streaming defaults to OpenAI Whisper — a dedicated ASR model that doesn't
    # hallucinate like Gemini's multimodal transcription does.
    "streaming": _parse_provider_pref(os.getenv("TRANSCRIBE_STREAMING_PROVIDER", "openai,gemini")),
    "translate": _parse_provider_pref(os.getenv("TRANSCRIBE_TRANSLATE_PROVIDER")),
    "imitate": _parse_provider_pref(os.getenv("TRANSCRIBE_IMITATE_PROVIDER")),
    "notes": _parse_provider_pref(os.getenv("TRANSCRIBE_NOTES_PROVIDER")),
}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    val = str(raw).strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


# Demo/trial cost controls (marketing mode)
# - Demo mode should be near-zero cost: prefer cached video results and deterministic import fallbacks.
DEMO_MODE = _env_flag("DEMO_MODE", default=False)
# When true, /api/scenarios/from_video only serves cache hits (no download/transcribe/LLM).
DEMO_VIDEO_CACHE_ONLY = _env_flag("DEMO_VIDEO_CACHE_ONLY", default=True)
# When false, /api/stories/import skips LLM scenario generation and uses deterministic fallback only.
DEMO_ALLOW_LLM_IMPORT = _env_flag("DEMO_ALLOW_LLM_IMPORT", default=False)
# When true, disable real streaming websocket (force clients to use /stream/mock).
DEMO_DISABLE_STREAMING = _env_flag("DEMO_DISABLE_STREAMING", default=True)

# Security / abuse controls (defaults are conservative for unauthenticated endpoints).
ALLOW_LOCAL_IMPORT_PATHS = _env_flag("ALLOW_LOCAL_IMPORT_PATHS", default=False)
URL_FETCH_MAX_BYTES = int(os.getenv("URL_FETCH_MAX_BYTES", "1500000"))
URL_FETCH_TIMEOUT_S = float(os.getenv("URL_FETCH_TIMEOUT_S", "10"))

# Optional admin gating for dangerous endpoints (recommended for any public deployment).
ADMIN_API_KEY = (os.getenv("ADMIN_API_KEY") or "").strip()
REQUIRE_ADMIN_FOR_IMPORT = _env_flag("REQUIRE_ADMIN_FOR_IMPORT", default=False)
REQUIRE_ADMIN_FOR_PUBLISH = _env_flag("REQUIRE_ADMIN_FOR_PUBLISH", default=False)
REQUIRE_ADMIN_FOR_STREAM = _env_flag("REQUIRE_ADMIN_FOR_STREAM", default=False)

# Appwrite auth (magic link + JWT verification).
APPWRITE_ENDPOINT = (os.getenv("APPWRITE_ENDPOINT") or "").strip()
APPWRITE_PROJECT_ID = (os.getenv("APPWRITE_PROJECT_ID") or "").strip()
APPWRITE_API_KEY = (os.getenv("APPWRITE_API_KEY") or "").strip()

REQUIRE_AUTH_FOR_IMPORT = _env_flag("REQUIRE_AUTH_FOR_IMPORT", default=False)
REQUIRE_AUTH_FOR_PUBLISH = _env_flag("REQUIRE_AUTH_FOR_PUBLISH", default=False)
REQUIRE_AUTH_FOR_STREAM = _env_flag("REQUIRE_AUTH_FOR_STREAM", default=False)

# Streaming caps (WebSocket /stream/interaction).
STREAM_MAX_CHUNK_BYTES = int(os.getenv("STREAM_MAX_CHUNK_BYTES", "262144"))  # 256 KiB
STREAM_MAX_BUFFER_BYTES = int(os.getenv("STREAM_MAX_BUFFER_BYTES", "2000000"))  # ~2 MB rolling buffer
STREAM_MAX_SESSION_BYTES = int(os.getenv("STREAM_MAX_SESSION_BYTES", "8000000"))  # ~8 MB total per session

# Video ingest caps (ffmpeg/yt-dlp).
VIDEO_MAX_SECONDS = int(os.getenv("VIDEO_MAX_SECONDS", "300"))  # 5 minutes
YTDLP_MAX_FILESIZE_BYTES = int(os.getenv("YTDLP_MAX_FILESIZE_BYTES", "52428800"))  # 50 MiB

# Basic rate limiting (off by default; recommended for any public deployment).
RATE_LIMIT_ENABLED = _env_flag("RATE_LIMIT_ENABLED", default=False)
RATE_LIMIT_IMPORT_PER_MIN = int(os.getenv("RATE_LIMIT_IMPORT_PER_MIN", "10"))
RATE_LIMIT_PUBLISH_PER_MIN = int(os.getenv("RATE_LIMIT_PUBLISH_PER_MIN", "10"))
RATE_LIMIT_STREAM_CONN_PER_MIN = int(os.getenv("RATE_LIMIT_STREAM_CONN_PER_MIN", "30"))

# CORS origins
def _collect_allowed_origins() -> list[str]:
    """Collect allowed frontend origins from env or provide sensible dev defaults.

    Priority:
    1) Per-origin variables: ALLOWED_ORIGIN, ALLOWED_ORIGIN_1..N
    2) Back-compat: ALLOWED_ORIGINS (comma-separated)
    3) Local dev defaults (localhost on common Vite ports)
    """
    origins: list[str] = []
    keys = [k for k in os.environ.keys() if k == "ALLOWED_ORIGIN" or k.startswith("ALLOWED_ORIGIN_")]
    for key in sorted(keys):
        val = (os.getenv(key) or "").strip()
        if val and val not in origins:
            origins.append(val)
    if origins:
        return origins
    csv = (os.getenv("ALLOWED_ORIGINS") or "").strip()
    if csv:
        return [o.strip() for o in csv.split(",") if o.strip()]
    ports = [5173, 5174, 5175, 5176, 5177, 5178, 5179, 5180, 5199, 5200, 5201, 5202, 5203]
    origins = []
    for p in ports:
        origins.append(f"http://localhost:{p}")
        origins.append(f"http://127.0.0.1:{p}")
    return origins

ALLOWED_ORIGINS = _collect_allowed_origins()
ALLOWED_ORIGIN_REGEX = (os.getenv("ALLOWED_ORIGIN_REGEX") or "").strip() or None
