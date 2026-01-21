"""
Reusable scenario templates for tests.

Each helper returns a deep-copied dictionary so individual tests can adjust
fields without mutating shared state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

_BEGINNER_BASE: Dict[str, Any] = {
    "id": 101,
    "language": "Japanese",
    "mode": "beginner",
    "lives": 3,
    "reward_points": 12,
    "penalties": {
        "incorrect_answer": {"lives": 1},
        "language_mismatch": {"lives": 2, "points": 12},
    },
    "character_dialogue_en": "Welcome back! Ready to order?",
    "character_dialogue_jp": "いらっしゃいませ！ご注文はお決まりですか？",
    "options": [
        {
            "text": "Yes, please.",
            "style": "polite",
            "next_scenario": 201,
            "examples": [
                {
                    "native": "Yes, please.",
                    "target": "はい、お願いします。",
                    "pronunciation": "Hai, onegaishimasu.",
                }
            ],
        },
        {
            "text": "No, thank you.",
            "style": "polite",
            "next_scenario": 202,
            "examples": [
                {
                    "native": "No, thank you.",
                    "target": "いいえ、結構です。",
                    "pronunciation": "Iie, kekkou desu.",
                }
            ],
        },
    ],
}

_ADVANCED_BASE: Dict[str, Any] = {
    "id": 401,
    "language": "Japanese",
    "mode": "advanced",
    "lives": 2,
    "reward_points": 18,
    "penalties": {
        "incorrect_answer": {"lives": 2},
        "language_mismatch": {"lives": 2, "points": 18},
    },
    "character_dialogue_en": "Keep up with the kitchen rush—respond live!",
    "character_dialogue_jp": "キッチンは大忙し！すぐに返事してください！",
    "options": [
        {
            "text": "It's delicious!",
            "style": "excited",
            "next_scenario": 402,
            "examples": [
                {
                    "native": "It's delicious!",
                    "target": "とてもおいしいです！",
                    "pronunciation": "Totemo oishii desu!",
                }
            ],
        },
        {
            "text": "Could I have water?",
            "style": "polite",
            "next_scenario": 403,
            "examples": [
                {
                    "native": "Water, please.",
                    "target": "お水をいただけますか？",
                    "pronunciation": "Omizu o itadakemasu ka?",
                }
            ],
        },
    ],
}


def _build(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    scenario = deepcopy(base)
    scenario.update(overrides)
    return scenario


def beginner_scenario(**overrides: Any) -> Dict[str, Any]:
    """Return a beginner/time-stop scenario with optional overrides."""
    return _build(_BEGINNER_BASE, overrides)


def advanced_scenario(**overrides: Any) -> Dict[str, Any]:
    """Return an advanced/streaming scenario with optional overrides."""
    return _build(_ADVANCED_BASE, overrides)
