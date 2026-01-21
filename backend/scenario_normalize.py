from __future__ import annotations

from typing import Optional

import config


def _normalize_mode(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    if raw in {"advanced", "live", "streaming"}:
        return "advanced"
    if raw in {"beginner", "time-stop", "timestop", "planning"}:
        return "beginner"
    return None


def normalize_scenarios(scenarios: list[dict], *, ensure_advanced: bool = True) -> list[dict]:
    """Normalize scenario metadata required by HUD/streaming.

    - Ensures each scenario has mode/lives/reward_points/penalties.
    - Ensures at least one advanced scene (scene 2 by default) when requested.

    Returns the same list for convenience (mutates dicts in-place).
    """
    if not isinstance(scenarios, list):
        return []
    dicts: list[dict] = [s for s in scenarios if isinstance(s, dict)]
    if not dicts:
        return []

    has_advanced = any(_normalize_mode(s.get("mode")) == "advanced" for s in dicts)
    if has_advanced:
        ensure_advanced = False

    for idx, scenario in enumerate(dicts):
        mode = _normalize_mode(scenario.get("mode"))
        if mode is None:
            if idx == 0:
                mode = "beginner"
            elif ensure_advanced and idx == 1:
                mode = "advanced"
            else:
                mode = "beginner"
        scenario["mode"] = mode

        raw_lives = scenario.get("lives") or scenario.get("max_lives")
        try:
            lives = int(raw_lives)
        except Exception:
            lives = 0
        if lives <= 0:
            scenario["lives"] = 3 if mode == "beginner" else 2

        raw_reward = scenario.get("reward_points") or scenario.get("points") or scenario.get("success_points")
        try:
            reward = int(raw_reward)
        except Exception:
            reward = 0
        if reward <= 0:
            scenario["reward_points"] = config.DEFAULT_SUCCESS_POINTS if mode == "beginner" else config.DEFAULT_SUCCESS_POINTS + 5

        penalties = scenario.get("penalties")
        if not isinstance(penalties, dict):
            scenario["penalties"] = {
                "incorrect_answer": {"lives": config.DEFAULT_FAILURE_LIFE_COST},
                "language_mismatch": {"lives": config.DEFAULT_FAILURE_LIFE_COST},
            }

    return scenarios

