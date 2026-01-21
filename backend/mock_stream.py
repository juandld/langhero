from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _hash_preview(data: bytes, length: int = 12) -> str:
    """Return a deterministic preview token for a chunk."""
    if not data:
        return "empty"
    digest = hashlib.sha1(data).hexdigest()
    return digest[:length]


def _fake_transcript(seq: int, preview: str) -> str:
    """Generate a mock transcript string."""
    templates = [
        "mock phrase {seq}",
        "placeholder utterance {seq}",
        "imagined sentence {seq}",
        "practice line {seq}",
    ]
    template = templates[(seq - 1) % len(templates)]
    return f"{template.format(seq=seq)} ({preview})"


@dataclass
class MockStreamingSession:
    """Stateful helper that fabricates streaming responses."""

    scenario_id: Optional[str] = None
    language: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    sequence: int = 0
    total_bytes: int = 0
    lives_total: int = 3
    lives_remaining: int = 3
    score: int = 0
    mode: str = "advanced"

    def ready_event(self) -> Dict[str, Any]:
        return {
            "event": "ready",
            "scenario_id": self.scenario_id,
            "language": self.language,
            "mode": self.mode,
            "lives_total": self.lives_total,
            "lives_remaining": self.lives_remaining,
            "score": self.score,
            "message": "Mock streaming session ready.",
        }

    def register_chunk(self, chunk: bytes) -> Dict[str, Any]:
        self.sequence += 1
        size = len(chunk)
        self.total_bytes += size
        preview = _hash_preview(chunk)
        transcript = _fake_transcript(self.sequence, preview)
        return {
            "event": "partial",
            "seq": self.sequence,
            "bytes": size,
            "preview": preview,
            "transcript": transcript,
            "received_at": time.time(),
        }

    def final_event(self, reason: str = "client_stop") -> Dict[str, Any]:
        return {
            "event": "final",
            "total_chunks": self.sequence,
            "total_bytes": self.total_bytes,
            "duration": max(time.time() - self.started_at, 0.0),
            "reason": reason,
            "scenario_id": self.scenario_id,
            "language": self.language,
            "mode": self.mode,
            "lives_total": self.lives_total,
            "lives_remaining": self.lives_remaining,
            "score": self.score,
        }


def build_session(payload: Optional[Dict[str, Any]]) -> MockStreamingSession:
    payload = payload or {}
    scenario_id = payload.get("scenario_id") or payload.get("session_id")
    language = payload.get("language") or payload.get("lang")
    raw_mode = payload.get("mode") or "advanced"
    mode = raw_mode.strip().lower() if isinstance(raw_mode, str) and raw_mode.strip() else "advanced"
    session = MockStreamingSession(
        scenario_id=scenario_id,
        language=language,
        mode=mode,
    )
    return session
