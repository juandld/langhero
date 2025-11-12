from __future__ import annotations

import asyncio
import io
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import logging

import providers
from services import process_interaction, get_scenario_by_id

logger = logging.getLogger(__name__)


def normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    if v in {"ja", "jp", "japanese"}:
        return "japanese"
    if v in {"en", "eng", "english"}:
        return "english"
    return v or None


def detect_language_from_text(text: str) -> str:
    """Very lightweight language heuristic (Japanese vs English vs Unknown)."""
    if not text:
        return "unknown"
    jp_count = 0
    en_count = 0
    for ch in text:
        code = ord(ch)
        if "a" <= ch.lower() <= "z":
            en_count += 1
        elif (
            0x3040 <= code <= 0x30FF  # Hiragana + Katakana
            or 0x31F0 <= code <= 0x31FF  # Katakana Phonetic Extensions
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs (common Kanji)
        ):
            jp_count += 1
    if jp_count > max(en_count, 3):
        return "japanese"
    if en_count > 0 and en_count >= jp_count:
        return "english"
    return "unknown"


MIN_PARTIAL_BYTES = 12000  # avoid hitting ASR with ultra-short buffers (~0.5s)
DEFAULT_LIVES = 3
LANGUAGE_MISMATCH_SCORE_PENALTY = 10
SUCCESS_POINTS_DEFAULT = 10
AUTO_FINALIZE_MIN_INTERVAL = 0.8


def _scenario_config(scenario_id: Optional[int]) -> Dict[str, Any]:
    """Return per-scenario streaming configuration (lives, penalties, messaging)."""
    scenario = get_scenario_by_id(scenario_id) if scenario_id else None
    lives = DEFAULT_LIVES
    penalty_points = LANGUAGE_MISMATCH_SCORE_PENALTY
    penalty_message = None
    success_points = SUCCESS_POINTS_DEFAULT
    if isinstance(scenario, dict):
        raw_lives = scenario.get("lives") or scenario.get("max_lives")
        try:
            lives = max(1, int(raw_lives))
        except Exception:
            lives = DEFAULT_LIVES
        reward = scenario.get("reward_points") or scenario.get("points") or scenario.get("success_points")
        try:
            if reward is not None:
                success_points = max(0, int(reward))
        except Exception:
            success_points = SUCCESS_POINTS_DEFAULT
        penalties = scenario.get("penalties")
        if isinstance(penalties, dict):
            lang_penalty = penalties.get("language_mismatch") or penalties.get("wrong_language")
            if isinstance(lang_penalty, dict):
                try:
                    penalty_points = abs(int(lang_penalty.get("points") or penalty_points))
                except Exception:
                    penalty_points = LANGUAGE_MISMATCH_SCORE_PENALTY
                msg = lang_penalty.get("message")
                if isinstance(msg, str) and msg.strip():
                    penalty_message = msg.strip()
    return {
        "lives": lives,
        "penalty_points": penalty_points,
        "penalty_message": penalty_message,
        "success_points": success_points,
    }


async def transcribe_audio(audio_bytes: bytes, language: Optional[str] = None) -> str:
    """Run transcription in a background thread (best-effort)."""
    if len(audio_bytes) < MIN_PARTIAL_BYTES:
        return ""
    loop = asyncio.get_running_loop()

    def _call() -> str:
        try:
            lang_norm = normalize_language(language)
            lang_code = None
            if lang_norm == "japanese":
                lang_code = "ja"
            elif lang_norm == "english":
                lang_code = "en"
            return providers.transcribe_with_openai(
                audio_bytes,
                file_ext="webm",
                language=lang_code,
            )
        except Exception:
            return ""

    return await loop.run_in_executor(None, _call)


@dataclass
class StreamingSession:
    scenario_id: Optional[int]
    target_language: Optional[str]
    learner_language: Optional[str] = None
    audio_buffer: bytearray = field(default_factory=bytearray)
    chunk_seq: int = 0
    last_partial_ts: float = 0.0
    language_penalized: bool = False
    partial_task: Optional[asyncio.Task] = None
    closed: bool = False
    lives_total: int = DEFAULT_LIVES
    lives_remaining: int = DEFAULT_LIVES
    score: int = 0
    points_per_penalty: int = LANGUAGE_MISMATCH_SCORE_PENALTY
    penalty_message_template: Optional[str] = None
    points_per_success: int = SUCCESS_POINTS_DEFAULT
    final_event_sent: bool = False
    auto_finalized: bool = False
    last_auto_check: float = 0.0

    async def append_chunk(self, chunk: bytes, websocket) -> None:
        if self.closed:
            return
        self.chunk_seq += 1
        self.audio_buffer.extend(chunk)
        await self._maybe_emit_partial(websocket)

    async def apply_language_penalty(self, detected_language: str, websocket) -> None:
        if self.lives_remaining <= 0:
            return
        self.lives_remaining = max(0, self.lives_remaining - 1)
        if (
            self.target_language
            and detected_language not in {"unknown", None}
            and detected_language != self.target_language
        ):
            detail = f"Heard {detected_language}, expected {self.target_language}."
        else:
            detail = "Speech did not match the target language."
        message = self.penalty_message_template or detail
        payload = {
            "event": "penalty",
            "type": "wrong_language",
            "detected_language": detected_language,
            "target_language": self.target_language,
            "lives_delta": -1,
            "lives_remaining": self.lives_remaining,
            "lives_total": self.lives_total,
            "score": self.score,
            "message": message,
        }
        if self.lives_remaining == 0:
            payload["status"] = "exhausted"
        await websocket.send_json(payload)

    async def apply_incorrect_answer_penalty(
        self,
        websocket,
        message: Optional[str] = None,
        delta: Optional[int] = None,
    ) -> None:
        if self.lives_remaining <= 0:
            return
        lives_delta = delta if isinstance(delta, int) and delta != 0 else -1
        if lives_delta > 0:
            lives_delta = -abs(lives_delta)
        elif lives_delta == 0:
            lives_delta = -1
        self.lives_remaining = max(0, self.lives_remaining + lives_delta)
        payload: Dict[str, Any] = {
            "event": "penalty",
            "type": "incorrect_answer",
            "lives_delta": lives_delta,
            "lives_remaining": self.lives_remaining,
            "lives_total": self.lives_total,
            "score": self.score,
            "message": message or "Let's try that again.",
        }
        if self.lives_remaining == 0:
            payload["status"] = "exhausted"
        await websocket.send_json(payload)

    async def _maybe_emit_partial(self, websocket) -> None:
        now = time.time()
        if now - self.last_partial_ts < 1.0:
            return
        if self.partial_task and not self.partial_task.done():
            return
        audio_bytes = bytes(self.audio_buffer)
        if not audio_bytes:
            return
        loop = asyncio.get_running_loop()
        self.partial_task = loop.create_task(self._emit_partial(audio_bytes, websocket))

    async def _emit_partial(self, audio_bytes: bytes, websocket) -> None:
        transcript = await transcribe_audio(audio_bytes, self.target_language)
        self.last_partial_ts = time.time()
        detected = detect_language_from_text(transcript)
        payload: Dict[str, Any] = {
            "event": "partial",
            "seq": self.chunk_seq,
            "transcript": transcript,
            "detected_language": detected,
            "target_language": self.target_language,
        }
        await websocket.send_json(payload)
        # Penalise language mismatch once per mismatch window
        if (
            self.target_language
            and detected not in {"unknown", None}
            and detected != self.target_language
        ):
            if not self.language_penalized and self.lives_remaining > 0:
                self.language_penalized = True
                await self.apply_language_penalty(detected, websocket)
        else:
            # Reset when the learner comes back to the target language
            self.language_penalized = False

        await self._maybe_auto_finalize(audio_bytes, websocket)

    async def finalize(self, websocket, precomputed_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.final_event_sent:
            return precomputed_result or {"error": "already_finalized"}
        self.closed = True
        if self.partial_task:
            self.partial_task.cancel()
        audio_bytes = bytes(self.audio_buffer)

        result: Dict[str, Any]
        if precomputed_result is not None:
            result = precomputed_result
        else:
            def _call():
                if self.scenario_id is None:
                    return {"error": "missing_scenario", "heard": "", "nextScenario": None}
                audio_stream = io.BytesIO(audio_bytes)
                audio_stream.seek(0)
                return process_interaction(audio_stream, str(self.scenario_id), self.target_language)

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _call)
        if isinstance(result, dict) and not result.get("error"):
            score_delta = 0
            try:
                score_delta = int(result.get("scoreDelta") or 0)
            except Exception:
                score_delta = 0
            if score_delta <= 0:
                score_delta = self.points_per_success
            self.score += max(0, score_delta)
        else:
            lives_delta = None
            failure_message = ""
            if isinstance(result, dict):
                try:
                    lives_delta = int(result.get("livesDelta") or 0)
                except Exception:
                    lives_delta = None
                failure_message = str(result.get("message") or result.get("error") or "")
            await self.apply_incorrect_answer_penalty(
                websocket,
                message=failure_message or "Let's try that one again.",
                delta=lives_delta,
            )
        await websocket.send_json(
            {
                "event": "final",
                "result": result,
                "target_language": self.target_language,
                "score": self.score,
                "lives_remaining": self.lives_remaining,
                "lives_total": self.lives_total,
            }
        )
        self.final_event_sent = True
        return result

    async def _maybe_auto_finalize(self, audio_bytes: bytes, websocket) -> None:
        if self.closed or self.auto_finalized:
            return
        now = time.time()
        if self.last_auto_check and now - self.last_auto_check < AUTO_FINALIZE_MIN_INTERVAL:
            return
        if not audio_bytes:
            return
        self.last_auto_check = now

        def _call():
            if self.scenario_id is None:
                return {"error": "missing_scenario", "heard": "", "nextScenario": None}
            audio_stream = io.BytesIO(audio_bytes)
            audio_stream.seek(0)
            return process_interaction(audio_stream, str(self.scenario_id), self.target_language)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _call)
        if self._should_auto_finalize(result):
            self.auto_finalized = True
            logger.info(
                "Auto-finalizing streaming session scenario=%s chunk=%s",
                self.scenario_id,
                self.chunk_seq,
            )
            await self.finalize(websocket, precomputed_result=result)

    def _should_auto_finalize(self, result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("error"):
            return False
        if result.get("npcDoesNotUnderstand"):
            return False
        if result.get("repeatExpected"):
            return False
        return bool(result.get("nextScenario"))


def create_session(payload: Optional[Dict[str, Any]]) -> StreamingSession:
    payload = payload or {}
    scenario_id = payload.get("scenario_id")
    try:
        scenario_id = int(scenario_id) if scenario_id is not None else None
    except Exception:
        scenario_id = None
    target_language = normalize_language(payload.get("language"))
    learner_language = normalize_language(payload.get("learner_language"))
    config = _scenario_config(scenario_id)
    return StreamingSession(
        scenario_id=scenario_id,
        target_language=target_language,
        learner_language=learner_language,
        lives_total=config["lives"],
        lives_remaining=config["lives"],
        points_per_penalty=config["penalty_points"],
        penalty_message_template=config.get("penalty_message"),
        points_per_success=config["success_points"],
    )
