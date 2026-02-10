"""
Scenario version management endpoints.
"""

from fastapi import APIRouter, Request, Response
from services.scenarios import (
    list_scenario_versions,
    save_scenarios_version,
    activate_scenario_version,
)

router = APIRouter(prefix="/api/scenario-versions", tags=["scenario-versions"])


@router.get("")
async def api_list_scenario_versions():
    """List all saved scenario versions."""
    return list_scenario_versions()


@router.post("/save")
async def api_save_scenarios(request: Request):
    """Save current scenarios as a new version."""
    try:
        body = await request.json()
        label = (body or {}).get("label")
        filename = save_scenarios_version(label)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        return {"error": str(e)}


@router.post("/activate")
async def api_activate_scenarios(request: Request):
    """Activate a specific scenario version."""
    try:
        body = await request.json()
        filename = (body or {}).get("filename")
        if not filename or not isinstance(filename, str):
            return Response(status_code=400)
        activate_scenario_version(filename)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}
