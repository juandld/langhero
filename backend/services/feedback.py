"""
Social feedback generation for NPC reactions.
"""
from __future__ import annotations

import random
from typing import Optional

POSITIVE_FEEDBACK = [
    "They nod approvingly",
    "That seemed to land well",
    "You notice a slight smile",
    "They look pleased",
    "A warm nod of acknowledgment",
]

NEUTRAL_FEEDBACK = [
    "They consider your words",
    "A thoughtful pause follows",
    "They seem to be processing",
    "An attentive look crosses their face",
]

NEGATIVE_FEEDBACK = [
    "They look a bit confused",
    "That didn't quite land",
    "An awkward pause follows",
    "They seem uncertain",
    "A puzzled expression appears",
]

WRONG_LANGUAGE_FEEDBACK = [
    "They tilt their head, not understanding",
    "A look of confusion crosses their face",
    "They seem to be waiting for Japanese",
    "That language didn't register",
]


def generate_social_feedback(success: bool, match_type: str, style: Optional[str] = None) -> dict:
    """Generate NPC reaction based on interaction outcome.

    Returns: {message, sentiment, styleGained, stylePoints}
    """
    if match_type == "wrong_language":
        return {
            "message": random.choice(WRONG_LANGUAGE_FEEDBACK),
            "sentiment": "negative",
            "styleGained": None,
            "stylePoints": 0,
        }

    if success:
        return {
            "message": random.choice(POSITIVE_FEEDBACK),
            "sentiment": "positive",
            "styleGained": style,
            "stylePoints": 1 if style else 0,
        }
    else:
        return {
            "message": random.choice(NEGATIVE_FEEDBACK),
            "sentiment": "negative",
            "styleGained": None,
            "stylePoints": 0,
        }
