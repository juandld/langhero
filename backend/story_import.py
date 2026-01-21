from __future__ import annotations

from typing import Optional

import config
from language import infer_target_language, normalize_target_language
from scenario_normalize import normalize_scenarios
from services import generate_scenarios_from_transcript


def fallback_scenarios_from_text(
    text: str,
    target_language: str,
    max_scenes: int = 6,
) -> list[dict]:
    """Deterministic, no-network scenario builder used when LLM generation is unavailable."""
    cleaned = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    seed = cleaned[0] if cleaned else (text or "").strip()
    if not seed:
        seed = "A stranger approaches you."
    lang = normalize_target_language(target_language)
    n = max(1, min(int(max_scenes or 6), 12))
    scenarios: list[dict] = []
    for idx in range(1, n + 1):
        line = cleaned[idx - 1] if idx - 1 < len(cleaned) else seed
        scenarios.append(
            {
                "id": idx,
                "language": lang,
                "mode": "beginner" if idx == 1 else ("advanced" if idx == 2 else "beginner"),
                "lives": 3 if idx == 1 else 2,
                "reward_points": 10 if idx == 1 else 15,
                "description": "What do you say?",
                "character_dialogue_en": line,
                "character_dialogue_jp": "",
                "options": [
                    {
                        "text": "Yes",
                        "next_scenario": idx + 1 if idx < n else None,
                        "keywords": ["yes", "yeah", "sure"],
                        "examples": [{"native": "Yes.", "target": "Yes.", "pronunciation": ""}],
                    },
                    {
                        "text": "No",
                        "next_scenario": idx + 1 if idx < n else None,
                        "keywords": ["no", "nope", "nah"],
                        "examples": [{"native": "No.", "target": "No.", "pronunciation": ""}],
                    },
                ]
                if idx < n
                else [],
            }
        )
    if lang.lower() == "japanese":
        # Populate a minimal JP line in the first scene so UI heuristics can pick it up even without explicit override.
        scenarios[0]["character_dialogue_jp"] = "時間を止めてもいい。どうする？"
    return scenarios


def build_imported_scenarios(
    *,
    text: str,
    setting: Optional[str] = None,
    target_language: Optional[str] = None,
    max_scenes: int = 6,
) -> tuple[list[dict], str]:
    """Return (scenarios, target_language_display)."""
    max_scenes = max(1, min(int(max_scenes or 6), 12))
    if target_language and str(target_language).strip():
        resolved_language = normalize_target_language(target_language)
    else:
        resolved_language = infer_target_language(setting=setting, text=text)

    scenarios: list[dict] = []
    if not (config.DEMO_MODE and not config.DEMO_ALLOW_LLM_IMPORT):
        scenarios = generate_scenarios_from_transcript(
            text,
            target_language=resolved_language,
            max_scenes=max_scenes,
            usage_event="story_compile",
        ) or []
    if not scenarios:
        scenarios = fallback_scenarios_from_text(text, target_language=resolved_language, max_scenes=max_scenes)
    for s in scenarios:
        if isinstance(s, dict) and not s.get("language"):
            s["language"] = resolved_language
    dict_scenarios = [s for s in scenarios if isinstance(s, dict)]
    if dict_scenarios:
        normalize_scenarios(dict_scenarios, ensure_advanced=True)
    return scenarios, resolved_language
