"""
Voice Manifest for Story Mode.

Defines character voices for consistent TTS across story panels.
Similar to story_manifest.py for images, this ensures voice consistency.

Usage:
    from story_voices import get_story_voice_config, get_character_voice

    config = get_story_voice_config("shogun_test")
    voice = get_character_voice("shogun_test", "samurai_toranaga")
"""

from dataclasses import dataclass, field
from typing import Optional

# Available OpenAI TTS voices:
# - alloy: neutral, versatile (good for narration)
# - echo: male, warm
# - fable: male, formal, british accent
# - onyx: male, deep (good for authority figures)
# - nova: female, warm
# - shimmer: female, soft (good for Bimbo)


@dataclass
class CharacterVoice:
    """Voice configuration for a story character."""
    id: str                          # Character ID (matches panel speaker)
    voice: str                       # OpenAI voice name
    gender: str = "neutral"          # male/female/neutral
    default_sentiment: str = "neutral"  # Default emotion
    speaking_style: str = ""         # Custom instructions

    def get_instructions(self, sentiment: Optional[str] = None) -> str:
        """Build TTS instructions for this character."""
        parts = []
        if self.speaking_style:
            parts.append(self.speaking_style)
        return " ".join(parts) if parts else None


@dataclass
class StoryVoiceConfig:
    """Voice configuration for an entire story."""
    story_id: str
    narrator_voice: str = "alloy"
    narrator_style: str = "Speak with calm authority, painting vivid scenes. Measured pace, clear enunciation."
    characters: dict = field(default_factory=dict)  # id -> CharacterVoice

    def get_character(self, speaker: str) -> Optional[CharacterVoice]:
        """Get voice config for a speaker."""
        return self.characters.get(speaker)

    def get_voice_for_panel(self, panel: dict) -> dict:
        """Get complete voice config for a panel.

        Returns dict with:
        - narration_voice, narration_sentiment, narration_instructions
        - dialogue_voice, dialogue_sentiment, dialogue_instructions
        """
        result = {}

        # Narration config
        if panel.get("narration"):
            result["narration"] = {
                "voice": self.narrator_voice,
                "role": "narrator",
                "sentiment": "neutral",
                "instructions": self.narrator_style,
            }

        # Dialogue config
        if panel.get("dialogue") and panel.get("speaker"):
            speaker = panel["speaker"]
            char = self.get_character(speaker)
            if char:
                result["dialogue"] = {
                    "voice": char.voice,
                    "role": "npc",
                    "sentiment": char.default_sentiment,
                    "instructions": char.speaking_style,
                    "character_id": char.id,
                }
            else:
                # Fallback for unknown speakers
                result["dialogue"] = {
                    "voice": "alloy",
                    "role": "npc",
                    "sentiment": "neutral",
                }

        return result


# =============================================================================
# SHOGUN TEST STORY VOICES
# =============================================================================

SHOGUN_CHARACTERS = {
    # AI Companion - fairy-like guide
    "bimbo": CharacterVoice(
        id="bimbo",
        voice="shimmer",
        gender="female",
        default_sentiment="encouraging",
        speaking_style="Speak with a bright, fairy-like quality - helpful and encouraging. "
                      "Like a magical companion guiding an adventurer. Light, quick, energetic. "
                      "Similar to Navi from Zelda - small, helpful, with playful urgency.",
    ),

    # Main samurai antagonist/ally - Lord Toranaga type
    "samurai": CharacterVoice(
        id="samurai",
        voice="onyx",
        gender="male",
        default_sentiment="stern",
        speaking_style="Speak with the dignity and weight of a samurai lord. "
                      "Measured, powerful, commanding respect. Deep authority.",
    ),

    # Hana - interpreter/guide character
    "hana": CharacterVoice(
        id="hana",
        voice="nova",
        gender="female",
        default_sentiment="warm",
        speaking_style="Speak gracefully with warmth. A cultured woman navigating "
                      "between worlds - Japanese refinement with openness to foreigners.",
    ),

    # Player character (for examples/teaching moments)
    "player": CharacterVoice(
        id="player",
        voice="echo",
        gender="male",
        default_sentiment="neutral",
        speaking_style="Speak as a foreigner learning Japanese - careful pronunciation, "
                      "slight hesitation showing effort to communicate correctly.",
    ),

    # Generic villager/farmer
    "villager": CharacterVoice(
        id="villager",
        voice="echo",
        gender="male",
        default_sentiment="suspicious",
        speaking_style="Speak as a common villager - wary of strangers, "
                      "simple direct speech.",
    ),

    # Old village elder
    "elder": CharacterVoice(
        id="elder",
        voice="fable",
        gender="male",
        default_sentiment="thoughtful",
        speaking_style="Speak with aged wisdom and formality. "
                      "Slow, deliberate, respected voice of experience.",
    ),
}

SHOGUN_VOICE_CONFIG = StoryVoiceConfig(
    story_id="shogun_test",
    narrator_voice="alloy",
    narrator_style="Narrate with cinematic gravitas. Paint vivid imagery of feudal Japan. "
                  "Measured pace, dramatic pauses. Like a documentary narrator "
                  "describing an epic historical moment.",
    characters=SHOGUN_CHARACTERS,
)


# =============================================================================
# REGISTRY
# =============================================================================

STORY_VOICE_CONFIGS = {
    "shogun_test": SHOGUN_VOICE_CONFIG,
}


def get_story_voice_config(story_id: str) -> Optional[StoryVoiceConfig]:
    """Get voice configuration for a story."""
    return STORY_VOICE_CONFIGS.get(story_id)


def get_character_voice(story_id: str, speaker: str) -> Optional[CharacterVoice]:
    """Get voice config for a specific character in a story."""
    config = get_story_voice_config(story_id)
    if config:
        return config.get_character(speaker)
    return None


def get_panel_voice_config(story_id: str, panel: dict) -> dict:
    """Get complete voice configuration for a panel."""
    config = get_story_voice_config(story_id)
    if config:
        return config.get_voice_for_panel(panel)
    return {}
