from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional


IMPORT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "import_cache")


def _video_scenarios_dir() -> str:
    return os.path.join(IMPORT_CACHE_DIR, "video_scenarios")
CACHE_VERSION = 1


def _ensure_dirs() -> None:
    os.makedirs(_video_scenarios_dir(), exist_ok=True)


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class VideoScenariosCacheKey:
    source_id: str
    target_language: str
    max_scenes: int
    version: int = CACHE_VERSION


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def normalize_youtube_id(url: str) -> Optional[str]:
    """Return the YouTube video id if present."""
    if not isinstance(url, str):
        return None
    u = url.strip()
    if not u:
        return None
    # youtu.be/<id>
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u)
    if m:
        return m.group(1)
    # youtube.com/watch?v=<id>
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", u)
    if m:
        return m.group(1)
    return None


def normalize_video_source_id(url: str) -> str:
    """Normalize URL for caching (avoid treating the same YouTube video as different keys)."""
    yt = normalize_youtube_id(url)
    if yt:
        return f"youtube:{yt}"
    return f"url:{url.strip()}"


def video_scenarios_cache_key(url: str, *, target_language: str, max_scenes: Any) -> VideoScenariosCacheKey:
    source_id = normalize_video_source_id(url)
    lang = str(target_language or "").strip()[:40] or "Japanese"
    scenes = max(1, min(_coerce_int(max_scenes, 5), 12))
    return VideoScenariosCacheKey(source_id=source_id, target_language=lang, max_scenes=scenes)


def _video_cache_path(key: VideoScenariosCacheKey) -> str:
    _ensure_dirs()
    fingerprint = _sha256_hex(json.dumps(key.__dict__, sort_keys=True))
    return os.path.join(_video_scenarios_dir(), f"{fingerprint}.json")


def load_cached_video_scenarios(key: VideoScenariosCacheKey) -> Optional[list[dict]]:
    path = _video_cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("version") != CACHE_VERSION:
        return None
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return None
    return [s for s in scenarios if isinstance(s, dict)]


def save_cached_video_scenarios(key: VideoScenariosCacheKey, scenarios: list[dict]) -> None:
    path = _video_cache_path(key)
    payload = {
        "version": CACHE_VERSION,
        "created_at_ms": _now_ms(),
        "key": key.__dict__,
        "scenarios": [s for s in (scenarios or []) if isinstance(s, dict)],
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
