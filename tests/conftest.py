from __future__ import annotations

import importlib
from pathlib import Path
from typing import Optional

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _DummyResponse:
    def __init__(self, content: str):
        self.content = content


@pytest.fixture(scope="session")
def _isolated_paths(tmp_path_factory) -> dict[str, Path]:
    """Create isolated filesystem roots for media generated during tests."""
    root = tmp_path_factory.mktemp("langhero-test-data")
    paths = {
        "voice": root / "voice_notes",
        "trans": root / "transcriptions",
        "narratives": root / "narratives",
        "examples": root / "examples_audio",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


@pytest.fixture(scope="session")
def app(_isolated_paths) -> FastAPI:
    """FastAPI app configured to use temporary storage directories."""
    mp = MonkeyPatch()

    def _set_paths(module_name: str, mapping: dict[str, Path]) -> None:
        module = importlib.import_module(module_name)
        for attr, path in mapping.items():
            if hasattr(module, attr):
                mp.setattr(module, attr, str(path), raising=False)

    root_dir = _isolated_paths["voice"].parent
    path_mapping = {
        "VOICE_NOTES_DIR": _isolated_paths["voice"],
        "TRANSCRIPTS_DIR": _isolated_paths["trans"],
        "NARRATIVES_DIR": _isolated_paths["narratives"],
        "EXAMPLES_DIR": _isolated_paths["examples"],
        "EXAMPLES_AUDIO_DIR": _isolated_paths["examples"],
        "PUBLISHED_RUNS_DIR": root_dir / "published_runs",
        "IMPORT_CACHE_DIR": root_dir / "import_cache",
        "USAGE_DIR": root_dir / "usage",
    }

    # Patch modules that cache directory locations at import time.
    for module_name in ["config", "services", "note_store", "main", "published_runs", "import_cache", "usage_log"]:
        _set_paths(module_name, path_mapping)

    app_module = importlib.import_module("main")
    application = app_module.app

    yield application

    mp.undo()


@pytest.fixture
def app_client(app):
    """HTTP/WebSocket client for the FastAPI app under test."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def stub_providers(monkeypatch):
    """Stub external provider calls to avoid network use in tests."""
    providers = importlib.import_module("providers")

    def fake_transcribe_audio(*args, **kwargs):
        return providers.TranscriptionResult(
            text="stub transcript",
            provider="openai",
            model="stub-model",
        )

    def fake_translate_text(text: str, to_language: Optional[str] = None, from_language: Optional[str] = None):
        return f"{text} ({to_language or 'target'})"

    def fake_romanize(text: str, target_language: Optional[str] = None):
        return f"{text} (romanized)"

    def fake_openai_chat(*args, **kwargs):
        return "stub narrative"

    def fake_invoke_google(messages, model_override=None):
        return _DummyResponse("stub response"), 0

    def fake_tts_with_openai(text: str, voice: str = "alloy", fmt: str = "mp3") -> bytes:
        return f"tts:{voice}:{fmt}:{text}".encode("utf-8")

    def fake_collect_keys():
        return ["stub-key"]

    monkeypatch.setattr(providers, "GOOGLE_KEYS", ["stub-key"], raising=False)
    monkeypatch.setattr(providers, "GOOGLE_LLMS", [], raising=False)
    monkeypatch.setattr(providers, "transcribe_audio", fake_transcribe_audio, raising=False)
    monkeypatch.setattr(providers, "translate_text", fake_translate_text, raising=False)
    monkeypatch.setattr(providers, "romanize", fake_romanize, raising=False)
    monkeypatch.setattr(providers, "openai_chat", fake_openai_chat, raising=False)
    monkeypatch.setattr(providers, "invoke_google", fake_invoke_google, raising=False)
    monkeypatch.setattr(providers, "tts_with_openai", fake_tts_with_openai, raising=False)
    monkeypatch.setattr(providers, "collect_google_api_keys", fake_collect_keys, raising=False)


@pytest.fixture(autouse=True)
def stub_url_validation(monkeypatch):
    """Disable DNS/network-dependent URL validation in tests."""
    import importlib

    url_fetch = importlib.import_module("url_fetch")

    def allow_all(_url: str):
        return None

    monkeypatch.setattr(url_fetch, "validate_public_url", allow_all, raising=True)
