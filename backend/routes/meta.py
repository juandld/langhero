"""
Meta and usage endpoints for dev tools and runtime flags.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter
import config
import usage_log as usage

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
async def api_meta():
    """Lightweight runtime flags for the frontend (dev/demo UX)."""
    return {
        "demo_mode": bool(config.DEMO_MODE),
        "demo_video_cache_only": bool(config.DEMO_VIDEO_CACHE_ONLY),
        "demo_allow_llm_import": bool(config.DEMO_ALLOW_LLM_IMPORT),
        "demo_disable_streaming": bool(config.DEMO_DISABLE_STREAMING),
        "utc_now": datetime.utcnow().isoformat(),
    }


@router.get("/usage/weekly")
async def api_usage_weekly(year: Optional[int] = None, week: Optional[int] = None):
    """Weekly rollup of usage events (for dev tools / cost estimation)."""
    return usage.load_weekly_summary(year=year, iso_week=week)


@router.get("/usage/recent")
async def api_usage_recent(limit: int = 200, days: int = 7):
    """Recent raw usage events (newest-first) from daily JSONL logs."""
    return {
        "limit": max(1, min(int(limit or 200), 2000)),
        "days": max(1, min(int(days or 7), 60)),
        "events": usage.load_recent_events(limit=limit, days=days),
    }
