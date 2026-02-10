"""
AI Image Generation via Google's Nano Banana (Gemini Image Generation).

Supports reference images for character consistency.
"""

import os
import hashlib
import base64
import asyncio
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

# Cache directories
IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache")
CHARACTER_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "characters")
LOCATION_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "locations")
PANEL_DIR = os.path.join(IMAGE_CACHE_DIR, "panels")

# Models
NANO_BANANA_FAST = "gemini-2.5-flash-image"  # Fast, good quality
NANO_BANANA_PRO = "gemini-3-pro-image-preview"  # Best quality

# Default to Pro for best results
NANO_BANANA = NANO_BANANA_PRO


def _get_api_key() -> str:
    """Get Google API key."""
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not configured")
    return key


def _ensure_dirs() -> None:
    """Ensure cache directories exist."""
    for d in [IMAGE_CACHE_DIR, CHARACTER_REF_DIR, LOCATION_REF_DIR, PANEL_DIR]:
        os.makedirs(d, exist_ok=True)


def _cache_key(prompt: str, refs: list = None) -> str:
    """Generate cache key from prompt and reference paths."""
    content = prompt + ("|".join(refs) if refs else "")
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _load_image_as_base64(path: str) -> tuple[str, str]:
    """Load image and return (base64_data, mime_type)."""
    ext = path.lower().split(".")[-1]
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


async def generate_image(
    prompt: str,
    reference_images: list[str] = None,
    output_path: str = None,
    force: bool = False,
) -> dict:
    """Generate an image with optional reference images.

    Args:
        prompt: Text prompt describing the image
        reference_images: List of paths to reference images
        output_path: Where to save (if None, uses cache with hash)
        force: Regenerate even if cached

    Returns:
        {"path": "/path/to/image.png", "cached": bool}
    """
    _ensure_dirs()

    # Determine output path
    if output_path is None:
        cache_key = _cache_key(prompt, reference_images)
        output_path = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.png")

    # Check cache
    if not force and os.path.exists(output_path):
        return {"path": output_path, "cached": True}

    # Build request parts
    parts = []

    # Add reference images first
    if reference_images:
        for ref_path in reference_images:
            if os.path.exists(ref_path):
                img_data, mime_type = _load_image_as_base64(ref_path)
                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": img_data
                    }
                })

    # Add text prompt
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        }
    }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{NANO_BANANA}:generateContent"
    api_key = _get_api_key()

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            api_url,
            params={"key": api_key},
            json=payload,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Generation failed ({response.status_code}): {response.text[:500]}")

        result = response.json()
        candidates = result.get("candidates", [])

        if not candidates:
            raise RuntimeError("No candidates in response")

        parts = candidates[0].get("content", {}).get("parts", [])

        for part in parts:
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                return {"path": output_path, "cached": False}

        raise RuntimeError("No image in response")


async def generate_character_ref(
    character_id: str,
    prompt: str,
    face_reference: str = None,
    force: bool = False,
) -> dict:
    """Generate a character reference image.

    Args:
        character_id: e.g., "bimbo", "mariko"
        prompt: Character description
        face_reference: Path to face reference image
        force: Regenerate even if exists

    Returns:
        {"character_id": str, "path": str, "cached": bool}
    """
    output_path = os.path.join(CHARACTER_REF_DIR, f"{character_id}.png")
    refs = [face_reference] if face_reference else None

    result = await generate_image(prompt, refs, output_path, force)
    return {
        "character_id": character_id,
        "path": result["path"],
        "cached": result["cached"],
    }


async def generate_character_variant(
    character_id: str,
    variant_name: str,
    prompt: str,
    force: bool = False,
) -> dict:
    """Generate a variant of an existing character.

    Uses the character's base reference for consistency.

    Args:
        character_id: e.g., "bimbo"
        variant_name: e.g., "casual", "kimono", "danger"
        prompt: Variant description
        force: Regenerate

    Returns:
        {"character_id": str, "variant": str, "path": str, "cached": bool}
    """
    base_ref = os.path.join(CHARACTER_REF_DIR, f"{character_id}.png")
    if not os.path.exists(base_ref):
        raise RuntimeError(f"Base reference for {character_id} not found. Generate base first.")

    output_path = os.path.join(CHARACTER_REF_DIR, f"{character_id}_{variant_name}.png")

    result = await generate_image(prompt, [base_ref], output_path, force)
    return {
        "character_id": character_id,
        "variant": variant_name,
        "path": result["path"],
        "cached": result["cached"],
    }


async def generate_location_ref(
    location_id: str,
    prompt: str,
    force: bool = False,
) -> dict:
    """Generate a location reference image.

    Args:
        location_id: e.g., "beach_dawn", "castle_interior"
        prompt: Location description

    Returns:
        {"location_id": str, "path": str, "cached": bool}
    """
    output_path = os.path.join(LOCATION_REF_DIR, f"{location_id}.png")

    result = await generate_image(prompt, None, output_path, force)
    return {
        "location_id": location_id,
        "path": result["path"],
        "cached": result["cached"],
    }


async def generate_panel(
    panel_id: str,
    prompt: str,
    character_refs: list[str] = None,
    location_ref: str = None,
    reference_images: list[str] = None,
    chapter: str = None,
    force: bool = False,
) -> dict:
    """Generate a story panel with character and location references.

    Args:
        panel_id: Unique panel identifier
        prompt: Panel scene description
        character_refs: List of character_ids to include as references (legacy)
        location_ref: location_id to use as reference (legacy)
        reference_images: Direct list of reference image paths (preferred)
        chapter: Chapter folder (e.g., "ch01")
        force: Regenerate

    Returns:
        {"panel_id": str, "path": str, "cached": bool}
    """
    # Build reference list
    refs = []

    # Prefer direct reference_images if provided
    if reference_images:
        for ref_path in reference_images:
            if os.path.exists(ref_path):
                refs.append(ref_path)
    else:
        # Legacy behavior: look up by ID
        if character_refs:
            for char_id in character_refs:
                char_path = os.path.join(CHARACTER_REF_DIR, f"{char_id}.png")
                if os.path.exists(char_path):
                    refs.append(char_path)

        if location_ref:
            loc_path = os.path.join(LOCATION_REF_DIR, f"{location_ref}.png")
            if os.path.exists(loc_path):
                refs.append(loc_path)

    # Output path
    if chapter:
        panel_dir = os.path.join(PANEL_DIR, chapter)
    else:
        panel_dir = PANEL_DIR

    output_path = os.path.join(panel_dir, f"{panel_id}.png")

    result = await generate_image(prompt, refs if refs else None, output_path, force)
    return {
        "panel_id": panel_id,
        "path": result["path"],
        "cached": result["cached"],
    }


# ============================================================
# CHARACTER PROMPTS
# ============================================================

FACE_REFERENCE = os.path.join(os.path.dirname(__file__), "..", "narratives", "face-shape", "20220113_012551.jpg")

BIMBO_BASE_PROMPT = """Use this face as the reference for the character's face shape, eyes, lips, and expression.

Create a manhwa/Korean webtoon style character portrait:

CHARACTER: Young woman AI hologram companion named Bimbo
- Face: Keep the exact face shape, eye shape, lip shape from reference
- Expression: Warm, playful, slight knowing smirk
- Hair: Long, straight, flowing - gradient from deep purple at roots to cyan at tips
- Skin: Warm undertone with subtle luminous/holographic shimmer
- Style: Clean manhwa lineart, expressive eyes

HOLOGRAPHIC EFFECTS:
- Soft purple-cyan glow around edges of form
- Small floating geometric particles near her
- Subtle ethereal quality - she's made of light

Portrait shot, shoulders up, slight head tilt, white/light background.
Professional character design reference sheet quality."""

BIMBO_CASUAL_PROMPT = """Use this character reference to maintain face and hair consistency.

Same character in a different outfit and setting:

OUTFIT: Cozy futuristic casual
- Oversized soft lavender hoodie with subtle cyan tech-line accents
- Holographic choker that glows softly
- Headphones with purple-cyan lights (optional)

POSE: Relaxed, friendly wave or hand near face
EXPRESSION: Warm, welcoming smile
SETTING: Spaceship interior, stars visible through window, purple ambient lighting

Maintain the exact same face, hair color gradient (purple to cyan), and holographic glow effect.
Manhwa/Korean webtoon style, clean lines."""

BIMBO_KIMONO_PROMPT = """Use this character reference to maintain face and hair consistency.

Same character wearing a holographic kimono:

OUTFIT: Traditional kimono made of translucent holographic light
- Kimono silhouette but clearly made of energy/light, not fabric
- Purple base with cyan geometric patterns
- Edges dissolve into floating particles
- Cyan obi sash

POSE: Graceful, hands gently clasped
EXPRESSION: Gentle, serene smile
SETTING: Soft Japanese garden background with cherry blossoms

She's clearly a hologram/projection that doesn't belong to this era - ethereal and out of time.
Maintain exact same face and purple-cyan hair gradient.
Manhwa style, beautiful contrast between traditional silhouette and futuristic holographic material."""

BIMBO_DANGER_PROMPT = """Use this character reference to maintain face and hair consistency.

Same character in alert/protective mode:

APPEARANCE CHANGES:
- Hair flowing more dramatically, more intense cyan glow
- Expression serious, determined, protective
- Holographic effects intensified - more particles, slight glitch artifacts

OUTFIT: Sleek dark purple bodysuit with glowing cyan circuit patterns
POSE: Alert stance, one arm raised with holographic shield forming
SETTING: Dark background with red warning tones, sense of danger

She's worried about the player and ready to protect them.
Maintain exact same face but with serious/concerned expression.
Manhwa style, dramatic lighting, high contrast."""

BIMBO_TEACHING_PROMPT = """Use this character reference to maintain face and hair consistency.

Same character in teaching mode:

POSE: Gesturing toward floating holographic text/UI elements
- One hand pointing at floating Japanese characters
- Patient, encouraging expression
- Slight lean forward, engaged

EXPRESSION: Warm, patient, encouraging teacher energy
SETTING: Neutral background with holographic UI panels floating nearby

Include floating holographic text boxes and interface elements around her.
Maintain exact same face and purple-cyan hair.
Manhwa style, educational but warm mood."""


# ============================================================
# LOCATION PROMPTS
# ============================================================

LOCATION_PROMPTS = {
    "ship_observation": """Spaceship observation deck interior, science fiction setting.
Wide curved window showing stars and void of space.
Purple and cyan ambient lighting, soft glow.
Minimalist futuristic furniture.
Atmosphere: contemplative, quiet, liminal space between worlds.
Manhwa/digital art style, detailed background.""",

    "beach_dawn": """Japanese beach at dawn after a storm.
Bruised sky - purple and amber colors, sun just clearing mountains.
Waves washing on sand, debris from shipwreck scattered.
Moody, dangerous atmosphere.
Manhwa style background art, cinematic composition.""",

    "village_day": """Small Japanese village, Sengoku period (1600s).
Cluster of wooden buildings around muddy central path.
Smoke rising from cook fires.
Farmers going about daily work - carrying water, repairing nets.
Atmosphere: fragile normalcy, wary peace.
Manhwa style, warm but muted colors.""",

    "village_samurai": """Same Japanese village but with tension.
Samurai on horseback have arrived.
Villagers clearing the path, mothers pulling children away.
Atmosphere: fear, danger, oppression.
Manhwa style, more dramatic shadows and contrast.""",

    "forest_road": """Forest road in feudal Japan, cedar trees thick on both sides.
Mountain path with switchbacks visible.
Rain falling, mist in the air.
Atmosphere: journey, isolation, nature's indifference.
Manhwa style, moody greens and grays.""",

    "castle_exterior": """Japanese castle on a hill above a river, Sengoku period.
Gray stone walls rising from mist.
Not large but solid, permanent - a statement of power.
Late afternoon light.
Atmosphere: power, permanence, new chapter.
Manhwa style, detailed architecture.""",

    "castle_interior": """Interior of Japanese castle, tatami room.
Sliding paper screens (shoji), minimal furnishing.
Single window overlooking valley.
Futon in corner.
Atmosphere: elegant but sparse, comfortable prison.
Manhwa style, clean lines, warm wood tones.""",

    "garden_koi": """Small Japanese garden within castle grounds.
Koi pond with gold and white fish.
Carefully arranged rocks, single bent pine tree.
Stone bench nearby.
Autumn colors, leaves falling.
Atmosphere: peace, infinity in small space, contemplation.
Manhwa style, beautiful detailed nature.""",

    "temple_exterior": """Small Buddhist temple in the mountains.
Single weathered wooden building with mossy roof.
Bell hanging in wooden frame outside.
Surrounded by forest, mist.
Atmosphere: sanctuary, simplicity, timelessness.
Manhwa style, peaceful earthy tones.""",

    "sekigahara_sunset": """Sekigahara battlefield, months after the battle.
Wide valley between mountains.
Trampled grass slowly recovering, remnants of war.
Sunset casting amber light across the field.
Atmosphere: ghosts, remembrance, the weight of history.
Manhwa style, epic wide shot, melancholy beauty.""",
}


# ============================================================
# BATCH GENERATION HELPERS
# ============================================================

async def generate_all_bimbo_refs(face_ref: str = None, force: bool = False) -> list[dict]:
    """Generate all Bimbo character references."""
    if face_ref is None:
        face_ref = FACE_REFERENCE

    results = []

    # Base reference (uses face photo)
    print("Generating Bimbo base reference...")
    result = await generate_character_ref("bimbo", BIMBO_BASE_PROMPT, face_ref, force)
    results.append(result)
    print(f"  -> {result['path']} (cached: {result['cached']})")

    # Variants (use base reference)
    variants = [
        ("casual", BIMBO_CASUAL_PROMPT),
        ("kimono", BIMBO_KIMONO_PROMPT),
        ("danger", BIMBO_DANGER_PROMPT),
        ("teaching", BIMBO_TEACHING_PROMPT),
    ]

    for variant_name, prompt in variants:
        print(f"Generating Bimbo {variant_name}...")
        result = await generate_character_variant("bimbo", variant_name, prompt, force)
        results.append(result)
        print(f"  -> {result['path']} (cached: {result['cached']})")

    return results


async def generate_all_location_refs(force: bool = False) -> list[dict]:
    """Generate all location reference images."""
    results = []

    for loc_id, prompt in LOCATION_PROMPTS.items():
        print(f"Generating location: {loc_id}...")
        result = await generate_location_ref(loc_id, prompt, force)
        results.append(result)
        print(f"  -> {result['path']} (cached: {result['cached']})")

    return results


# CLI test
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) > 1 and sys.argv[1] == "bimbo":
            results = await generate_all_bimbo_refs(force="--force" in sys.argv)
            print(f"\nGenerated {len(results)} Bimbo images")
        elif len(sys.argv) > 1 and sys.argv[1] == "locations":
            results = await generate_all_location_refs(force="--force" in sys.argv)
            print(f"\nGenerated {len(results)} location images")
        else:
            print("Usage: python image_gen_google.py [bimbo|locations] [--force]")

    asyncio.run(main())
