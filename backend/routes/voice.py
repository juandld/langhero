"""
Voice and TTS endpoints for audio generation.

Supports multiple TTS providers:
- openai: OpenAI TTS (default, 6 voices)
- google: Google Cloud TTS (Neural2/Journey voices, more natural)
"""

from fastapi import APIRouter, Request, Response
import voice_select
import voice_cache
from services.scenarios import get_scenario_by_id

# Try to import Google TTS
try:
    import google_tts
    GOOGLE_TTS_AVAILABLE = google_tts.GOOGLE_TTS_AVAILABLE
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    google_tts = None

# Try to import ElevenLabs TTS
try:
    import elevenlabs_tts
    ELEVENLABS_AVAILABLE = elevenlabs_tts.ELEVENLABS_AVAILABLE
except ImportError:
    ELEVENLABS_AVAILABLE = False
    elevenlabs_tts = None

router = APIRouter(prefix="/api", tags=["voice"])


@router.get("/voices")
async def api_voices():
    """Return available TTS voices, sentiments, and their characteristics."""
    return {
        "voices": voice_select.VOICES,
        "male": voice_select.MALE_VOICES,
        "female": voice_select.FEMALE_VOICES,
        "neutral": voice_select.NEUTRAL_VOICES,
        "character_types": list(voice_select.CHARACTER_TYPE_VOICES.keys()),
        "sentiments": list(voice_select.SENTIMENT_INSTRUCTIONS.keys()),
        "contexts": list(voice_select.CONTEXT_SENTIMENTS.keys()),
    }


@router.post("/tts")
async def api_tts(request: Request):
    """Return a cached/pre-rendered voice clip for a short phrase.

    Body JSON: {
        "text": "...",
        "language"?: "Japanese",
        "voice"?: "alloy",              # explicit voice override
        "format"?: "mp3",
        "provider"?: "google",          # "openai" (default) or "google"
        "scenario_id"?: 1,              # for auto voice selection
        "character_id"?: "merchant_1",  # for consistent voice across scenes
        "character"?: "narrator",       # character name for Google TTS voice selection
        "role"?: "npc",                 # context: "npc", "narrator", "bimbo"
        "character_gender"?: "female",  # hint for auto selection
        "character_type"?: "samurai",   # hint for auto selection
        "sentiment"?: "suspicious",     # emotion/tone for expressive TTS
        "context"?: "greeting"          # situational context for sentiment inference
    }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    text = str((body or {}).get("text") or "").strip()
    if not text:
        return Response(status_code=400)

    language = (body or {}).get("language")
    fmt = str((body or {}).get("format") or "mp3").strip().lower() or "mp3"
    if fmt not in {"mp3", "wav", "opus"}:
        fmt = "mp3"

    # Check provider preference
    provider = str((body or {}).get("provider") or "elevenlabs").strip().lower()

    # Use ElevenLabs if requested and available
    if provider == "elevenlabs" and ELEVENLABS_AVAILABLE:
        character = (body or {}).get("character")
        role = str((body or {}).get("role") or "npc").strip().lower()

        # Map role to character if not specified
        if not character:
            if role == "narrator":
                character = "narrator"
            elif role == "bimbo":
                character = "bimbo"

        try:
            result = elevenlabs_tts.synthesize_speech(
                text=text,
                character=character,
                output_format=fmt if fmt in ("mp3", "wav") else "mp3",
            )

            # Check if TTS should be skipped (e.g., player character)
            if result.get("skip"):
                return {"skip": True, "reason": result.get("reason", "no_voice")}

            return {
                "clip_id": f"eleven_{result.get('voice', 'unknown')[:8]}",
                "phrase_id": None,
                "file": result["file"],
                "voice": result["voice"],
                "format": result["format"],
                "url": f"/examples/{result['file']}",
                "provider": "elevenlabs",
                "cached": result.get("cached", False),
            }
        except Exception as e:
            # Fall back to Google if ElevenLabs fails
            print(f"[TTS] ElevenLabs failed, falling back to Google: {e}")
            provider = "google"

    # Use Google TTS if requested and available
    if provider == "google" and GOOGLE_TTS_AVAILABLE:
        character = (body or {}).get("character")
        role = str((body or {}).get("role") or "npc").strip().lower()

        # Map role to character if not specified
        if not character:
            if role == "narrator":
                character = "narrator"
            elif role == "bimbo":
                character = "bimbo"

        try:
            result = google_tts.synthesize_speech(
                text=text,
                character=character,
                language=language[:2] if language else None,
                output_format=fmt,
            )
            return {
                "clip_id": f"gcloud_{result.get('voice', 'unknown')}",
                "phrase_id": None,
                "file": result["file"],
                "voice": result["voice"],
                "format": result["format"],
                "url": f"/examples/{result['file']}",
                "provider": "google",
                "cached": result.get("cached", False),
            }
        except Exception as e:
            # Fall back to OpenAI if Google fails
            print(f"[TTS] Google TTS failed, falling back to OpenAI: {e}")
            provider = "openai"

    # OpenAI TTS (default/fallback)
    # Build context for voice/sentiment selection
    scenario_id = (body or {}).get("scenario_id")
    scenario = None
    if scenario_id:
        scenario = get_scenario_by_id(int(scenario_id))

    # Allow hints without full scenario
    context = dict(scenario) if scenario else {}
    if (body or {}).get("character_id"):
        context["character_id"] = body["character_id"]
    if (body or {}).get("character_gender"):
        context["character_gender"] = body["character_gender"]
    if (body or {}).get("character_type"):
        context["character_type"] = body["character_type"]

    # Determine voice: explicit > auto-select > default
    explicit_voice = (body or {}).get("voice")
    if explicit_voice:
        voice = str(explicit_voice).strip()
    else:
        role = str((body or {}).get("role") or "npc").strip()
        voice = voice_select.select_voice(scenario=context, role=role, default="alloy")

    # Build sentiment instructions
    sentiment = (body or {}).get("sentiment")
    ctx_hint = (body or {}).get("context")
    char_type = context.get("character_type")
    role = str((body or {}).get("role") or "npc").strip().lower()

    # Use special Bimbo instructions for fairy-like voice
    if role == "bimbo":
        base_instructions = voice_select.get_bimbo_instructions()
        sentiment_inst = voice_select.get_sentiment_instructions(sentiment, ctx_hint)
        if sentiment_inst:
            instructions = f"{base_instructions} {sentiment_inst}"
        else:
            instructions = base_instructions
    else:
        instructions = voice_select.build_tts_instructions(
            sentiment=sentiment,
            context=ctx_hint,
            language=language,
            character_type=char_type,
        )

    try:
        meta = voice_cache.get_or_create_clip(
            text,
            language=language,
            voice=voice,
            fmt=fmt,
            instructions=instructions,
        )
        return {
            **meta,
            "url": f"/examples/{meta['file']}",
            "voice": voice,
            "sentiment": sentiment,
            "instructions": instructions,
            "provider": "openai",
        }
    except Exception as e:
        return {"error": str(e)}
