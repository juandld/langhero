import logging

# Silence verbose loggers
logging.basicConfig(level=logging.INFO)
loggers_to_silence = [
    "google.generativeai",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
]
for logger_name in loggers_to_silence:
    # Use ERROR to reduce noisy quota retry warnings
    logging.getLogger(logger_name).setLevel(logging.ERROR)

import json

from typing import Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, Response, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services import (
    process_interaction,
    get_notes,
    transcribe_and_save,
    generate_option_suggestions,
    list_scenarios,
    reload_scenarios,
    list_scenario_versions,
    save_scenarios_version,
    activate_scenario_version,
    imitate_say,
    generate_scenarios_from_video,
)
from models import TagsUpdate, StoryImportRequest, AutoImportRequest
from story_import import build_imported_scenarios
from utils import on_startup
import uvicorn
import socket
import os
from datetime import datetime
import uuid
import asyncio
from langchain_core.messages import HumanMessage
import providers
import config
import voice_cache
import published_runs
from mock_stream import build_session, MockStreamingSession
from streaming import create_session, StreamingSession
from scenario_normalize import normalize_scenarios
import import_cache
import usage_log as usage
import url_fetch
import urllib.parse
import time


@asynccontextmanager
async def lifespan(_: FastAPI):
    await on_startup()
    yield


app = FastAPI(lifespan=lifespan)

# ----------------- Security helpers -----------------

_RATE_STATE: dict[str, dict[str, tuple[int, int]]] = {}


def _client_ip_from_headers(headers: dict) -> str:
    try:
        xff = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
        if isinstance(xff, str) and xff.strip():
            return xff.split(",")[0].strip()
    except Exception:
        pass
    return "unknown"


def _rate_limit(bucket: str, ip: str, limit_per_min: int) -> None:
    if not config.RATE_LIMIT_ENABLED:
        return
    try:
        limit = int(limit_per_min)
    except Exception:
        limit = 0
    if limit <= 0:
        return
    now_bucket = int(time.time() // 60)
    bucket_map = _RATE_STATE.setdefault(bucket, {})
    prev = bucket_map.get(ip)
    if not prev or prev[0] != now_bucket:
        bucket_map[ip] = (now_bucket, 1)
        return
    count = int(prev[1]) + 1
    bucket_map[ip] = (now_bucket, count)
    if count > limit:
        raise HTTPException(status_code=429, detail="rate_limited")


def _is_admin(headers: dict) -> bool:
    key = (config.ADMIN_API_KEY or "").strip()
    if not key:
        return False
    # Accept either X-Admin-Key or Authorization: Bearer <key>
    try:
        supplied = headers.get("x-admin-key") or headers.get("X-Admin-Key") or ""
        if isinstance(supplied, str) and supplied.strip() == key:
            return True
    except Exception:
        pass
    try:
        auth = headers.get("authorization") or headers.get("Authorization") or ""
        if isinstance(auth, str) and auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1].strip()
            if token == key:
                return True
    except Exception:
        pass
    return False


def _require_admin(headers: dict, *, flag: bool) -> None:
    if not flag:
        return
    if not (config.ADMIN_API_KEY or "").strip():
        raise HTTPException(status_code=500, detail="admin_key_not_configured")
    if not _is_admin(headers):
        raise HTTPException(status_code=401, detail="admin_required")

# Configure CORS to allow requests from the SvelteKit frontend.
# Prefer env-configured origins/regex from config; otherwise fall back to localhost defaults.
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

allowed_regex = getattr(config, "ALLOWED_ORIGIN_REGEX", None)
if allowed_regex:
    cors_kwargs["allow_origin_regex"] = allowed_regex
else:
    origins = getattr(config, "ALLOWED_ORIGINS", None)
    if origins:
        cors_kwargs["allow_origins"] = origins
    else:
        cors_kwargs["allow_origin_regex"] = r"^http://(localhost|127\\.0\\.0\\.1)(:\\d+)?$"

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Mount static files directory for voice notes
VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))
NARRATIVES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'narratives'))
EXAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples_audio'))
# Ensure mount directories exist before mounting static routes
os.makedirs(VOICE_NOTES_DIR, exist_ok=True)
os.makedirs(EXAMPLES_DIR, exist_ok=True)
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")
app.mount("/examples", StaticFiles(directory=EXAMPLES_DIR), name="examples")

@app.get("/api/meta")
async def api_meta():
    """Lightweight runtime flags for the frontend (dev/demo UX)."""
    return {
        "demo_mode": bool(config.DEMO_MODE),
        "demo_video_cache_only": bool(config.DEMO_VIDEO_CACHE_ONLY),
        "demo_allow_llm_import": bool(config.DEMO_ALLOW_LLM_IMPORT),
        "demo_disable_streaming": bool(config.DEMO_DISABLE_STREAMING),
        "utc_now": datetime.utcnow().isoformat(),
    }


@app.get("/api/usage/weekly")
async def api_usage_weekly(year: Optional[int] = None, week: Optional[int] = None):
    """Weekly rollup of usage events (for dev tools / cost estimation)."""
    return usage.load_weekly_summary(year=year, iso_week=week)


@app.get("/api/usage/recent")
async def api_usage_recent(limit: int = 200, days: int = 7):
    """Recent raw usage events (newest-first) from daily JSONL logs."""
    return {
        "limit": max(1, min(int(limit or 200), 2000)),
        "days": max(1, min(int(days or 7), 60)),
        "events": usage.load_recent_events(limit=limit, days=days),
    }


@app.websocket("/stream/mock")
async def mock_stream_endpoint(websocket: WebSocket):
    """Mock streaming endpoint that echoes chunk metadata and fake transcripts."""
    await websocket.accept()

    session: MockStreamingSession = build_session({})
    pending_chunk: Optional[bytes] = None
    reason = "client_stop"

    try:
        first_message = await websocket.receive()
    except WebSocketDisconnect:
        return

    msg_type = first_message.get("type")
    if msg_type == "websocket.receive":
        text_payload = first_message.get("text")
        bytes_payload = first_message.get("bytes")
        if text_payload is not None:
            try:
                payload = json.loads(text_payload)
                if isinstance(payload, dict):
                    session = build_session(payload)
            except json.JSONDecodeError:
                # Treat non-JSON text as an info message after ready event
                pending_chunk = None
            else:
                pending_chunk = None
        elif bytes_payload is not None:
            pending_chunk = bytes_payload
    elif msg_type == "websocket.disconnect":
        return

    await websocket.send_json(session.ready_event())

    if pending_chunk is not None:
        await websocket.send_json(session.register_chunk(pending_chunk))

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.receive":
                if message.get("bytes") is not None:
                    chunk = message.get("bytes") or b""
                    event = session.register_chunk(chunk)
                    await websocket.send_json(event)
                elif message.get("text") is not None:
                    text = (message.get("text") or "").strip()
                    lowered = text.lower()
                    if lowered in {"stop", "done", "finish"}:
                        reason = f"client_{lowered}"
                        break
                    await websocket.send_json(
                        {
                            "event": "info",
                            "message": text,
                        }
                    )
            elif msg_type == "websocket.disconnect":
                reason = "disconnect"
                break
    except WebSocketDisconnect:
        reason = "disconnect"

    await websocket.send_json(session.final_event(reason=reason))
    await websocket.close()


@app.websocket("/stream/interaction")
async def interaction_stream_endpoint(websocket: WebSocket):
    """Real streaming endpoint: emits partial transcripts, penalties, and final results."""
    if config.DEMO_MODE and config.DEMO_DISABLE_STREAMING:
        await websocket.accept()
        await websocket.send_json({"event": "error", "error": "demo_mode_streaming_disabled"})
        await websocket.close()
        return
    headers = {k.lower(): v for (k, v) in websocket.headers.items()}
    if bool(config.REQUIRE_ADMIN_FOR_STREAM):
        if not (config.ADMIN_API_KEY or "").strip():
            await websocket.accept()
            await websocket.send_json({"event": "error", "error": "admin_key_not_configured"})
            await websocket.close()
            return
        if not _is_admin(headers):
            await websocket.accept()
            await websocket.send_json({"event": "error", "error": "admin_required"})
            await websocket.close()
            return
    try:
        ip = (websocket.client.host if websocket.client else None) or _client_ip_from_headers(headers)
        _rate_limit("stream_connect", str(ip), int(getattr(config, "RATE_LIMIT_STREAM_CONN_PER_MIN", 30)))
    except HTTPException as he:
        await websocket.accept()
        await websocket.send_json({"event": "error", "error": str(getattr(he, "detail", "rate_limited"))})
        await websocket.close()
        return
    await websocket.accept()
    session: StreamingSession = create_session({})
    pending_chunk: Optional[bytes] = None
    total_bytes = 0
    try:
        max_chunk_bytes = int(config.STREAM_MAX_CHUNK_BYTES or 0)
    except Exception:
        max_chunk_bytes = 0
    try:
        max_session_bytes = int(config.STREAM_MAX_SESSION_BYTES or 0)
    except Exception:
        max_session_bytes = 0

    try:
        first_message = await websocket.receive()
    except WebSocketDisconnect:
        return

    msg_type = first_message.get("type")
    if msg_type == "websocket.receive":
        text_payload = first_message.get("text")
        bytes_payload = first_message.get("bytes")
        if text_payload is not None:
            try:
                payload = json.loads(text_payload)
                if isinstance(payload, dict):
                    session = create_session(payload)
            except json.JSONDecodeError:
                # treat text as command after ready phase
                pass
        elif bytes_payload is not None:
            pending_chunk = bytes_payload
    elif msg_type == "websocket.disconnect":
        return

    await websocket.send_json(
        {
            "event": "ready",
            "scenario_id": session.scenario_id,
            "target_language": session.target_language,
            "mode": session.mode,
            "lives_total": session.lives_total,
            "lives_remaining": session.lives_remaining,
            "score": session.score,
            "reward_points": session.points_per_success,
            "language_penalty_lives": session.language_penalty_lives,
            "incorrect_penalty_lives": session.incorrect_penalty_lives,
        }
    )

    if pending_chunk:
        if max_chunk_bytes > 0 and len(pending_chunk) > max_chunk_bytes:
            await websocket.send_json({"event": "error", "error": "stream_chunk_too_large"})
            await websocket.close()
            return
        total_bytes += len(pending_chunk)
        if max_session_bytes > 0 and total_bytes > max_session_bytes:
            await websocket.send_json({"event": "error", "error": "stream_session_bytes_exceeded"})
            await websocket.close()
            return
        await session.append_chunk(pending_chunk, websocket)

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")
            if msg_type == "websocket.receive":
                if message.get("bytes") is not None:
                    chunk = message.get("bytes") or b""
                    if max_chunk_bytes > 0 and len(chunk) > max_chunk_bytes:
                        await websocket.send_json({"event": "error", "error": "stream_chunk_too_large"})
                        break
                    total_bytes += len(chunk)
                    if max_session_bytes > 0 and total_bytes > max_session_bytes:
                        await websocket.send_json({"event": "error", "error": "stream_session_bytes_exceeded"})
                        break
                    await session.append_chunk(chunk, websocket)
                elif message.get("text") is not None:
                    text = (message.get("text") or "").strip().lower()
                    if text in {"stop", "done", "finish"}:
                        await session.finalize(websocket)
                        break
                    elif text in {"reset"}:
                        session = create_session(
                            {
                                "scenario_id": session.scenario_id,
                                "language": session.target_language,
                                "learner_language": session.learner_language,
                                "judge": getattr(session, "judge_story_weight", 0.0),
                            }
                        )
                        await websocket.send_json(
                            {
                                "event": "reset",
                                "scenario_id": session.scenario_id,
                                "target_language": session.target_language,
                                "mode": session.mode,
                                "lives_total": session.lives_total,
                                "lives_remaining": session.lives_remaining,
                                "score": session.score,
                                "reward_points": session.points_per_success,
                                "language_penalty_lives": session.language_penalty_lives,
                                "incorrect_penalty_lives": session.incorrect_penalty_lives,
                            }
                        )
                    else:
                        await websocket.send_json({"event": "info", "message": text})
            elif msg_type == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()

@app.post("/narrative/interaction")
async def handle_interaction(
    audio_file: UploadFile = File(...), 
    current_scenario_id: str = Form(...),
    lang: str = Form(None),
    judge: str = Form(None),
):
    """
    This endpoint receives audio and the current scenario ID,
    processes them, and returns the next scenario.
    """
    judge_value = None
    try:
        if judge is not None and str(judge).strip() != "":
            judge_value = float(judge)
    except Exception:
        judge_value = None
    result = process_interaction(audio_file.file, current_scenario_id, lang, judge=judge_value)
    return result

@app.post("/narrative/imitate")
async def imitate_endpoint(
    audio_file: UploadFile = File(...),
    expected: str = Form(...),
    next_scenario: int = Form(None),
    lang: str = Form(None),
):
    """Transcribe learner audio and check similarity to expected.

    Returns {success, score, heard, nextScenario?}
    """
    ct = (audio_file.content_type or '').lower()
    if 'webm' in ct:
        mime = 'audio/webm'
    elif 'ogg' in ct:
        mime = 'audio/ogg'
    elif 'm4a' in ct:
        mime = 'audio/mp4'
    elif 'mp3' in ct:
        mime = 'audio/mp3'
    else:
        mime = 'audio/wav'
    audio_bytes = audio_file.file.read()
    res = imitate_say(audio_bytes, mime, expected, lang)
    if res.get('success') and next_scenario is not None:
        # Attach the target scenario so the UI can advance
        try:
            ns = int(next_scenario)
            res['nextScenario'] = ns
        except Exception:
            pass
    return res

@app.post("/narrative/translate")
async def translate_endpoint(
    request: Request,
    text: str = Form(None),
    native: str = Form(...),
    target: str = Form(...),
    audio_file: UploadFile = File(None),
):
    """Translate user text (or speech) from native -> target and return pronunciation.

    Returns { native, target, pronunciation }
    """
    try:
        # If audio is provided, transcribe it first (assume native language)
        if audio_file is not None:
            ct = (audio_file.content_type or '').lower()
            if 'webm' in ct:
                mime = 'audio/webm'
            elif 'ogg' in ct:
                mime = 'audio/ogg'
            elif 'm4a' in ct:
                mime = 'audio/mp4'
            elif 'mp3' in ct:
                mime = 'audio/mp3'
            else:
                mime = 'audio/wav'
            audio_bytes = audio_file.file.read()
            result = providers.transcribe_audio(
                audio_bytes,
                file_ext=("webm" if "webm" in mime else "wav"),
                mime_type=mime,
                instructions="Transcribe this audio recording.",
                context=providers.CONTEXT_TRANSLATE,
            )
            native_text = result.text
        else:
            native_text = (text or '').strip()
        if not native_text:
            return Response(status_code=400)
        # Translate to target
        target_text = providers.translate_text(native_text, to_language=target, from_language=native)
        # Pronunciation (romaji) when target is Japanese
        pron = providers.romanize(target_text, target)
        return {"native": native_text, "target": target_text, "pronunciation": pron}
    except Exception as e:
        return {"error": str(e)}

@app.get("/narrative/options")
async def get_speaking_options(scenario_id: int, n_per_option: int = 3, lang: Optional[str] = None, native: Optional[str] = None, stage: Optional[str] = None):
    """Return child-friendly example utterances for the current scenario options.

    Query: scenario_id (int), n_per_option (int, default 3), lang (optional target language), stage (examples|hints)
    """
    try:
        data = generate_option_suggestions(
            scenario_id,
            n_per_option,
            target_language=lang or None,
            native_language=native or None,
            stage=stage or "examples",
        )
        return data
    except Exception as e:
        return {"question": "", "options": [], "error": str(e)}


@app.post("/api/tts")
async def api_tts(request: Request):
    """Return a cached/pre-rendered voice clip for a short phrase.

    Body JSON: { "text": "...", "language"?: "Japanese", "voice"?: "alloy", "format"?: "mp3" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    text = str((body or {}).get("text") or "").strip()
    if not text:
        return Response(status_code=400)

    language = (body or {}).get("language")
    voice = str((body or {}).get("voice") or "alloy").strip() or "alloy"
    fmt = str((body or {}).get("format") or "mp3").strip().lower() or "mp3"
    if fmt not in {"mp3", "wav", "opus"}:
        fmt = "mp3"

    try:
        meta = voice_cache.get_or_create_clip(text, language=language, voice=voice, fmt=fmt)
        return {
            **meta,
            "url": f"/examples/{meta['file']}",
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/notes")
async def read_notes():
    """API endpoint to retrieve all notes."""
    return get_notes()

@app.post("/api/notes")
async def create_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    date: str = Form(None),
    place: str = Form(None)
):
    """API endpoint to upload a new note."""
    ct = (file.content_type or '').lower()
    if 'webm' in ct:
        ext = 'webm'
    elif 'ogg' in ct:
        ext = 'ogg'
    elif 'm4a' in ct:
        ext = 'm4a'
    elif 'mp3' in ct:
        ext = 'mp3'
    else:
        ext = 'wav'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
    file_path = os.path.join(VOICE_NOTES_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    
    # Start transcription and title generation in the background
    print(f"File saved: {filename}. Adding transcription to background tasks.")
    background_tasks.add_task(transcribe_and_save, file_path)
    
    return {"filename": filename, "message": "File upload successful, transcription started."}

@app.post("/api/notes/{filename}/retry")
async def retry_note(background_tasks: BackgroundTasks, filename: str):
    """Manually trigger reprocessing (transcribe/title) for a specific note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    background_tasks.add_task(transcribe_and_save, file_path)
    return {"status": "queued"}

@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """API endpoint to delete a note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        # Delete associated JSON (and legacy txt)
        base_filename = os.path.splitext(filename)[0]
        json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
        legacy_txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.txt")
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(legacy_txt_path):
            os.remove(legacy_txt_path)
        return Response(status_code=200)
    return Response(status_code=404)

@app.patch("/api/notes/{filename}/tags")
async def update_tags(filename: str, payload: TagsUpdate):
    """Update user-defined tags for a note (stored in JSON)."""
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    # Ensure a JSON exists
    if not os.path.exists(json_path):
        return Response(status_code=404)
    try:
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Normalize tags into list of {label, color}
        tags = []
        for t in payload.tags:
            tags.append({"label": t.label, "color": t.color})
        data["tags"] = tags
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "tags": tags}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Narratives API -----------------

@app.get("/api/narratives")
async def list_narratives():
    if not os.path.exists(NARRATIVES_DIR):
        os.makedirs(NARRATIVES_DIR)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith('.txt')]
    return files

@app.get("/api/narratives/{filename}")
async def get_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
    return {"content": content}


@app.post("/api/stories/import")
async def import_story(body: StoryImportRequest, request: Request):
    """Import a story seed (text or source_url) and return playable scenarios."""
    if not (body.attest_rights is True):
        raise HTTPException(status_code=400, detail="attest_rights_required")
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    _require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    ip = (request.client.host if request.client else None) or _client_ip_from_headers(headers)
    _rate_limit("import_story", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))
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


@app.post("/api/published_runs")
async def publish_run(request: Request):
    """Publish a compiled scenario chain for sharing (explicit confirmation required)."""
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    _require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_PUBLISH))
    ip = (request.client.host if request.client else None) or _client_ip_from_headers(headers)
    _rate_limit("publish_run", str(ip), int(getattr(config, "RATE_LIMIT_PUBLISH_PER_MIN", 10)))
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")
    if body.get("attest_rights") is not True:
        raise HTTPException(status_code=400, detail="attest_rights_required")
    if body.get("confirm_publish") is not True:
        raise HTTPException(status_code=400, detail="confirm_publish_required")
    scenarios = body.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise HTTPException(status_code=400, detail="missing_scenarios")
    title = str(body.get("title") or "Published run")
    target_language = str(body.get("target_language") or body.get("targetLanguage") or "")
    run, delete_key = published_runs.create_published_run(
        title=title,
        target_language=target_language,
        scenarios=[s for s in scenarios if isinstance(s, dict)],
    )
    payload = published_runs.public_payload(run)
    payload["delete_key"] = delete_key
    return payload


@app.get("/api/published_runs/{public_id}")
async def get_published_run(public_id: str):
    run = published_runs.load_published_run(public_id)
    if not run:
        raise HTTPException(status_code=404, detail="not_found")
    return published_runs.public_payload(run)


@app.delete("/api/published_runs/{public_id}")
async def delete_published_run(public_id: str, request: Request):
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    _require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_PUBLISH))
    ip = (request.client.host if request.client else None) or _client_ip_from_headers(headers)
    _rate_limit("publish_delete", str(ip), int(getattr(config, "RATE_LIMIT_PUBLISH_PER_MIN", 10)))
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")
    delete_key = str(body.get("delete_key") or "")
    if not delete_key.strip():
        raise HTTPException(status_code=400, detail="missing_delete_key")
    ok = published_runs.delete_published_run(public_id, delete_key)
    if not ok:
        raise HTTPException(status_code=403, detail="delete_forbidden")
    return {"status": "ok"}

@app.delete("/api/narratives/{filename}")
async def delete_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return Response(status_code=200)
    return Response(status_code=404)

@app.post("/api/narratives")
async def create_narrative_from_notes(request: Request):
    """Create a simple narrative by concatenating selected notes' titles and transcriptions.

    Expects JSON body: [{"filename": "...wav"}, ...]
    Writes a .txt file into narratives/ and returns its filename.
    """
    try:
        items = await request.json()
        if not isinstance(items, list):
            return Response(status_code=400)
        parts = []
        for it in items:
            name = (it or {}).get('filename')
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ''
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r') as jf:
                    data = json.load(jf)
                title = data.get('title') or title
                text = data.get('transcription') or ''
            parts.append(f"# {title}\n\n{text}\n\n")
        if not parts:
            return Response(status_code=400)
        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        from datetime import datetime
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        with open(out, 'w') as f:
            f.write("\n".join(parts))
        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/narratives/generate")
async def generate_narrative(request: Request):
    """Generate a narrative from selected notes and optional extra context via Gemini/OpenAI.

    Body JSON:
    {
      "items": [{"filename": "...wav"}, ...],
      "extra_text": "optional",
      "provider": "auto" | "gemini" | "openai",
      "model": "optional override",
      "temperature": 0.2,
      "system": "optional system instruction"
    }
    Returns: {"filename": "narrative-...txt"}
    """
    try:
        body = await request.json()
        items = (body or {}).get("items", [])
        extra_text = (body or {}).get("extra_text", "")
        provider_choice = ((body or {}).get("provider") or "auto").lower()
        model_override = (body or {}).get("model")
        temperature = float((body or {}).get("temperature") or 0.2)
        system_inst = (body or {}).get("system") or (
            "You are an expert editor. Synthesize a cohesive, structured narrative from the provided notes and context. "
            "Focus on clarity, key insights, and concrete action items. Keep it concise and readable."
        )

        # Collect sources
        if not isinstance(items, list):
            return Response(status_code=400)
        sources = []
        for it in items:
            name = (it or {}).get("filename")
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ""
            if os.path.exists(json_path):
                import json
                with open(json_path, "r") as jf:
                    data = json.load(jf)
                title = data.get("title") or title
                text = data.get("transcription") or ""
            sources.append((title, text))

        if not sources and not extra_text.strip():
            return Response(status_code=400)

        # Build prompt
        parts = [system_inst.strip(), "\n\nContext Notes:\n"]
        for i, (title, text) in enumerate(sources, start=1):
            parts.append(f"[{i}] {title}\n{text}\n")
        if extra_text.strip():
            parts.append("\nAdditional Context:\n" + extra_text.strip() + "\n")
        parts.append("\nWrite the narrative now.")
        prompt_text = "\n".join(parts)

        # Call provider
        content = None
        key_index = None
        provider_used = provider_choice
        model_used = model_override or (config.GOOGLE_MODEL if provider_choice != "openai" else config.OPENAI_NARRATIVE_MODEL)
        if provider_choice in ("auto", "gemini"):
            try:
                resp, key_index = await asyncio.to_thread(
                    providers.invoke_google,
                    [HumanMessage(content=[{"type": "text", "text": prompt_text}])],
                    model_override if provider_choice == "gemini" and model_override else None,
                )
                content = str(getattr(resp, "content", resp))
                provider_used = "gemini"
                model_used = model_override or config.GOOGLE_MODEL
            except Exception:
                if provider_choice == "gemini":
                    raise
                provider_used = "openai"
                model_used = model_override or config.OPENAI_NARRATIVE_MODEL
                content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)
        else:
            provider_used = "openai"
            model_used = model_override or config.OPENAI_NARRATIVE_MODEL
            content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)

        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        with open(out, "w") as f:
            f.write(content or "")

        try:
            usage.log_usage(
                event="narrative",
                provider=provider_used,
                model=model_used,
                key_label=(providers.key_label_from_index(key_index or 0) if provider_used == "gemini" else usage.OPENAI_LABEL),
                status="success",
            )
        except Exception:
            pass

        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Scenarios Admin -----------------

@app.get("/api/scenarios")
async def api_list_scenarios():
    return list_scenarios()

@app.post("/api/scenarios/import")
async def api_import_scenarios(request: Request):
    """Replace scenarios with provided list. Body: {"scenarios": [...]}"""
    try:
        body = await request.json()
        scenarios = (body or {}).get("scenarios")
        if not isinstance(scenarios, list):
            return Response(status_code=400)
        reload_scenarios(scenarios)
        return {"status": "ok", "count": len(scenarios)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scenarios/from_video")
async def api_generate_scenarios_from_video(request: Request):
    """Generate and activate scenarios from a video URL.

    Body JSON: { "url": "https://...", "target_language": "Japanese", "max_scenes": 5, "activate": true }
    """
    body = await request.json()
    url = (body or {}).get("url")
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="missing_url")
    _validate_import_url_or_path(url)
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    _require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    ip = (request.client.host if request.client else None) or _client_ip_from_headers(headers)
    _rate_limit("import_video", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))
    attest_rights = bool((body or {}).get("attest_rights", False))
    if not attest_rights:
        raise HTTPException(status_code=400, detail="attest_rights_required")
    target_language = (body or {}).get("target_language") or "Japanese"
    max_scenes = (body or {}).get("max_scenes") or 5
    activate = bool((body or {}).get("activate", True))

    cache_key = import_cache.video_scenarios_cache_key(url, target_language=target_language, max_scenes=max_scenes)
    scenarios = import_cache.load_cached_video_scenarios(cache_key)
    cache_hit = scenarios is not None
    cache_saved = False
    try:
        usage.log_usage(
            event=("video_cache_hit" if cache_hit else "video_cache_miss"),
            provider="cache",
            model="video_scenarios",
            key_label="n/a",
            status=("hit" if cache_hit else "miss"),
        )
    except Exception:
        pass

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
        "status": "ok",
        "count": len(scenarios),
        "activated": activate,
        "cached": cache_hit,
        "cache_saved": cache_saved,
        "scenarios": scenarios,
    }
def _validate_import_url_or_path(url: str) -> None:
    """Enforce SSRF-safe URL rules for remote imports.

    For now, only allow http/https URLs to public hosts unless ALLOW_LOCAL_IMPORT_PATHS is enabled.
    """
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
    u = str(url or "").strip()
    if not u:
        return False
    lower = u.lower()
    try:
        parsed = urllib.parse.urlsplit(u)
        host = (parsed.hostname or "").lower()
    except Exception:
        host = ""

    # Known "video page" hosts where we should assume video ingest.
    video_hosts = {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "tiktok.com",
        "www.tiktok.com",
        "twitch.tv",
        "www.twitch.tv",
        "dailymotion.com",
        "www.dailymotion.com",
    }
    if host in video_hosts:
        return True

    # Common direct media extensions.
    for ext in (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac", ".m3u8"):
        if lower.split("?", 1)[0].split("#", 1)[0].endswith(ext):
            return True
    return False


@app.post("/api/import/auto")
async def api_import_auto(body: AutoImportRequest, request: Request):
    """Unified importer: takes an optional URL (default path) and optional text (extra context).

    If URL looks like video -> routes to the video pipeline.
    Otherwise -> fetches readable text from the URL and compiles it (optionally prefixed by text).
    If no URL -> compiles the provided text.
    """
    if not (body.attest_rights is True):
        raise HTTPException(status_code=400, detail="attest_rights_required")

    headers = {k.lower(): v for (k, v) in request.headers.items()}
    _require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
    ip = (request.client.host if request.client else None) or _client_ip_from_headers(headers)
    _rate_limit("import_auto", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))

    url = (body.url or "").strip()
    text = (body.text or "").strip()
    target_language = body.target_language
    max_scenes = int(body.max_scenes or 6)
    activate = bool(body.activate)

    if not url and not text:
        raise HTTPException(status_code=400, detail="missing_input")

    # Video path (default for YouTube / direct media URLs).
    if url and _seems_video_url(url):
        _validate_import_url_or_path(url)
        cache_key = import_cache.video_scenarios_cache_key(url, target_language=(target_language or "Japanese"), max_scenes=max_scenes)
        scenarios = import_cache.load_cached_video_scenarios(cache_key)
        cache_hit = scenarios is not None
        cache_saved = False

        if config.DEMO_MODE and config.DEMO_VIDEO_CACHE_ONLY and not scenarios:
            raise HTTPException(status_code=403, detail="demo_mode_cache_only")

        if not scenarios:
            try:
                scenarios = await asyncio.to_thread(generate_scenarios_from_video, url, (target_language or "Japanese"), max_scenes)
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
            "target_language": (target_language or "Japanese"),
            "activated": activate,
            "cached": cache_hit,
            "cache_saved": cache_saved,
            "scenarios": scenarios,
        }

    # Web/text path (default for arbitrary URLs with readable text).
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
            # If URL fetch didn't yield readable text, fall back to video ingest to support "video page" URLs.
            if str(ve) in {"no_text_found"}:
                cache_key = import_cache.video_scenarios_cache_key(url, target_language=(target_language or "Japanese"), max_scenes=max_scenes)
                scenarios = import_cache.load_cached_video_scenarios(cache_key)
                cache_hit = scenarios is not None
                cache_saved = False

                if config.DEMO_MODE and config.DEMO_VIDEO_CACHE_ONLY and not scenarios:
                    raise HTTPException(status_code=403, detail="demo_mode_cache_only")

                if not scenarios:
                    try:
                        scenarios = await asyncio.to_thread(generate_scenarios_from_video, url, (target_language or "Japanese"), max_scenes)
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
                    "target_language": (target_language or "Japanese"),
                    "activated": activate,
                    "cached": cache_hit,
                    "cache_saved": cache_saved,
                    "scenarios": scenarios,
                }
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

@app.get("/api/scenario-versions")
async def api_list_scenario_versions():
    return list_scenario_versions()

@app.post("/api/scenario-versions/save")
async def api_save_scenarios(request: Request):
    try:
        body = await request.json()
        label = (body or {}).get("label")
        filename = save_scenarios_version(label)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scenario-versions/activate")
async def api_activate_scenarios(request: Request):
    try:
        body = await request.json()
        filename = (body or {}).get("filename")
        if not filename or not isinstance(filename, str):
            return Response(status_code=400)
        activate_scenario_version(filename)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "8000"))
    except Exception:
        port = 8000

    def _find_free_port() -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p

    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        # Address in use, fall back to a free port
        if getattr(e, 'errno', None) in (98, 48):  # 98 Linux, 48 macOS
            alt = _find_free_port()
            print(f"Port {port} in use. Falling back to {alt}.")
            uvicorn.run(app, host=host, port=alt)
        else:
            raise
