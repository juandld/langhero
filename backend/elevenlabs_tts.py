"""
ElevenLabs Text-to-Speech integration.

Premium quality voices with emotional expressiveness.
Supports voice cloning, multilingual, and fine-tuned control.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import ElevenLabs
try:
    from elevenlabs import ElevenLabs, Voice, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None

# Cache directory - same as other TTS providers
CACHE_DIR = Path(__file__).parent.parent / "examples_audio" / "phrases"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Get API key
API_KEY = os.getenv("ELEVENLABS_API_KEY")


def get_client():
    """Get ElevenLabs client."""
    if not ELEVENLABS_AVAILABLE:
        raise RuntimeError("ElevenLabs not installed. Run: pip install elevenlabs")
    if not API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set in environment")
    return ElevenLabs(api_key=API_KEY)


def list_voices() -> list:
    """List all available ElevenLabs voices."""
    client = get_client()
    response = client.voices.get_all()

    voices = []
    for voice in response.voices:
        voices.append({
            "voice_id": voice.voice_id,
            "name": voice.name,
            "category": voice.category,
            "description": voice.description,
            "labels": voice.labels,
            "preview_url": voice.preview_url,
        })
    return voices


def print_voices():
    """Print available voices in a readable format."""
    voices = list_voices()

    print(f"\n{'='*60}")
    print(f"ELEVENLABS VOICES ({len(voices)} available)")
    print(f"{'='*60}\n")

    # Group by category
    categories = {}
    for v in voices:
        cat = v.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(v)

    for cat, cat_voices in sorted(categories.items()):
        print(f"\n## {cat.upper()} ({len(cat_voices)} voices)")
        print("-" * 40)
        for v in cat_voices:
            labels = v.get("labels", {})
            accent = labels.get("accent", "")
            age = labels.get("age", "")
            gender = labels.get("gender", "")
            use_case = labels.get("use_case", "")

            print(f"  {v['name']}")
            print(f"    ID: {v['voice_id']}")
            if gender or age or accent:
                print(f"    {gender} | {age} | {accent}")
            if use_case:
                print(f"    Best for: {use_case}")
            if v.get("preview_url"):
                print(f"    Preview: {v['preview_url']}")
            print()


# Popular voices for different use cases
RECOMMENDED_VOICES = {
    # Narration
    "narrator_male": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - deep, narrator
        "name": "Adam",
        "description": "Deep male voice, great for narration"
    },
    "narrator_female": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Bella - warm, storytelling
        "name": "Bella",
        "description": "Warm female voice, storytelling"
    },
    "narrator_dramatic": {
        "voice_id": "VR6AewLTigWG4xSOukaG",  # Arnold - powerful, dramatic
        "name": "Arnold",
        "description": "Powerful, dramatic narration"
    },

    # Characters
    "female_young": {
        "voice_id": "jBpfuIE2acCO8z3wKNLl",  # Gigi - young, energetic
        "name": "Gigi",
        "description": "Young, energetic female"
    },
    "female_warm": {
        "voice_id": "z9fAnlkpzviPz146aGWa",  # Glinda - warm, friendly
        "name": "Glinda",
        "description": "Warm, friendly female"
    },
    "male_authoritative": {
        "voice_id": "ODq5zmih8GrVes37Dizd",  # Patrick - authoritative
        "name": "Patrick",
        "description": "Authoritative male"
    },
    "male_warm": {
        "voice_id": "TX3LPaxmHKxFdv7VOQHJ",  # Liam - warm, friendly
        "name": "Liam",
        "description": "Warm, friendly male"
    },

    # Special
    "fairy_helper": {
        "voice_id": "jBpfuIE2acCO8z3wKNLl",  # Gigi - perfect for Bimbo
        "name": "Gigi",
        "description": "Young, bright - good for fairy/helper character"
    },
}

# Story character to ElevenLabs voice mapping
# Use voice_id directly for custom voices, or key from RECOMMENDED_VOICES
# "none" = no voice (text only)
CHARACTER_VOICES = {
    "narrator": "ksryVoNAGZT8GxWCTiVm",  # User's chosen narrator voice
    "bimbo": "ZT9u07TYPVl83ejeLakq",     # User's chosen bimbo voice
    "samurai": "male_authoritative",
    "hana": "female_warm",
    "player": "none",                     # Player is the user - no TTS
    "villager": "male_warm",
    "elder": "narrator_male",
}


def get_voice_id_for_character(character: str) -> Optional[str]:
    """Get ElevenLabs voice ID for a story character.

    Returns None if character should not have TTS (e.g., player).
    """
    voice_key = CHARACTER_VOICES.get(character, "narrator_female")

    # "none" means no voice for this character
    if voice_key == "none":
        return None

    # If it looks like a voice ID (long alphanumeric), use directly
    if len(voice_key) > 15 and voice_key.isalnum():
        return voice_key

    # Otherwise look up in recommended voices
    voice_info = RECOMMENDED_VOICES.get(voice_key, RECOMMENDED_VOICES["narrator_female"])
    return voice_info["voice_id"]


def synthesize_speech(
    text: str,
    voice_id: Optional[str] = None,
    character: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    output_format: str = "mp3",
) -> dict:
    """Synthesize speech using ElevenLabs.

    Args:
        text: Text to synthesize
        voice_id: ElevenLabs voice ID (or use character param)
        character: Character name for automatic voice selection
        stability: Voice stability (0-1, lower = more expressive)
        similarity_boost: Voice clarity (0-1, higher = clearer)
        style: Style exaggeration (0-1, higher = more stylized)
        use_speaker_boost: Boost speaker similarity
        output_format: "mp3" or "wav"

    Returns:
        dict with keys: file, voice, format, cached, provider
    """
    if not ELEVENLABS_AVAILABLE:
        raise RuntimeError("ElevenLabs not installed")

    # Get voice ID from character if not specified
    if not voice_id:
        if character:
            voice_id = get_voice_id_for_character(character)
            # None means no TTS for this character (e.g., player)
            if voice_id is None:
                return {"skip": True, "reason": "no_voice_for_character"}
        else:
            voice_id = RECOMMENDED_VOICES["narrator_female"]["voice_id"]

    # Build cache key
    cache_key = hashlib.md5(
        f"{text}:{voice_id}:{stability}:{similarity_boost}:{style}:{output_format}".encode()
    ).hexdigest()[:16]

    cache_file = CACHE_DIR / f"eleven-{cache_key}.{output_format}"

    # Check cache
    if cache_file.exists():
        return {
            "file": f"phrases/{cache_file.name}",
            "voice": voice_id,
            "format": output_format,
            "cached": True,
            "provider": "elevenlabs",
        }

    # Generate speech
    client = get_client()

    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",  # Best quality multilingual model
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
        ),
        output_format="mp3_44100_128" if output_format == "mp3" else "pcm_44100",
    )

    # Save to cache
    with open(cache_file, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return {
        "file": f"phrases/{cache_file.name}",
        "voice": voice_id,
        "format": output_format,
        "cached": False,
        "provider": "elevenlabs",
    }


# Quick test / voice browser
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "voices":
        print_voices()
    else:
        print("Testing ElevenLabs TTS...")
        try:
            result = synthesize_speech(
                "Welcome to Japan. The year is sixteen hundred.",
                character="narrator",
            )
            print(f"Success: {result}")
        except Exception as e:
            print(f"Error: {e}")

        print("\nRun 'python elevenlabs_tts.py voices' to list all available voices")
