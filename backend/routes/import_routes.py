"""
Story and video import endpoints.
"""

import asyncio
import urllib.parse
from fastapi import APIRouter, Request, HTTPException
import config
import url_fetch
import usage_log as usage
import import_cache
from models import StoryImportRequest, AutoImportRequest
from story_import import build_imported_scenarios
from scenario_normalize import normalize_scenarios
from security import require_admin, require_auth, rate_limit, client_ip_from_headers
from services.scenarios import reload_scenarios
from services.video import generate_scenarios_from_video

router = APIRouter(prefix="/api", tags=["import"])


def _validate_import_url_or_path(url: str) -> None:
    """Enforce SSRF-safe URL rules for remote imports."""
    raw = str(url or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="missing_url")

    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme in {"http", "https"}:
        try:
            url_fetch.validate_public_url(raw)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return

    if config.ALLOW_LOCAL_IMPORT_PATHS and parsed.scheme == "":
        return

    raise HTTPException(status_code=400, detail="invalid_scheme")


def _seems_video_url(url: str) -> bool:
    """Check if URL appears to be a video."""
    u = str(url or "").strip()
    if not u:
        return False
    lower = u.lower()

    try:
        parsed = urllib.parse.urlsplit(u)
        host = (parsed.hostname or "").lower()
    except Exception:
        host = ""

    # Known video hosts
    video_hosts = {
        "youtube.com", "www.youtube.com", "youtu.be",
        "vimeo.com", "www.vimeo.com",
        "tiktok.com", "www.tiktok.com",
        "twitch.tv", "www.twitch.tv",
        "dailymotion.com", "www.dailymotion.com",
    }
    if host in video_hosts:
        return True

    # Common media extensions
    for ext in (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac", ".m3u8"):
        if lower.split("?", 1)[0].split("#", 1)[0].endswith(ext):
            return True
    return False


async def _handle_video_import(url: str, target_language: str, max_scenes: int, activate: bool):
    """Handle video URL import with caching."""
    cache_key = import_cache.video_scenarios_cache_key(url, target_language=target_language, max_scenes=max_scenes)
    scenarios = import_cache.load_cached_video_scenarios(cache_key)
    cache_hit = scenarios is not None
    cache_saved = False

    if config.DEMO_MODE and config.DEMO_VIDEO_CACHE_ONLY and not scenarios:
        raise HTTPException(status_code=403, detail="demo_mode_cache_only")

    if not scenarios:
        try:
            scenarios = await asyncio.to_thread(generate_scenarios_from_video, url, target_language, max_scenes)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"video_import_failed:{e}")

    if not scenarios:
        raise HTTPException(status_code=502, detail="generation_failed")

    dict_scenarios = [s for s in scenarios if isinstance(s, dict)]
    if dict_scenarios:
        normalize_scenarios(dict_scenarios, ensure_advanced=True)

    if not cache_hit and dict_scenarios:
        try:
            import_cache.save_cached_video_scenarios(cache_key, dict_scenarios)
            cache_saved = True
        except Exception:
            cache_saved = False

    if activate:
        reload_scenarios(scenarios)

    return {
        "kind": "video",
        "url": url,
        "target_language": target_language,
        "activated": activate,
        "cached": cache_hit,
        "cache_saved": cache_saved,
        "scenarios": scenarios,
    }


@router.post("/stories/import")
async def import_story(body: StoryImportRequest, request: Request):
    """Import a story seed (text or source_url) and return playable scenarios."""
    if not (body.attest_rights is True):
        raise HTTPException(status_code=400, detail="attest_rights_required")

    headers = {k.lower(): v for (k, v) in request.headers.items()}
    require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_IMPORT))

    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("import_story", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))

    text = (body.text or "").strip()
    source_meta = None

    if not text and (body.source_url or "").strip():
        source_url = str(body.source_url or "").strip()
        _validate_import_url_or_path(source_url)
        try:
            source_meta = await asyncio.to_thread(
                url_fetch.fetch_url_text,
                source_url,
                timeout_s=float(config.URL_FETCH_TIMEOUT_S),
                max_bytes=int(config.URL_FETCH_MAX_BYTES),
            )
            text = str(source_meta.get("text") or "").strip()
            try:
                usage.log_usage(event="url_fetch", provider="http", model="urllib", key_label="n/a", status="success")
            except Exception:
                pass
        except ValueError as ve:
            try:
                usage.log_usage(event="url_fetch", provider="http", model="urllib", key_label="n/a", status=str(ve))
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception:
            try:
                usage.log_usage(event="url_fetch", provider="http", model="urllib", key_label="n/a", status="error")
            except Exception:
                pass
            raise HTTPException(status_code=502, detail="source_url_fetch_failed")

    if not text:
        raise HTTPException(status_code=400, detail="missing_text")

    scenarios, target_language = build_imported_scenarios(
        text=text,
        setting=(body.setting or (source_meta.get("title") if isinstance(source_meta, dict) else None)),
        target_language=body.target_language,
        max_scenes=int(body.max_scenes or 6),
    )

    activated = False
    if body.activate:
        try:
            reload_scenarios(scenarios)
            activated = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"activate_failed:{e}")

    payload = {"scenarios": scenarios, "target_language": target_language, "activated": activated}
    if isinstance(source_meta, dict):
        payload["source"] = {
            "url": source_meta.get("url"),
            "final_url": source_meta.get("final_url"),
            "title": source_meta.get("title"),
            "content_type": source_meta.get("content_type"),
        }
    return payload


@router.post("/scenarios/from_video")
async def api_generate_scenarios_from_video(request: Request):
    """Generate and activate scenarios from a video URL."""
    body = await request.json()
    url = (body or {}).get("url")
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="missing_url")

    _validate_import_url_or_path(url)

    headers = {k.lower(): v for (k, v) in request.headers.items()}
    require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_IMPORT))

    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("import_video", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))

    attest_rights = bool((body or {}).get("attest_rights", False))
    if not attest_rights:
        raise HTTPException(status_code=400, detail="attest_rights_required")

    target_language = (body or {}).get("target_language") or "Japanese"
    max_scenes = (body or {}).get("max_scenes") or 5
    activate = bool((body or {}).get("activate", True))

    result = await _handle_video_import(url, target_language, max_scenes, activate)
    return {
        "status": "ok",
        "count": len(result["scenarios"]),
        **result,
    }


@router.post("/import/auto")
async def api_import_auto(body: AutoImportRequest, request: Request):
    """Unified importer: takes an optional URL and optional text.

    If URL looks like video -> routes to the video pipeline.
    Otherwise -> fetches readable text from the URL and compiles it.
    If no URL -> compiles the provided text.
    """
    if not (body.attest_rights is True):
        raise HTTPException(status_code=400, detail="attest_rights_required")

    headers = {k.lower(): v for (k, v) in request.headers.items()}
    require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_IMPORT))

    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("import_auto", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))

    url = (body.url or "").strip()
    text = (body.text or "").strip()
    target_language = body.target_language
    max_scenes = int(body.max_scenes or 6)
    activate = bool(body.activate)

    if not url and not text:
        raise HTTPException(status_code=400, detail="missing_input")

    # Video path (default for YouTube / direct media URLs)
    if url and _seems_video_url(url):
        _validate_import_url_or_path(url)
        return await _handle_video_import(url, target_language or "Japanese", max_scenes, activate)

    # Web/text path (default for arbitrary URLs with readable text)
    source_meta = None
    combined_text = text

    if url:
        _validate_import_url_or_path(url)
        try:
            source_meta = await asyncio.to_thread(
                url_fetch.fetch_url_text,
                url,
                timeout_s=float(config.URL_FETCH_TIMEOUT_S),
                max_bytes=int(config.URL_FETCH_MAX_BYTES),
            )
            fetched_text = str(source_meta.get("text") or "").strip()
            combined_text = "\n\n".join([t for t in [text, fetched_text] if t.strip()])
            try:
                usage.log_usage(event="url_fetch", provider="http", model="urllib", key_label="n/a", status="success")
            except Exception:
                pass
        except ValueError as ve:
            # If URL fetch didn't yield readable text, fall back to video ingest
            if str(ve) in {"no_text_found"}:
                return await _handle_video_import(url, target_language or "Japanese", max_scenes, activate)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception:
            raise HTTPException(status_code=502, detail="source_url_fetch_failed")

    scenarios, resolved_language = build_imported_scenarios(
        text=combined_text,
        setting=(body.setting or (source_meta.get("title") if isinstance(source_meta, dict) else None)),
        target_language=target_language,
        max_scenes=max_scenes,
    )

    if activate:
        try:
            reload_scenarios(scenarios)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"activate_failed:{e}")

    payload = {
        "kind": ("web" if url else "text"),
        "url": url or None,
        "target_language": resolved_language,
        "activated": activate,
        "scenarios": scenarios,
    }
    if isinstance(source_meta, dict):
        payload["source"] = {
            "url": source_meta.get("url"),
            "final_url": source_meta.get("final_url"),
            "title": source_meta.get("title"),
            "content_type": source_meta.get("content_type"),
        }
    return payload
