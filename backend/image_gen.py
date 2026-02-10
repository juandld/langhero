"""
AI Scene Image Generation via DALL-E 3.

Generates and caches manga/webtoon-style scene images for scenarios and panels.
Supports multiple art styles: manhwa, manga, ghibli, dramatic, minimal.
"""

import os
import hashlib
import requests
from typing import Optional, TYPE_CHECKING
from openai import OpenAI
import config

if TYPE_CHECKING:
    from visual_styles import Panel, ArtStyle

# Cache directory for generated images
IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache")

# OpenAI client (initialized lazily)
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = config.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _client = OpenAI(api_key=api_key)
    return _client


def _ensure_cache_dir() -> None:
    """Ensure the image cache directory exists."""
    os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)


def _cache_key(scenario: dict) -> str:
    """Generate a stable cache key for a scenario."""
    setting = scenario.get("setting", "")
    description = scenario.get("description", "")
    style = scenario.get("art_style", "manhwa")
    content = f"{style}|{setting}|{description}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _cache_key_for_panel(panel_id: str, scene_description: str, art_style: str) -> str:
    """Generate a stable cache key for a panel."""
    content = f"{art_style}|{panel_id}|{scene_description}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _build_prompt(scenario: dict) -> str:
    """Build a DALL-E prompt for the scenario (legacy Ghibli style)."""
    setting = scenario.get("setting", "A warm Japanese street scene")
    description = scenario.get("description", "")

    return f"""Create a warm, inviting anime-style illustration for a language learning app.

Scene setting: {setting}
Context: {description}

Style requirements:
- Studio Ghibli inspired aesthetic
- Soft, warm color palette with gentle lighting
- Welcoming and cozy atmosphere
- No text, speech bubbles, or written words
- Character should be friendly and approachable
- Simple, clean composition
- Suitable for children and beginners

The image should evoke the feeling of a gentle, encouraging learning environment."""


def _build_panel_prompt(panel: "Panel", context: str = "") -> str:
    """Build a DALL-E prompt for a panel using visual_styles."""
    from visual_styles import build_image_prompt
    return build_image_prompt(panel, context)


def get_cached_image(scenario: dict) -> Optional[str]:
    """Check if an image is cached for this scenario.

    Returns the relative URL path if cached, None otherwise.
    """
    _ensure_cache_dir()
    cache_key = _cache_key(scenario)
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.png")

    if os.path.exists(cache_path):
        return f"/images/generated/{cache_key}.png"
    return None


def generate_scene_image(scenario: dict, force: bool = False) -> dict:
    """Generate and cache a scene image via DALL-E 3.

    Args:
        scenario: Scenario dict with 'setting' and 'description' fields
        force: If True, regenerate even if cached

    Returns:
        {
            "url": "/images/generated/abc123.png",
            "cached": True/False,
            "cache_key": "abc123"
        }
    """
    _ensure_cache_dir()
    cache_key = _cache_key(scenario)
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.png")

    # Check cache first
    if not force and os.path.exists(cache_path):
        return {
            "url": f"/images/generated/{cache_key}.png",
            "cached": True,
            "cache_key": cache_key,
        }

    # Generate new image
    client = _get_client()
    prompt = _build_prompt(scenario)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # Download and save to cache
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        with open(cache_path, "wb") as f:
            f.write(img_response.content)

        return {
            "url": f"/images/generated/{cache_key}.png",
            "cached": False,
            "cache_key": cache_key,
        }

    except Exception as e:
        raise RuntimeError(f"Image generation failed: {e}")


def list_cached_images() -> list[dict]:
    """List all cached images.

    Returns list of {cache_key, url, path}
    """
    _ensure_cache_dir()
    images = []

    for filename in os.listdir(IMAGE_CACHE_DIR):
        if filename.endswith(".png"):
            cache_key = filename[:-4]  # Remove .png
            images.append({
                "cache_key": cache_key,
                "url": f"/images/generated/{cache_key}.png",
                "path": os.path.join(IMAGE_CACHE_DIR, filename),
            })

    return images


def delete_cached_image(cache_key: str) -> bool:
    """Delete a cached image by its cache key.

    Returns True if deleted, False if not found.
    """
    _ensure_cache_dir()
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.png")

    if os.path.exists(cache_path):
        os.remove(cache_path)
        return True
    return False


def generate_panel_image(
    panel: "Panel",
    context: str = "",
    force: bool = False,
    size: str = "1024x1024",
) -> dict:
    """Generate and cache an image for a visual panel.

    Args:
        panel: Panel object from visual_styles
        context: Additional story context
        force: Regenerate even if cached
        size: Image size ("1024x1024", "1792x1024" for wide, "1024x1792" for tall)

    Returns:
        {
            "url": "/images/generated/abc123.png",
            "cached": True/False,
            "cache_key": "abc123",
            "panel_id": "panel_1"
        }
    """
    from visual_styles import PanelType

    _ensure_cache_dir()

    # Determine size based on panel type
    if panel.type == PanelType.WIDE:
        size = "1792x1024"
    elif panel.type == PanelType.TALL:
        size = "1024x1792"
    else:
        size = "1024x1024"

    cache_key = _cache_key_for_panel(
        panel.id,
        panel.scene_description,
        panel.art_style.value
    )
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{cache_key}.png")

    # Check cache first
    if not force and os.path.exists(cache_path):
        return {
            "url": f"/images/generated/{cache_key}.png",
            "cached": True,
            "cache_key": cache_key,
            "panel_id": panel.id,
        }

    # Generate new image
    client = _get_client()
    prompt = _build_panel_prompt(panel, context)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # Download and save to cache
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        with open(cache_path, "wb") as f:
            f.write(img_response.content)

        return {
            "url": f"/images/generated/{cache_key}.png",
            "cached": False,
            "cache_key": cache_key,
            "panel_id": panel.id,
        }

    except Exception as e:
        raise RuntimeError(f"Panel image generation failed: {e}")


def generate_sequence_images(
    sequence: "VisualSequence",
    context: str = "",
    force: bool = False,
    skip_existing: bool = True,
) -> list[dict]:
    """Generate images for all panels in a sequence.

    Args:
        sequence: VisualSequence object
        context: Story context for prompts
        force: Regenerate all images
        skip_existing: Skip panels that already have image_url set

    Returns:
        List of generation results for each panel
    """
    from visual_styles import VisualSequence

    results = []

    for panel in sequence.panels:
        # Skip if already has image and skip_existing is True
        if skip_existing and panel.image_url and not force:
            results.append({
                "url": panel.image_url,
                "cached": True,
                "cache_key": None,
                "panel_id": panel.id,
                "skipped": True,
            })
            continue

        try:
            result = generate_panel_image(panel, context, force)
            panel.image_url = result["url"]  # Update panel with URL
            results.append(result)
        except Exception as e:
            results.append({
                "url": None,
                "cached": False,
                "cache_key": None,
                "panel_id": panel.id,
                "error": str(e),
            })

    return results
