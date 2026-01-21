from __future__ import annotations

from pathlib import Path

import config
import providers


def test_api_tts_requires_text(app_client):
    res = app_client.post("/api/tts", json={})
    assert res.status_code == 400


def test_api_tts_creates_and_reuses_clip(app_client, monkeypatch):
    calls: list[tuple[str, str, str]] = []

    def counting_tts(text: str, voice: str = "alloy", fmt: str = "mp3") -> bytes:
        calls.append((text, voice, fmt))
        return f"audio:{len(calls)}:{voice}:{fmt}:{text}".encode("utf-8")

    monkeypatch.setattr(providers, "tts_with_openai", counting_tts, raising=False)

    payload = {"text": "はい、お願いします。", "language": "Japanese"}

    first = app_client.post("/api/tts", json=payload)
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["clip_id"].startswith("clip_")
    assert first_payload["url"].startswith("/examples/")
    file_path = Path(config.EXAMPLES_AUDIO_DIR) / first_payload["file"]
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"audio:1:")

    second = app_client.post("/api/tts", json=payload)
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["clip_id"] == first_payload["clip_id"]
    assert len(calls) == 1

