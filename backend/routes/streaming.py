"""
WebSocket streaming endpoints for real-time game interactions.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import config
import auth
from security import is_admin, rate_limit, client_ip_from_headers
from mock_stream import build_session, MockStreamingSession
from streaming import create_session, StreamingSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])


@router.websocket("/stream/mock")
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
                    await websocket.send_json({
                        "event": "info",
                        "message": text,
                    })
            elif msg_type == "websocket.disconnect":
                reason = "disconnect"
                break
    except WebSocketDisconnect:
        reason = "disconnect"

    await websocket.send_json(session.final_event(reason=reason))
    await websocket.close()


@router.websocket("/stream/interaction")
async def interaction_stream_endpoint(websocket: WebSocket):
    """Real streaming endpoint: emits partial transcripts, penalties, and final results."""
    if config.DEMO_MODE and config.DEMO_DISABLE_STREAMING:
        await websocket.accept()
        await websocket.send_json({"event": "error", "error": "demo_mode_streaming_disabled"})
        await websocket.close()
        return

    headers = {k.lower(): v for (k, v) in websocket.headers.items()}

    # Admin check if required
    if bool(config.REQUIRE_ADMIN_FOR_STREAM):
        if not (config.ADMIN_API_KEY or "").strip():
            await websocket.accept()
            await websocket.send_json({"event": "error", "error": "admin_key_not_configured"})
            await websocket.close()
            return
        if not is_admin(headers):
            await websocket.accept()
            await websocket.send_json({"event": "error", "error": "admin_required"})
            await websocket.close()
            return

    # Rate limiting
    try:
        ip = (websocket.client.host if websocket.client else None) or client_ip_from_headers(headers)
        rate_limit("stream_connect", str(ip), int(getattr(config, "RATE_LIMIT_STREAM_CONN_PER_MIN", 30)))
    except Exception as he:
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
    init_payload: Optional[dict] = None
    if msg_type == "websocket.receive":
        text_payload = first_message.get("text")
        bytes_payload = first_message.get("bytes")
        if text_payload is not None:
            try:
                payload = json.loads(text_payload)
                if isinstance(payload, dict):
                    init_payload = payload
                    session = create_session(payload)
            except json.JSONDecodeError:
                pass
        elif bytes_payload is not None:
            pending_chunk = bytes_payload
    elif msg_type == "websocket.disconnect":
        return

    # Auth check if required
    if bool(config.REQUIRE_AUTH_FOR_STREAM):
        try:
            await auth.require_user(headers, payload=init_payload, required=True)
        except PermissionError as exc:
            await websocket.send_json({"event": "error", "error": str(exc)})
            await websocket.close()
            return
        except RuntimeError as exc:
            await websocket.send_json({"event": "error", "error": str(exc)})
            await websocket.close()
            return

    await websocket.send_json({
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
    })

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
                        logger.info("[%s] STOP signal received (%r), final_event_sent=%s auto_finalized=%s",
                                     session.session_tag, text, session.final_event_sent, session.auto_finalized)
                        await session.finalize(websocket)
                        break
                    elif text in {"reset"}:
                        session = create_session({
                            "scenario_id": session.scenario_id,
                            "language": session.target_language,
                            "learner_language": session.learner_language,
                            "judge": getattr(session, "judge_story_weight", 0.0),
                        })
                        await websocket.send_json({
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
                        })
                    else:
                        await websocket.send_json({"event": "info", "message": text})
            elif msg_type == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
