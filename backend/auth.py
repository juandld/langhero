"""
Appwrite auth helpers.

We treat Appwrite JWTs as opaque and validate them by calling Appwrite's
account endpoint. This keeps the backend stateless and avoids signing keys.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import httpx

import config


def _appwrite_base() -> str:
    base = (config.APPWRITE_ENDPOINT or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


def _extract_bearer(headers: Dict[str, str]) -> str:
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth.split(None, 1)[1].strip()
    return ""


def extract_appwrite_jwt(headers: Dict[str, str], payload: Optional[Dict[str, Any]] = None) -> str:
    token = _extract_bearer(headers)
    if token:
        return token
    try:
        raw = headers.get("x-appwrite-jwt") or headers.get("X-Appwrite-JWT") or ""
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    except Exception:
        pass
    if payload and isinstance(payload, dict):
        raw = payload.get("auth_token") or payload.get("authToken") or ""
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


async def verify_appwrite_jwt(token: str) -> Dict[str, Any]:
    if not token:
        raise PermissionError("auth_required")
    base = _appwrite_base()
    project = (config.APPWRITE_PROJECT_ID or "").strip()
    if not base or not project:
        raise RuntimeError("appwrite_not_configured")
    url = f"{base}/account"
    headers = {
        "X-Appwrite-Project": project,
        "X-Appwrite-JWT": token,
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code in (401, 403):
        raise PermissionError("invalid_token")
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise PermissionError("invalid_token")
    return data


async def require_user(
    headers: Dict[str, str],
    *,
    payload: Optional[Dict[str, Any]] = None,
    required: bool = False,
) -> Optional[Dict[str, Any]]:
    token = extract_appwrite_jwt(headers, payload)
    if not token:
        if required:
            raise PermissionError("auth_required")
        return None
    return await verify_appwrite_jwt(token)
