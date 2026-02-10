"""
Published runs endpoints for sharing scenario chains.
"""

from fastapi import APIRouter, Request, HTTPException
import config
import published_runs
from security import require_admin, require_auth, rate_limit, client_ip_from_headers

router = APIRouter(prefix="/api/published_runs", tags=["published"])


@router.post("")
async def publish_run(request: Request):
    """Publish a compiled scenario chain for sharing (explicit confirmation required)."""
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_PUBLISH))
    await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_PUBLISH))

    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("publish_run", str(ip), int(getattr(config, "RATE_LIMIT_PUBLISH_PER_MIN", 10)))

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


@router.get("/{public_id}")
async def get_published_run(public_id: str):
    """Get a published run by its public ID."""
    run = published_runs.load_published_run(public_id)
    if not run:
        raise HTTPException(status_code=404, detail="not_found")
    return published_runs.public_payload(run)


@router.delete("/{public_id}")
async def delete_published_run(public_id: str, request: Request):
    """Delete a published run (requires delete_key)."""
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_PUBLISH))
    await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_PUBLISH))

    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("publish_delete", str(ip), int(getattr(config, "RATE_LIMIT_PUBLISH_PER_MIN", 10)))

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
