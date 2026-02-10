"""
Automatic voice selection for TTS based on character metadata.

Supports:
- Explicit override via 'voice' field
- Deterministic assignment based on character_id (consistency)
- Smart defaults based on character_gender, character_type
- Sentiment/emotion instructions for expressive TTS
"""

from __future__ import annotations

import hashlib
from typing import Optional

# OpenAI TTS available voices
VOICES = {
    "alloy": {"gender": "neutral", "tone": "versatile", "accent": "neutral"},
    "echo": {"gender": "male", "tone": "warm", "accent": "neutral"},
    "fable": {"gender": "male", "tone": "formal", "accent": "british"},
    "onyx": {"gender": "male", "tone": "deep", "accent": "neutral"},
    "nova": {"gender": "female", "tone": "warm", "accent": "neutral"},
    "shimmer": {"gender": "female", "tone": "soft", "accent": "neutral"},
}

# Voice pools by gender
MALE_VOICES = ["echo", "onyx", "fable"]
FEMALE_VOICES = ["nova", "shimmer"]
NEUTRAL_VOICES = ["alloy"]

# Character type to voice mapping (for Japanese historical setting)
# Order matters: first voice is primary, others are fallbacks
CHARACTER_TYPE_VOICES = {
    # Authority figures
    "samurai": ["onyx", "echo"],
    "shogun": ["onyx"],
    "lord": ["onyx", "fable"],
    "daimyo": ["onyx", "echo"],
    "warrior": ["onyx", "echo"],

    # Common folk
    "merchant": ["echo", "nova"],
    "shopkeeper": ["echo", "nova"],
    "innkeeper": ["echo", "nova"],
    "villager": ["echo", "nova", "shimmer"],
    "farmer": ["echo"],

    # Service roles
    "servant": ["shimmer", "nova"],
    "geisha": ["shimmer"],
    "entertainer": ["nova", "shimmer"],

    # Special roles
    "narrator": ["alloy"],
    "guide": ["alloy"],
    "bimbo": ["shimmer"],  # AI companion - Navi-like fairy voice
    "teacher": ["alloy", "nova"],
    "child": ["shimmer", "nova"],

    # Foreign characters
    "foreigner": ["fable", "echo"],
    "english": ["fable"],
    "portuguese": ["echo"],
}

# Role context defaults
ROLE_DEFAULTS = {
    "npc": None,  # Will use character metadata
    "narrator": "alloy",
    "bimbo": "shimmer",  # Navi-like fairy companion voice
    "player_example": "nova",  # Warm voice for teaching
    "system": "alloy",
}

# Special character voice instructions
BIMBO_INSTRUCTIONS = (
    "Speak with a bright, fairy-like quality - helpful and encouraging but slightly urgent, "
    "like a magical companion guiding an adventurer. Keep the tone light, quick, and energetic. "
    "Similar to Navi from Zelda - small, helpful, with a hint of playful impatience."
)

# Sentiment to TTS instructions mapping
# These are passed to OpenAI TTS for expressive speech
SENTIMENT_INSTRUCTIONS = {
    # Positive sentiments
    "warm": "Speak warmly and kindly, with a gentle welcoming tone.",
    "friendly": "Speak in a friendly, approachable manner.",
    "encouraging": "Speak encouragingly, like a supportive teacher.",
    "happy": "Speak with joy and happiness in your voice.",
    "excited": "Speak with excitement and enthusiasm.",
    "grateful": "Speak with gratitude and appreciation.",
    "proud": "Speak with pride and satisfaction.",

    # Neutral sentiments
    "neutral": "Speak in a calm, neutral tone.",
    "formal": "Speak formally and professionally.",
    "calm": "Speak calmly and steadily.",
    "informative": "Speak clearly and informatively, like a teacher.",
    "thoughtful": "Speak thoughtfully, with measured pauses.",

    # Negative/tense sentiments
    "suspicious": "Speak with suspicion and wariness, slightly guarded.",
    "stern": "Speak sternly and seriously.",
    "angry": "Speak with restrained anger, firm and tense.",
    "threatening": "Speak with a low, threatening undertone.",
    "impatient": "Speak with slight impatience, hurried.",
    "worried": "Speak with concern and worry in your voice.",
    "sad": "Speak with sadness, slightly subdued.",
    "confused": "Speak with confusion, questioning.",

    # Urgent/dramatic
    "urgent": "Speak urgently, with importance and haste.",
    "commanding": "Speak with authority and command.",
    "dramatic": "Speak dramatically, with weight and gravity.",
    "whispered": "Speak softly, almost in a whisper.",
}

# Default sentiment for different contexts
CONTEXT_SENTIMENTS = {
    "greeting": "warm",
    "question": "neutral",
    "teaching": "encouraging",
    "warning": "stern",
    "threat": "threatening",
    "praise": "proud",
    "correction": "informative",
}


def _deterministic_pick(options: list[str], seed: str) -> str:
    """Deterministically pick from a list based on a seed string.

    Uses hash to ensure same seed always picks same option.
    """
    if not options:
        return "alloy"
    if len(options) == 1:
        return options[0]
    # Hash the seed and use it to index into options
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


def _get_character_seed(scenario: Optional[dict]) -> str:
    """Generate a consistent seed for character voice selection.

    Uses character_id, character_name, or scenario_id for consistency.
    """
    if not scenario:
        return ""

    # Priority: character_id > character_name > scenario_id
    char_id = scenario.get("character_id") or scenario.get("npc_id")
    if char_id:
        return f"char:{char_id}"

    char_name = scenario.get("character_name") or scenario.get("npc_name")
    if char_name:
        return f"name:{char_name}"

    scenario_id = scenario.get("id") or scenario.get("scenario_id")
    if scenario_id:
        return f"scenario:{scenario_id}"

    return ""


def select_voice(
    scenario: Optional[dict] = None,
    option: Optional[dict] = None,
    example: Optional[dict] = None,
    role: str = "npc",
    default: str = "alloy",
) -> str:
    """Select the best voice for TTS based on context.

    Priority:
    1. Explicit 'voice' field in example
    2. Explicit 'voice' field in option
    3. Explicit 'voice' field in scenario
    4. Role-based default (narrator, bimbo, etc.)
    5. Character type mapping (deterministic based on character_id)
    6. Gender-based selection (deterministic based on character_id)
    7. Fallback default

    Args:
        scenario: The scenario dict (may contain character_voice, character_gender, character_type)
        option: The option dict (may contain voice override)
        example: The example dict (may contain voice override)
        role: Context role - "npc", "narrator", "bimbo", "player_example", "system"
        default: Fallback voice if nothing else matches

    Returns:
        Voice name string (e.g., "nova", "onyx", "alloy")
    """
    # 1. Check explicit voice in example
    if example and example.get("voice"):
        voice = _normalize_voice(example["voice"])
        if voice:
            return voice

    # 2. Check explicit voice in option
    if option and option.get("voice"):
        voice = _normalize_voice(option["voice"])
        if voice:
            return voice

    # 3. Check explicit voice in scenario
    if scenario:
        for key in ("voice", "character_voice", "npc_voice"):
            if scenario.get(key):
                voice = _normalize_voice(scenario[key])
                if voice:
                    return voice

    # 4. Role-based defaults
    role_lower = (role or "").lower().strip()
    if role_lower in ROLE_DEFAULTS and ROLE_DEFAULTS[role_lower]:
        return ROLE_DEFAULTS[role_lower]

    # Get consistent seed for deterministic selection
    seed = _get_character_seed(scenario)

    # 5. Character type mapping (deterministic)
    if scenario:
        char_type = (scenario.get("character_type") or "").lower().strip()
        if char_type in CHARACTER_TYPE_VOICES:
            voices = CHARACTER_TYPE_VOICES[char_type]
            return _deterministic_pick(voices, seed or char_type)

    # 6. Gender-based selection (deterministic)
    if scenario:
        gender = (scenario.get("character_gender") or "").lower().strip()
        if gender in ("male", "m", "man"):
            return _deterministic_pick(MALE_VOICES, seed or "male")
        elif gender in ("female", "f", "woman"):
            return _deterministic_pick(FEMALE_VOICES, seed or "female")
        elif gender in ("neutral", "nonbinary", "nb"):
            return "alloy"

    # 7. Fallback
    return default


def get_sentiment_instructions(
    sentiment: Optional[str] = None,
    context: Optional[str] = None,
) -> Optional[str]:
    """Get TTS instructions for expressing a sentiment.

    Args:
        sentiment: Explicit sentiment (e.g., "warm", "suspicious", "angry")
        context: Context hint to infer sentiment (e.g., "greeting", "warning")

    Returns:
        Instruction string for TTS, or None if no specific sentiment.
    """
    # Use explicit sentiment if provided
    if sentiment:
        sent_lower = sentiment.lower().strip()
        if sent_lower in SENTIMENT_INSTRUCTIONS:
            return SENTIMENT_INSTRUCTIONS[sent_lower]

    # Infer from context if available
    if context:
        ctx_lower = context.lower().strip()
        if ctx_lower in CONTEXT_SENTIMENTS:
            inferred = CONTEXT_SENTIMENTS[ctx_lower]
            if inferred in SENTIMENT_INSTRUCTIONS:
                return SENTIMENT_INSTRUCTIONS[inferred]

    return None


def build_tts_instructions(
    sentiment: Optional[str] = None,
    context: Optional[str] = None,
    language: Optional[str] = None,
    character_type: Optional[str] = None,
) -> Optional[str]:
    """Build complete TTS instructions combining sentiment and context.

    Args:
        sentiment: Emotion/sentiment for the speech
        context: Situational context
        language: Target language (for pronunciation hints)
        character_type: Type of character speaking

    Returns:
        Combined instruction string, or None if no specific instructions.
    """
    parts = []

    # Add sentiment instructions
    sent_inst = get_sentiment_instructions(sentiment, context)
    if sent_inst:
        parts.append(sent_inst)

    # Add character-specific hints
    if character_type:
        ct_lower = character_type.lower().strip()
        if ct_lower == "samurai":
            parts.append("Speak with the dignity of a warrior.")
        elif ct_lower in ("shogun", "lord", "daimyo"):
            parts.append("Speak with authority and power.")
        elif ct_lower == "child":
            parts.append("Speak with youthful energy.")
        elif ct_lower == "geisha":
            parts.append("Speak gracefully and elegantly.")

    # Add language hints for proper pronunciation
    if language:
        lang_lower = language.lower().strip()
        if "japanese" in lang_lower or lang_lower == "ja":
            parts.append("Pronounce Japanese words clearly and naturally.")

    if not parts:
        return None

    return " ".join(parts)


def _normalize_voice(voice: str) -> Optional[str]:
    """Normalize and validate voice name."""
    if not voice:
        return None
    v = voice.lower().strip()
    if v in VOICES:
        return v
    # Try partial match
    for name in VOICES:
        if name.startswith(v) or v in name:
            return name
    return None


def get_voice_for_scenario(scenario: dict, role: str = "npc") -> str:
    """Convenience wrapper for scenario-level voice selection."""
    return select_voice(scenario=scenario, role=role)


def get_voice_for_example(
    scenario: dict,
    option: dict,
    example: dict,
    role: str = "npc",
) -> str:
    """Get voice for a specific example phrase."""
    return select_voice(
        scenario=scenario,
        option=option,
        example=example,
        role=role,
    )


def get_bimbo_voice() -> str:
    """Get the voice for Bimbo (AI companion)."""
    return "shimmer"


def get_bimbo_instructions() -> str:
    """Get TTS instructions for Bimbo's Navi-like voice."""
    return BIMBO_INSTRUCTIONS


def get_narrator_voice() -> str:
    """Get the voice for narration."""
    return "alloy"


def describe_voice(voice: str) -> dict:
    """Get metadata about a voice."""
    return VOICES.get(voice, {"gender": "unknown", "tone": "unknown", "accent": "unknown"})


# For scenarios that want variety, pick a random appropriate voice
def random_male_voice() -> str:
    return random.choice(MALE_VOICES)


def random_female_voice() -> str:
    return random.choice(FEMALE_VOICES)


def random_voice() -> str:
    return random.choice(list(VOICES.keys()))
