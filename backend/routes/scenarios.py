"""
Scenarios admin endpoints for managing game scenarios.
"""

import os
import asyncio
from fastapi import APIRouter, Request, Response, HTTPException
import config
import image_gen
import usage_log as usage
from security import require_admin, require_auth, rate_limit, client_ip_from_headers
from services.scenarios import (
    list_scenarios,
    reload_scenarios,
    get_scenario_by_id,
    list_scenario_versions,
    save_scenarios_version,
    activate_scenario_version,
)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("")
async def api_list_scenarios():
    """List all scenarios."""
    return list_scenarios()


@router.get("/{scenario_id}")
async def api_get_scenario(scenario_id: int):
    """Get a single scenario by ID."""
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="scenario_not_found")
    return scenario


@router.post("/{scenario_id}/generate-image")
async def generate_scenario_image(scenario_id: int, request: Request):
    """Generate an AI scene image for a scenario via DALL-E 3.

    Returns {url, cached, cache_key}.
    """
    headers = {k.lower(): v for (k, v) in request.headers.items()}
    ip = (request.client.host if request.client else None) or client_ip_from_headers(headers)
    rate_limit("image_gen", str(ip), int(getattr(config, "RATE_LIMIT_IMPORT_PER_MIN", 10)))

    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="scenario_not_found")

    try:
        body = await request.json()
    except Exception:
        body = {}

    force = bool((body or {}).get("force", False))

    try:
        result = await asyncio.to_thread(image_gen.generate_scene_image, scenario, force=force)
        try:
            usage.log_usage(
                event=("image_cache_hit" if result.get("cached") else "image_generate"),
                provider="openai",
                model="dall-e-3",
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        except Exception:
            pass
        return result
    except Exception as e:
        try:
            usage.log_usage(
                event="image_generate",
                provider="openai",
                model="dall-e-3",
                key_label=usage.OPENAI_LABEL,
                status="error",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scenario_id}/image")
async def get_scenario_image(scenario_id: int):
    """Check if a cached image exists for a scenario.

    Returns {url, exists} or {exists: false}.
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="scenario_not_found")

    cached_url = image_gen.get_cached_image(scenario)
    if cached_url:
        return {"url": cached_url, "exists": True}
    return {"exists": False}


@router.post("/import")
async def api_import_scenarios(request: Request):
    """Replace scenarios with provided list. Body: {"scenarios": [...]}"""
    try:
        headers = {k.lower(): v for (k, v) in request.headers.items()}
        require_admin(headers, flag=bool(config.REQUIRE_ADMIN_FOR_IMPORT))
        await require_auth(headers, flag=bool(config.REQUIRE_AUTH_FOR_IMPORT))
        body = await request.json()
        scenarios = (body or {}).get("scenarios")
        if not isinstance(scenarios, list):
            return Response(status_code=400)
        reload_scenarios(scenarios)
        return {"status": "ok", "count": len(scenarios)}
    except Exception as e:
        return {"error": str(e)}
