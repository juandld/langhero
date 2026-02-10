"""
Security helpers for rate limiting, admin authentication, and user authorization.
"""

import time
from typing import Optional
from fastapi import HTTPException
import config
import auth


# Rate limiting state: bucket -> {ip: (minute_bucket, count)}
_RATE_STATE: dict[str, dict[str, tuple[int, int]]] = {}


def client_ip_from_headers(headers: dict) -> str:
    """Extract client IP from X-Forwarded-For header or return 'unknown'."""
    try:
        xff = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
        if isinstance(xff, str) and xff.strip():
            return xff.split(",")[0].strip()
    except Exception:
        pass
    return "unknown"


def rate_limit(bucket: str, ip: str, limit_per_min: int) -> None:
    """Enforce per-minute rate limit. Raises HTTPException(429) if exceeded."""
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


def is_admin(headers: dict) -> bool:
    """Check if request has valid admin credentials via X-Admin-Key or Bearer token."""
    key = (config.ADMIN_API_KEY or "").strip()
    if not key:
        return False

    # Accept X-Admin-Key header
    try:
        supplied = headers.get("x-admin-key") or headers.get("X-Admin-Key") or ""
        if isinstance(supplied, str) and supplied.strip() == key:
            return True
    except Exception:
        pass

    # Accept Authorization: Bearer <key>
    try:
        auth_header = headers.get("authorization") or headers.get("Authorization") or ""
        if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
            token = auth_header.split(None, 1)[1].strip()
            if token == key:
                return True
    except Exception:
        pass

    return False


def require_admin(headers: dict, *, flag: bool) -> None:
    """Require admin authentication if flag is True. Raises HTTPException on failure."""
    if not flag:
        return
    if not (config.ADMIN_API_KEY or "").strip():
        raise HTTPException(status_code=500, detail="admin_key_not_configured")
    if not is_admin(headers):
        raise HTTPException(status_code=401, detail="admin_required")


async def require_auth(headers: dict, *, payload: Optional[dict] = None, flag: bool) -> None:
    """Require user authentication if flag is True. Raises HTTPException on failure."""
    if not flag:
        return
    try:
        await auth.require_user(headers, payload=payload, required=True)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
