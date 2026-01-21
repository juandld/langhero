from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


PUBLISHED_RUNS_DIR = os.path.join(os.path.dirname(__file__), "published_runs")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_dir() -> None:
    os.makedirs(PUBLISHED_RUNS_DIR, exist_ok=True)


def _safe_id(value: str) -> Optional[str]:
    raw = (value or "").strip()
    if not raw or len(raw) > 128:
        return None
    for ch in raw:
        if ch.isalnum() or ch in {"-", "_"}:
            continue
        return None
    return raw


def _run_path(public_id: str) -> str:
    safe = _safe_id(public_id)
    if not safe:
        raise ValueError("invalid_id")
    return os.path.join(PUBLISHED_RUNS_DIR, f"{safe}.json")


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublishedRun:
    public_id: str
    title: str
    target_language: str
    created_at_ms: int
    scenarios: list[dict]


def create_published_run(*, title: str, target_language: str, scenarios: list[dict]) -> tuple[PublishedRun, str]:
    _ensure_dir()
    public_id = secrets.token_urlsafe(12).replace("-", "_")
    public_id = _safe_id(public_id) or secrets.token_hex(12)
    delete_key = secrets.token_urlsafe(24)
    payload = {
        "version": 1,
        "public_id": public_id,
        "title": (title or "").strip()[:120] or "Published run",
        "target_language": (target_language or "").strip()[:40] or "",
        "created_at_ms": _now_ms(),
        "delete_key_hash": _hash_key(delete_key),
        "scenarios": scenarios,
    }
    path = _run_path(public_id)
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    run = PublishedRun(
        public_id=payload["public_id"],
        title=payload["title"],
        target_language=payload["target_language"],
        created_at_ms=payload["created_at_ms"],
        scenarios=payload["scenarios"],
    )
    return run, delete_key


def load_published_run(public_id: str) -> Optional[PublishedRun]:
    _ensure_dir()
    try:
        path = _run_path(public_id)
    except ValueError:
        return None
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list):
        return None
    return PublishedRun(
        public_id=str(data.get("public_id") or public_id),
        title=str(data.get("title") or "Published run"),
        target_language=str(data.get("target_language") or ""),
        created_at_ms=int(data.get("created_at_ms") or 0),
        scenarios=[s for s in scenarios if isinstance(s, dict)],
    )


def delete_published_run(public_id: str, delete_key: str) -> bool:
    _ensure_dir()
    try:
        path = _run_path(public_id)
    except ValueError:
        return False
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return False
    expected = str((data or {}).get("delete_key_hash") or "")
    if not expected:
        return False
    if _hash_key(delete_key or "") != expected:
        return False
    try:
        os.remove(path)
    except Exception:
        return False
    return True


def public_payload(run: PublishedRun) -> Dict[str, Any]:
    return {
        "public_id": run.public_id,
        "title": run.title,
        "target_language": run.target_language,
        "created_at_ms": run.created_at_ms,
        "scenarios": run.scenarios,
    }

