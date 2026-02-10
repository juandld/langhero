from __future__ import annotations

import asyncio
import hashlib
import io
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import logging

import providers
import config
from language import detect_language_from_text, normalize_language_token
from services import process_interaction, get_scenario_by_id

_session_counter = 0

logger = logging.getLogger(__name__)


def clamp_float(value: object, default: float = 0.0, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = float(default)
    if v < lo:
        return float(lo)
    if v > hi:
        return float(hi)
    return float(v)


MIN_PARTIAL_BYTES = 4000  # lower threshold allows quicker partial turns (~0.15s chunks)
DEFAULT_LIVES = 3
DEFAULT_PENALTY_LIVES = 1
LANGUAGE_MISMATCH_SCORE_PENALTY = 10
SUCCESS_POINTS_DEFAULT = 10
AUTO_FINALIZE_MIN_INTERVAL = 0.8


def _quick_translate(text: str, source: str = "Japanese", target: str = "English") -> str:
    """Translate a short phrase using OpenAI. Best-effort, returns empty on failure."""
    if not text or not text.strip():
        return ""
    try:
        import config as cfg
        if not cfg.OPENAI_API_KEY:
            return ""
        from openai import OpenAI
        client = OpenAI(api_key=cfg.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Translate this {source} text to literal {target}. Reply with ONLY the translation, nothing else. If the input is gibberish, translate it as literally as possible — the humor matters."},
                {"role": "user", "content": text},
            ],
            max_tokens=60,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.debug("Quick translate failed: %s", e)
        return ""


def _vocab_match_level(transcript: str, expected: str) -> float:
    """Calculate match level between transcript and expected phrase."""
    import re

    def normalize(s: str) -> str:
        s = re.sub(r'[^\w\s]', '', s.lower().strip())
        return ''.join(s.split())

    norm_transcript = normalize(transcript)
    norm_expected = normalize(expected)

    if not norm_transcript or not norm_expected:
        return 0.0
    if norm_transcript == norm_expected:
        return 1.0
    if norm_expected in norm_transcript or norm_transcript in norm_expected:
        return min(len(norm_transcript), len(norm_expected)) / max(len(norm_transcript), len(norm_expected))
    common = sum(1 for c in norm_expected if c in norm_transcript)
    return common / max(len(norm_expected), 1)


def compare_vocab_response(transcript: str, expected: str, tag: str = "", target_language: str = "japanese") -> Dict[str, Any]:
    """Compare a transcript to an expected vocab phrase."""
    if not transcript or not transcript.strip():
        logger.info("[%s] compare_vocab_response: no speech detected", tag)
        return {
            "error": "no_speech_detected",
            "heard": transcript,
            "expected": expected,
            "match_level": 0.0,
            "score": 0,
            "tier": "fail",
            "detected_language": "unknown",
        }

    match_level = _vocab_match_level(transcript, expected)
    detected = detect_language_from_text(transcript)
    tier = compute_outcome_tier(match_level, transcript, target_language)
    success = tier in ("perfect", "good")
    logger.info("[%s] compare_vocab: heard=%r expected=%r match=%.3f tier=%s detected=%s", tag, transcript[:80], expected[:80], match_level, tier, detected)
    heard_translation = "" if success else _quick_translate(transcript)

    return {
        "heard": transcript,
        "heard_translation": heard_translation,
        "expected": expected,
        "match_level": match_level,
        "score": int(match_level * 100),
        "nextScenario": True if tier in ("perfect", "good", "passable") else None,
        "success": success,
        "tier": tier,
        "detected_language": detected,
    }


def compare_vocab_multi(transcript: str, expected_list: list, tag: str = "", target_language: str = "japanese") -> Dict[str, Any]:
    """Compare a transcript against multiple expected phrases, return best match."""
    if not transcript or not transcript.strip():
        logger.info("[%s] compare_vocab_multi: no speech detected", tag)
        return {
            "error": "no_speech_detected",
            "heard": transcript,
            "expected": expected_list[0] if expected_list else "",
            "match_level": 0.0,
            "score": 0,
            "matched_index": -1,
            "tier": "fail",
            "detected_language": "unknown",
        }

    best_level = 0.0
    best_index = 0
    scores = []
    for i, expected in enumerate(expected_list):
        level = _vocab_match_level(transcript, expected)
        scores.append((i, level, expected))
        if level > best_level:
            best_level = level
            best_index = i

    logger.info("[%s] compare_vocab_multi: heard=%r | scores=%s", tag, transcript[:80],
                " | ".join(f"[{i}] {lvl:.3f} {exp[:30]}" for i, lvl, exp in scores))

    detected = detect_language_from_text(transcript)
    tier = compute_outcome_tier(best_level, transcript, target_language)
    success = tier in ("perfect", "good")
    logger.info("[%s] compare_vocab_multi: best_index=%d best_level=%.3f tier=%s detected=%s", tag, best_index, best_level, tier, detected)

    heard_translation = "" if success else _quick_translate(transcript)
    return {
        "heard": transcript,
        "heard_translation": heard_translation,
        "expected": expected_list[best_index],
        "match_level": best_level,
        "score": int(best_level * 100),
        "nextScenario": True if tier in ("perfect", "good", "passable") else None,
        "success": success,
        "matched_index": best_index,
        "tier": tier,
        "detected_language": detected,
    }


def compute_outcome_tier(match_level: float, transcript: str, target_language: str) -> str:
    """Compute outcome tier from match level and detected language.

    Returns: 'perfect', 'good', 'passable', 'fumble', or 'fail'
    """
    if not transcript or not transcript.strip():
        return "fail"

    detected = detect_language_from_text(transcript)
    correct_lang = (detected == target_language) or detected == "unknown"

    if match_level >= 0.9:
        return "perfect"
    if match_level >= 0.7:
        return "good"
    if match_level >= 0.35 and correct_lang:
        return "passable"
    if correct_lang:
        return "fumble"
    return "fail"


def _scenario_config(scenario_id: Optional[int]) -> Dict[str, Any]:
    """Return per-scenario streaming configuration (lives, penalties, messaging)."""
    scenario = get_scenario_by_id(scenario_id) if scenario_id else None
    lives = DEFAULT_LIVES
    penalty_points = LANGUAGE_MISMATCH_SCORE_PENALTY
    penalty_message = None
    success_points = SUCCESS_POINTS_DEFAULT
    language_penalty_lives = DEFAULT_PENALTY_LIVES
    incorrect_penalty_lives = DEFAULT_PENALTY_LIVES
    mode = "beginner"
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
        raw_mode = scenario.get("mode")
        if isinstance(raw_mode, str) and raw_mode.strip():
            mode = raw_mode.strip().lower()
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
                try:
                    lives_val = int(lang_penalty.get("lives") or lang_penalty.get("life") or lang_penalty.get("count") or DEFAULT_PENALTY_LIVES)
                    language_penalty_lives = max(1, abs(lives_val))
                except Exception:
                    language_penalty_lives = DEFAULT_PENALTY_LIVES
            incorrect_penalty = penalties.get("incorrect_answer")
            if isinstance(incorrect_penalty, dict):
                try:
                    lives_val = int(
                        incorrect_penalty.get("lives")
                        or incorrect_penalty.get("life")
                        or incorrect_penalty.get("count")
                        or DEFAULT_PENALTY_LIVES
                    )
                    incorrect_penalty_lives = max(1, abs(lives_val))
                except Exception:
                    incorrect_penalty_lives = DEFAULT_PENALTY_LIVES
    return {
        "lives": lives,
        "penalty_points": penalty_points,
        "penalty_message": penalty_message,
        "success_points": success_points,
        "language_penalty_lives": language_penalty_lives,
        "incorrect_penalty_lives": incorrect_penalty_lives,
        "mode": mode,
    }


async def transcribe_audio(audio_bytes: bytes, language: Optional[str] = None) -> str:
    """Run transcription in a background thread (best-effort)."""
    if len(audio_bytes) < MIN_PARTIAL_BYTES:
        return ""
    loop = asyncio.get_running_loop()

    def _call() -> str:
        try:
            start = time.perf_counter()
            result = providers.transcribe_audio(
                audio_bytes,
                file_ext="webm",
                mime_type="audio/webm",
                language_hint=language,
                context=providers.CONTEXT_STREAMING,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            print(f"[streaming/{result.provider}] Partial transcript len={len(audio_bytes)} bytes took {duration_ms}ms")
            return result.text
        except Exception:
            return ""

    return await loop.run_in_executor(None, _call)


@dataclass
class StreamingSession:
    scenario_id: Optional[int]
    target_language: Optional[str]
    learner_language: Optional[str] = None
    expected_response: Optional[str] = None  # Direct phrase for vocab mode
    expected_responses: Optional[list] = None  # Multiple phrases for free-speak mode
    mode: str = "beginner"
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
    language_penalty_lives: int = DEFAULT_PENALTY_LIVES
    incorrect_penalty_lives: int = DEFAULT_PENALTY_LIVES
    final_event_sent: bool = False
    auto_finalized: bool = False
    last_auto_check: float = 0.0
    judge_story_weight: float = 0.0
    session_tag: str = ""
    _audio_hash: str = ""
    _transcript_cache_hash: str = ""  # hash of audio when last transcription was done
    _transcript_cache_text: str = ""  # cached transcription result

    def __post_init__(self):
        global _session_counter
        _session_counter += 1
        self.session_tag = f"S{_session_counter}"
        logger.info("[%s] Session created: scenario=%s lang=%s expected_response=%s expected_responses=%s mode=%s",
                     self.session_tag, self.scenario_id, self.target_language,
                     bool(self.expected_response), len(self.expected_responses or []), self.mode)

    async def append_chunk(self, chunk: bytes, websocket) -> None:
        if self.closed:
            return
        self.chunk_seq += 1
        self.audio_buffer.extend(chunk)
        # Compute hash of full buffer for detecting identical audio
        self._audio_hash = hashlib.md5(self.audio_buffer).hexdigest()[:8]
        logger.info("[%s] chunk #%d: +%d bytes, buffer=%d bytes, hash=%s",
                     self.session_tag, self.chunk_seq, len(chunk), len(self.audio_buffer), self._audio_hash)
        try:
            max_buf = int(getattr(config, "STREAM_MAX_BUFFER_BYTES", 2_000_000) or 2_000_000)
        except Exception:
            max_buf = 2_000_000
        if max_buf > 0 and len(self.audio_buffer) > max_buf:
            # Keep the most recent audio; prevents unbounded memory growth.
            self.audio_buffer = self.audio_buffer[-max_buf:]
        await self._maybe_emit_partial(websocket)

    async def apply_language_penalty(self, detected_language: str, websocket) -> None:
        if self.lives_remaining <= 0:
            return
        lives_delta = -max(1, int(self.language_penalty_lives or DEFAULT_PENALTY_LIVES))
        self.lives_remaining = max(0, self.lives_remaining + lives_delta)
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
            "lives_delta": lives_delta,
            "lives_remaining": self.lives_remaining,
            "lives_total": self.lives_total,
            "score": self.score,
            "message": message,
            "mode": self.mode,
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
        default_penalty = max(1, int(self.incorrect_penalty_lives or DEFAULT_PENALTY_LIVES))
        lives_delta = delta if isinstance(delta, int) and delta != 0 else -default_penalty
        if lives_delta > 0:
            lives_delta = -abs(lives_delta)
        elif lives_delta == 0:
            lives_delta = -default_penalty
        self.lives_remaining = max(0, self.lives_remaining + lives_delta)
        payload: Dict[str, Any] = {
            "event": "penalty",
            "type": "incorrect_answer",
            "lives_delta": lives_delta,
            "lives_remaining": self.lives_remaining,
            "lives_total": self.lives_total,
            "score": self.score,
            "message": message or "Let's try that again.",
            "mode": self.mode,
        }
        if self.lives_remaining == 0:
            payload["status"] = "exhausted"
        await websocket.send_json(payload)

    async def _maybe_emit_partial(self, websocket) -> None:
        now = time.time()
        if now - self.last_partial_ts < 0.4:
            return
        if self.partial_task and not self.partial_task.done():
            return
        audio_bytes = bytes(self.audio_buffer)
        if not audio_bytes:
            return
        loop = asyncio.get_running_loop()
        self.partial_task = loop.create_task(self._emit_partial(audio_bytes, websocket))

    async def _emit_partial(self, audio_bytes: bytes, websocket) -> None:
        logger.info("[%s] PARTIAL transcribing %d bytes...", self.session_tag, len(audio_bytes))
        t0 = time.perf_counter()
        transcript = await transcribe_audio(audio_bytes, self.target_language)
        elapsed = int((time.perf_counter() - t0) * 1000)
        self.last_partial_ts = time.time()
        # Cache transcript so auto-finalize/finalize can reuse if audio unchanged
        partial_hash = hashlib.md5(audio_bytes).hexdigest()[:8]
        self._transcript_cache_hash = partial_hash
        self._transcript_cache_text = transcript
        detected = detect_language_from_text(transcript)
        logger.info("[%s] PARTIAL result (%dms): %r detected=%s hash=%s", self.session_tag, elapsed, (transcript or "")[:100], detected, partial_hash)
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
            self.judge_story_weight < 0.66
            and self.target_language
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
            logger.warning("[%s] FINALIZE skipped — already sent final event (auto_finalized=%s)", self.session_tag, self.auto_finalized)
            return precomputed_result or {"error": "already_finalized"}
        self.closed = True
        if self.partial_task:
            self.partial_task.cancel()
        audio_bytes = bytes(self.audio_buffer)
        audio_hash = hashlib.md5(audio_bytes).hexdigest()[:8]
        logger.info("[%s] FINALIZE start: precomputed=%s auto_finalized=%s buffer=%d bytes hash=%s",
                     self.session_tag, precomputed_result is not None, self.auto_finalized, len(audio_bytes), audio_hash)

        result: Dict[str, Any]
        if precomputed_result is not None:
            logger.info("[%s] FINALIZE using precomputed result: heard=%r match=%.3f success=%s",
                         self.session_tag, (precomputed_result.get("heard") or "")[:80],
                         precomputed_result.get("match_level", 0), precomputed_result.get("success"))
            result = precomputed_result
        else:
            tag = self.session_tag

            # Check transcript cache before spawning executor
            cached_transcript = None
            if self._transcript_cache_hash == audio_hash and self._transcript_cache_text:
                cached_transcript = self._transcript_cache_text
                logger.info("[%s] FINALIZE reusing cached transcript (hash=%s): %r",
                             tag, audio_hash, cached_transcript[:100])

            def _call():
                # Vocab mode: direct phrase comparison
                if (self.expected_response or self.expected_responses) and self.scenario_id is None:
                    # Reuse cached transcript if audio hasn't changed
                    if cached_transcript is not None:
                        transcript = cached_transcript
                    else:
                        try:
                            logger.info("[%s] FINALIZE transcribing %d bytes (vocab mode)...", tag, len(audio_bytes))
                            t0 = time.perf_counter()
                            transcript_result = providers.transcribe_audio(
                                audio_bytes,
                                file_ext="webm",
                                mime_type="audio/webm",
                                language_hint=self.target_language,
                                context=providers.CONTEXT_STREAMING,
                            )
                            transcript = transcript_result.text
                            elapsed = int((time.perf_counter() - t0) * 1000)
                            logger.info("[%s] FINALIZE transcription (%dms, provider=%s): %r",
                                         tag, elapsed, transcript_result.provider, (transcript or "")[:100])
                        except Exception as e:
                            logger.error("[%s] FINALIZE vocab transcription failed: %s", tag, e)
                            return {"error": "transcription_failed", "heard": "", "match_level": 0}
                    if self.expected_response:
                        return compare_vocab_response(transcript, self.expected_response, tag=tag, target_language=self.target_language or "japanese")
                    return compare_vocab_multi(transcript, self.expected_responses, tag=tag, target_language=self.target_language or "japanese")

                # Scenario mode: use process_interaction
                if self.scenario_id is None:
                    return {"error": "missing_scenario", "heard": "", "nextScenario": None}
                audio_stream = io.BytesIO(audio_bytes)
                audio_stream.seek(0)
                return process_interaction(
                    audio_stream,
                    str(self.scenario_id),
                    self.target_language,
                    judge=self.judge_story_weight,
                )

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _call)
        tier = result.get("tier", "fail") if isinstance(result, dict) else "fail"
        if tier in ("perfect", "good", "passable"):
            score_delta = 0
            if tier == "passable":
                score_delta = max(1, int(result.get("score", 0) * 0.5))
            else:
                score_delta = int(result.get("score", 0)) or self.points_per_success
            self.score += max(0, score_delta)
            # No life penalty for these tiers
        elif tier == "fumble":
            pass  # No points, no life cost
        else:  # "fail"
            lives_delta = None
            failure_message = ""
            if isinstance(result, dict):
                try:
                    lives_delta = int(result.get("livesDelta") or 0) or None
                except Exception:
                    lives_delta = None
                failure_message = str(result.get("message") or result.get("error") or "")
            await self.apply_incorrect_answer_penalty(
                websocket,
                message=failure_message or "Let's try that one again.",
                delta=lives_delta,
            )
        logger.info("[%s] FINALIZE sending final event: heard=%r match=%.3f success=%s score=%d lives=%d/%d",
                     self.session_tag, (result.get("heard") or "")[:80],
                     result.get("match_level", 0), result.get("success"),
                     self.score, self.lives_remaining, self.lives_total)
        await websocket.send_json(
            {
                "event": "final",
                "result": result,
                "target_language": self.target_language,
                "mode": self.mode,
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
        tag = self.session_tag

        audio_hash = hashlib.md5(audio_bytes).hexdigest()[:8]
        logger.info("[%s] AUTO-FINALIZE check: %d bytes hash=%s...", tag, len(audio_bytes), audio_hash)

        # Reuse cached transcript if audio hasn't changed since partial emit
        cached_transcript = None
        if self._transcript_cache_hash == audio_hash and self._transcript_cache_text:
            cached_transcript = self._transcript_cache_text
            logger.info("[%s] AUTO-FINALIZE reusing cached transcript (hash=%s): %r", tag, audio_hash, cached_transcript[:100])

        def _call():
            # Vocab mode: direct phrase comparison
            if (self.expected_response or self.expected_responses) and self.scenario_id is None:
                if cached_transcript is not None:
                    transcript = cached_transcript
                else:
                    try:
                        t0 = time.perf_counter()
                        transcript_result = providers.transcribe_audio(
                            audio_bytes,
                            file_ext="webm",
                            mime_type="audio/webm",
                            language_hint=self.target_language,
                            context=providers.CONTEXT_STREAMING,
                        )
                        transcript = transcript_result.text
                        elapsed = int((time.perf_counter() - t0) * 1000)
                        logger.info("[%s] AUTO-FINALIZE transcription (%dms, provider=%s): %r",
                                     tag, elapsed, transcript_result.provider, (transcript or "")[:100])
                    except Exception as e:
                        logger.error("[%s] AUTO-FINALIZE transcription failed: %s", tag, e)
                        return {"error": "transcription_failed", "heard": "", "match_level": 0}
                # Cache for finalize
                self._transcript_cache_hash = audio_hash
                self._transcript_cache_text = transcript
                if self.expected_response:
                    return compare_vocab_response(transcript, self.expected_response, tag=f"{tag}/auto", target_language=self.target_language or "japanese")
                return compare_vocab_multi(transcript, self.expected_responses, tag=f"{tag}/auto", target_language=self.target_language or "japanese")

            # Scenario mode
            if self.scenario_id is None:
                return {"error": "missing_scenario", "heard": "", "nextScenario": None}
            audio_stream = io.BytesIO(audio_bytes)
            audio_stream.seek(0)
            return process_interaction(
                audio_stream,
                str(self.scenario_id),
                self.target_language,
                judge=self.judge_story_weight,
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _call)
        should = self._should_auto_finalize(result)
        logger.info("[%s] AUTO-FINALIZE decision: should=%s heard=%r match=%.3f success=%s",
                     tag, should, (result.get("heard") or "")[:80],
                     result.get("match_level", 0), result.get("success"))
        if should:
            self.auto_finalized = True
            logger.info("[%s] AUTO-FINALIZE triggering finalize (preempting stop signal)", tag)
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
        tier = result.get("tier")
        if tier in ("perfect", "good", "passable"):
            return True
        return bool(result.get("nextScenario"))


def create_session(payload: Optional[Dict[str, Any]]) -> StreamingSession:
    payload = payload or {}
    scenario_id = payload.get("scenario_id")
    try:
        scenario_id = int(scenario_id) if scenario_id is not None else None
    except Exception:
        scenario_id = None

    # Vocab mode: direct expected_response for phrase comparison
    expected_response = payload.get("expected_response")
    if isinstance(expected_response, str) and expected_response.strip():
        expected_response = expected_response.strip()
    else:
        expected_response = None

    # Free-speak mode: multiple expected responses
    expected_responses = payload.get("expected_responses")
    if isinstance(expected_responses, list) and len(expected_responses) > 0:
        expected_responses = [s.strip() for s in expected_responses if isinstance(s, str) and s.strip()]
        if not expected_responses:
            expected_responses = None
    else:
        expected_responses = None

    target_language = normalize_language_token(payload.get("language"))
    learner_language = normalize_language_token(payload.get("learner_language"))
    judge_story_weight = clamp_float(payload.get("judge") or payload.get("judge_story") or payload.get("judge_story_weight"), default=0.0)
    config = _scenario_config(scenario_id)
    session = StreamingSession(
        scenario_id=scenario_id,
        target_language=target_language,
        learner_language=learner_language,
        expected_response=expected_response,
        expected_responses=expected_responses,
        mode=config["mode"],
        lives_total=config["lives"],
        lives_remaining=config["lives"],
        points_per_penalty=config["penalty_points"],
        penalty_message_template=config.get("penalty_message"),
        points_per_success=config["success_points"],
        language_penalty_lives=config["language_penalty_lives"],
        incorrect_penalty_lives=config["incorrect_penalty_lives"],
        judge_story_weight=judge_story_weight,
    )

    # Optional client-provided run state (local single-player convenience).
    try:
        raw_score = payload.get("score")
        if raw_score is not None and str(raw_score).strip() != "":
            session.score = max(0, int(raw_score))
    except Exception:
        pass
    try:
        raw_remaining = payload.get("lives_remaining") if "lives_remaining" in payload else payload.get("livesRemaining")
        if raw_remaining is not None and str(raw_remaining).strip() != "":
            session.lives_remaining = max(0, min(session.lives_total, int(raw_remaining)))
    except Exception:
        pass
    return session
