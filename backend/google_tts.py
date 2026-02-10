"""
Google Cloud Text-to-Speech integration.

Uses WaveNet and Neural2 voices for more natural speech.
Supports SSML for pauses, emphasis, and prosody control.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import Google Cloud TTS
try:
    from google.cloud import texttospeech_v1 as texttospeech
    from google.oauth2 import service_account
    from google.api_core import exceptions as google_exceptions
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    texttospeech = None

# Cache directory - use same location as OpenAI TTS (examples_audio relative to project root)
CACHE_DIR = Path(__file__).parent.parent / "examples_audio" / "phrases"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Google Cloud TTS Voice Catalog
# Format: voice_name -> (language_code, voice_type, gender, description)
GOOGLE_VOICES = {
    # English voices - Neural2 (best quality)
    "en-neural2-a": ("en-US", "Neural2", "MALE", "American male, warm"),
    "en-neural2-c": ("en-US", "Neural2", "FEMALE", "American female, warm"),
    "en-neural2-d": ("en-US", "Neural2", "MALE", "American male, authoritative"),
    "en-neural2-f": ("en-US", "Neural2", "FEMALE", "American female, friendly"),
    "en-neural2-j": ("en-US", "Neural2", "MALE", "American male, casual"),

    # English - Journey voices (optimized for long-form narration)
    "en-journey-d": ("en-US", "Journey", "MALE", "Narrator, engaging"),
    "en-journey-f": ("en-US", "Journey", "FEMALE", "Narrator, warm"),
    "en-journey-o": ("en-US", "Journey", "FEMALE", "Narrator, expressive"),

    # English - Studio voices (highest quality, limited)
    "en-studio-o": ("en-US", "Studio", "FEMALE", "Studio quality female"),
    "en-studio-q": ("en-US", "Studio", "MALE", "Studio quality male"),

    # Japanese voices - Neural2
    "ja-neural2-b": ("ja-JP", "Neural2", "FEMALE", "Japanese female, natural"),
    "ja-neural2-c": ("ja-JP", "Neural2", "MALE", "Japanese male, natural"),
    "ja-neural2-d": ("ja-JP", "Neural2", "MALE", "Japanese male, formal"),

    # Japanese - WaveNet (good quality)
    "ja-wavenet-a": ("ja-JP", "WaveNet", "FEMALE", "Japanese female, clear"),
    "ja-wavenet-b": ("ja-JP", "WaveNet", "FEMALE", "Japanese female, soft"),
    "ja-wavenet-c": ("ja-JP", "WaveNet", "MALE", "Japanese male, clear"),
    "ja-wavenet-d": ("ja-JP", "WaveNet", "MALE", "Japanese male, deep"),
}

# Story character to Google voice mapping
CHARACTER_VOICES = {
    # Narrator - Journey voice for engaging long-form narration
    "narrator": "en-journey-d",

    # Bimbo - Female, bright and helpful
    "bimbo": "en-neural2-f",

    # Samurai - Male, authoritative
    "samurai": "en-neural2-d",

    # Hana - Female, warm
    "hana": "en-neural2-c",

    # Player - Male, casual
    "player": "en-neural2-j",

    # Villager - Male, wary
    "villager": "en-neural2-a",

    # Elder - Male, formal/wise
    "elder": "en-neural2-d",

    # Japanese dialogue (when speaking Japanese)
    "ja_female": "ja-neural2-b",
    "ja_male": "ja-neural2-c",
}

# Speaking rate adjustments by character
CHARACTER_SPEAKING_RATES = {
    "narrator": 0.95,    # Slightly slower for narration
    "bimbo": 1.1,        # Slightly faster, energetic
    "samurai": 0.9,      # Slower, deliberate
    "hana": 1.0,         # Normal
    "player": 1.0,       # Normal
    "villager": 1.0,     # Normal
    "elder": 0.85,       # Slower, wise
}

# Pitch adjustments (semitones, -20 to +20)
CHARACTER_PITCH = {
    "narrator": 0,
    "bimbo": 2,          # Slightly higher, fairy-like
    "samurai": -2,       # Lower, commanding
    "hana": 1,           # Slightly higher
    "player": 0,
    "villager": 0,
    "elder": -1,         # Slightly lower
}


def get_client():
    """Get Google Cloud TTS client."""
    if not GOOGLE_TTS_AVAILABLE:
        raise RuntimeError("Google Cloud TTS not installed")

    # Check for service account file first
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_file and os.path.exists(creds_file):
        credentials = service_account.Credentials.from_service_account_file(creds_file)
        return texttospeech.TextToSpeechClient(credentials=credentials)

    # Try API key authentication
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        # For API key, we need to use REST transport
        from google.cloud import texttospeech_v1
        client_options = {"api_key": api_key}
        return texttospeech_v1.TextToSpeechClient(client_options=client_options)

    # Fall back to default credentials (ADC)
    return texttospeech.TextToSpeechClient()


def get_voice_for_character(character: str, language: str = "en") -> str:
    """Get the appropriate Google voice for a character."""
    # Japanese text uses Japanese voices
    if language == "ja" or _contains_japanese(character):
        if character in ("hana", "bimbo"):
            return CHARACTER_VOICES.get("ja_female", "ja-neural2-b")
        return CHARACTER_VOICES.get("ja_male", "ja-neural2-c")

    return CHARACTER_VOICES.get(character, "en-journey-d")


def _contains_japanese(text: str) -> bool:
    """Check if text contains Japanese characters."""
    for char in text:
        if '\u3040' <= char <= '\u309F':  # Hiragana
            return True
        if '\u30A0' <= char <= '\u30FF':  # Katakana
            return True
        if '\u4E00' <= char <= '\u9FFF':  # Kanji
            return True
    return False


def _build_ssml(
    text: str,
    speaking_rate: float = 1.0,
    pitch: float = 0,
    emphasis: Optional[str] = None,
    break_time: Optional[str] = None,
) -> str:
    """Build SSML for more expressive speech.

    Args:
        text: The text to speak
        speaking_rate: Speed multiplier (0.25 to 4.0)
        pitch: Pitch adjustment in semitones (-20 to +20)
        emphasis: Emphasis level (strong, moderate, reduced)
        break_time: Add break before text (e.g., "500ms", "1s")
    """
    ssml_parts = ['<speak>']

    # Add break if specified
    if break_time:
        ssml_parts.append(f'<break time="{break_time}"/>')

    # Add prosody wrapper
    prosody_attrs = []
    if speaking_rate != 1.0:
        prosody_attrs.append(f'rate="{speaking_rate}"')
    if pitch != 0:
        sign = "+" if pitch > 0 else ""
        prosody_attrs.append(f'pitch="{sign}{pitch}st"')

    if prosody_attrs:
        ssml_parts.append(f'<prosody {" ".join(prosody_attrs)}>')

    # Add emphasis if specified
    if emphasis:
        ssml_parts.append(f'<emphasis level="{emphasis}">')
        ssml_parts.append(text)
        ssml_parts.append('</emphasis>')
    else:
        ssml_parts.append(text)

    if prosody_attrs:
        ssml_parts.append('</prosody>')

    ssml_parts.append('</speak>')

    return ''.join(ssml_parts)


def synthesize_speech(
    text: str,
    voice_name: str = "en-journey-d",
    character: Optional[str] = None,
    language: Optional[str] = None,
    use_ssml: bool = True,
    output_format: str = "mp3",
) -> dict:
    """Synthesize speech using Google Cloud TTS.

    Args:
        text: Text to synthesize
        voice_name: Google voice name (e.g., "en-journey-d")
        character: Character name for automatic voice/rate/pitch selection
        language: Language hint ("en" or "ja")
        use_ssml: Whether to use SSML for prosody control
        output_format: "mp3" or "wav"

    Returns:
        dict with keys: file, voice, format, cached
    """
    if not GOOGLE_TTS_AVAILABLE:
        raise RuntimeError("Google Cloud TTS not installed")

    # Auto-detect language from text
    if not language:
        language = "ja" if _contains_japanese(text) else "en"

    # Get voice for character
    if character:
        voice_name = get_voice_for_character(character, language)

    # Get voice info
    voice_info = GOOGLE_VOICES.get(voice_name)
    if not voice_info:
        # Default to journey narrator
        voice_name = "en-journey-d"
        voice_info = GOOGLE_VOICES[voice_name]

    language_code, voice_type, gender, description = voice_info

    # Get character-specific adjustments
    speaking_rate = CHARACTER_SPEAKING_RATES.get(character, 1.0)
    pitch = CHARACTER_PITCH.get(character, 0)

    # Build cache key
    cache_key = hashlib.md5(
        f"{text}:{voice_name}:{speaking_rate}:{pitch}:{output_format}".encode()
    ).hexdigest()[:16]

    cache_file = CACHE_DIR / f"google-{cache_key}.{output_format}"

    # Check cache
    if cache_file.exists():
        return {
            "file": f"phrases/{cache_file.name}",
            "voice": voice_name,
            "format": output_format,
            "cached": True,
            "provider": "google",
        }

    # Build input (SSML or plain text)
    if use_ssml:
        ssml = _build_ssml(text, speaking_rate=speaking_rate, pitch=pitch)
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=text)

    # Configure voice
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=f"{language_code}-{voice_type}-{voice_name.split('-')[-1].upper()}",
    )

    # For Neural2/Journey/Studio, use the full voice name
    if voice_type in ("Neural2", "Journey", "Studio"):
        # Neural2 voices use format like: en-US-Neural2-A
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=f"{language_code}-{voice_type}-{voice_name.split('-')[-1].upper()}",
        )

    # Configure audio
    audio_encoding = (
        texttospeech.AudioEncoding.MP3
        if output_format == "mp3"
        else texttospeech.AudioEncoding.LINEAR16
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=audio_encoding,
        speaking_rate=speaking_rate if not use_ssml else 1.0,  # Use SSML rate if available
        pitch=pitch if not use_ssml else 0,  # Use SSML pitch if available
    )

    # Synthesize
    client = get_client()

    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
    except google_exceptions.InvalidArgument as e:
        # If voice name format is wrong, try simpler format
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.MALE if gender == "MALE" else texttospeech.SsmlVoiceGender.FEMALE,
        )
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

    # Save to cache
    with open(cache_file, "wb") as f:
        f.write(response.audio_content)

    return {
        "file": f"phrases/{cache_file.name}",
        "voice": voice_name,
        "format": output_format,
        "cached": False,
        "provider": "google",
    }


def list_available_voices(language_code: Optional[str] = None) -> list:
    """List available Google TTS voices."""
    if not GOOGLE_TTS_AVAILABLE:
        return []

    client = get_client()
    response = client.list_voices(language_code=language_code)

    voices = []
    for voice in response.voices:
        voices.append({
            "name": voice.name,
            "language_codes": list(voice.language_codes),
            "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
            "natural_sample_rate": voice.natural_sample_rate_hertz,
        })

    return voices


# Quick test
if __name__ == "__main__":
    print("Testing Google TTS...")

    try:
        result = synthesize_speech(
            "Welcome to Japan. The year is 1600.",
            character="narrator",
        )
        print(f"Generated: {result}")
    except Exception as e:
        print(f"Error: {e}")
