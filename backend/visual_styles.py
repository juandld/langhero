"""
Visual Style System for Manga/Webtoon-style Scene Generation.

Defines art styles, panel layouts, and visual effects for creating
immersive comic-style experiences from any narrative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ArtStyle(str, Enum):
    """Available art styles for scene generation."""
    MANHWA = "manhwa"      # Full color Korean webtoon (default)
    MANGA = "manga"        # Japanese manga style
    GHIBLI = "ghibli"      # Studio Ghibli warm aesthetic
    DRAMATIC = "dramatic"  # High contrast cinematic
    MINIMAL = "minimal"    # Simple, clean illustration


class PanelType(str, Enum):
    """Panel layout types for comic presentation."""
    FULL = "full"          # Full screen, immersive
    WIDE = "wide"          # Cinematic wide shot
    TALL = "tall"          # Vertical webtoon panel
    SPLIT = "split"        # Two panels side by side
    TRIPLE = "triple"      # Three panels
    IMPACT = "impact"      # Small dramatic burst
    TRANSITION = "transition"  # Scene transition (blur, fade)


class VisualEffect(str, Enum):
    """Overlay effects for dramatic moments."""
    NONE = "none"
    SPEED_LINES = "speed_lines"      # Action/movement
    IMPACT_BURST = "impact_burst"    # Dramatic moment
    RADIAL_ZOOM = "radial_zoom"      # Focus/surprise
    SCREEN_TONE = "screen_tone"      # Manga shading
    VIGNETTE = "vignette"            # Edge darkening
    FROZEN = "frozen"                # Time stop effect
    RAIN = "rain"                    # Weather overlay
    PARTICLES = "particles"          # Magical/ethereal


class Mood(str, Enum):
    """Scene mood for color/lighting."""
    WARM = "warm"
    COLD = "cold"
    TENSE = "tense"
    PEACEFUL = "peaceful"
    MYSTERIOUS = "mysterious"
    DRAMATIC = "dramatic"
    HOPEFUL = "hopeful"


@dataclass
class Panel:
    """A single panel in the visual sequence."""
    id: str
    type: PanelType = PanelType.FULL

    # Content
    scene_description: str = ""
    dialogue: Optional[str] = None
    dialogue_translation: Optional[str] = None
    speaker: Optional[str] = None

    # Visual
    art_style: ArtStyle = ArtStyle.MANHWA
    mood: Mood = Mood.WARM
    effects: List[VisualEffect] = field(default_factory=list)

    # Layout
    duration_ms: int = 3000  # How long to show (for auto-advance)
    transition: str = "fade"  # fade, slide, cut, zoom

    # Character
    character_expression: Optional[str] = None  # "angry", "surprised", etc.
    character_position: str = "center"  # left, center, right, none

    # Image generation
    image_prompt_override: Optional[str] = None  # Custom prompt if needed
    image_url: Optional[str] = None  # Generated/cached image URL


@dataclass
class VisualSequence:
    """A sequence of panels forming a scene or chapter."""
    id: str
    title: str = ""
    panels: List[Panel] = field(default_factory=list)
    default_style: ArtStyle = ArtStyle.MANHWA
    default_mood: Mood = Mood.WARM


# Style-specific prompt templates
STYLE_PROMPTS = {
    ArtStyle.MANHWA: """Create a full-color Korean webtoon (manhwa) style illustration.

Style requirements:
- Vibrant, rich colors with strong lighting
- Clean linework with subtle shading
- Dramatic composition and camera angles
- Expressive character designs
- Modern digital art aesthetic
- Vertical panel composition friendly
- High contrast for readability on mobile""",

    ArtStyle.MANGA: """Create a Japanese manga style illustration.

Style requirements:
- Black and white with screentone shading
- Dynamic linework with varying line weights
- Expressive speed lines and impact effects
- Classic manga panel composition
- Strong emotional expressions
- Clean backgrounds with selective detail""",

    ArtStyle.GHIBLI: """Create a Studio Ghibli inspired illustration.

Style requirements:
- Soft, warm color palette
- Painterly, watercolor-like textures
- Gentle, welcoming atmosphere
- Rich environmental detail
- Nostalgic, dreamlike quality
- Natural lighting with soft shadows""",

    ArtStyle.DRAMATIC: """Create a cinematic, dramatic illustration.

Style requirements:
- High contrast lighting (chiaroscuro)
- Intense, saturated colors
- Dynamic, tilted camera angles
- Film noir influenced shadows
- Tension and atmosphere
- Cinematic aspect ratio composition""",

    ArtStyle.MINIMAL: """Create a clean, minimal illustration.

Style requirements:
- Simple, flat color palette
- Clean vector-like linework
- Lots of negative space
- Focus on essential elements
- Modern, app-friendly aesthetic
- Easy to read on any device""",
}


# Mood-specific lighting/color adjustments
MOOD_PROMPTS = {
    Mood.WARM: "Warm golden lighting, sunset tones, welcoming atmosphere.",
    Mood.COLD: "Cool blue tones, overcast lighting, distant feeling.",
    Mood.TENSE: "High contrast, sharp shadows, uneasy atmosphere.",
    Mood.PEACEFUL: "Soft diffused light, pastel tones, serene feeling.",
    Mood.MYSTERIOUS: "Low light, deep shadows, fog or mist, enigmatic.",
    Mood.DRAMATIC: "Intense directional light, strong shadows, cinematic.",
    Mood.HOPEFUL: "Dawn light, warm rays breaking through, uplifting.",
}


# Effect descriptions for prompts
EFFECT_PROMPTS = {
    VisualEffect.SPEED_LINES: "with dynamic speed lines indicating motion",
    VisualEffect.IMPACT_BURST: "with impact burst effect at focal point",
    VisualEffect.RADIAL_ZOOM: "with radial zoom lines focusing on center",
    VisualEffect.SCREEN_TONE: "with manga-style screentone shading",
    VisualEffect.VIGNETTE: "with darkened edges creating focus",
    VisualEffect.FROZEN: "with desaturated colors and suspended particles",
    VisualEffect.RAIN: "with rain falling, wet reflections",
    VisualEffect.PARTICLES: "with floating particles or sparkles",
}


def build_image_prompt(panel: Panel, context: str = "") -> str:
    """Build a complete DALL-E prompt for a panel.

    Args:
        panel: The panel to generate an image for
        context: Additional story context

    Returns:
        Complete prompt string for image generation
    """
    if panel.image_prompt_override:
        return panel.image_prompt_override

    parts = []

    # Base style
    parts.append(STYLE_PROMPTS.get(panel.art_style, STYLE_PROMPTS[ArtStyle.MANHWA]))

    # Scene description
    if panel.scene_description:
        parts.append(f"\nScene: {panel.scene_description}")

    # Context
    if context:
        parts.append(f"\nContext: {context}")

    # Mood
    parts.append(f"\nMood: {MOOD_PROMPTS.get(panel.mood, MOOD_PROMPTS[Mood.WARM])}")

    # Effects
    effect_descs = [EFFECT_PROMPTS.get(e, "") for e in panel.effects if e != VisualEffect.NONE]
    if effect_descs:
        parts.append(f"\nEffects: {', '.join(effect_descs)}")

    # Character
    if panel.character_expression:
        parts.append(f"\nCharacter expression: {panel.character_expression}")

    # Technical requirements
    parts.append("""

Technical requirements:
- No text, speech bubbles, or written words in the image
- Composition should leave space for UI overlays
- High quality, detailed illustration
- Safe for all ages""")

    return "\n".join(parts)


# Pre-defined panel sequences for common narrative beats
# Using Unsplash images as fallbacks until AI-generated images are cached
NARRATIVE_TEMPLATES = {
    "intro_future": [
        Panel(
            id="future_1",
            type=PanelType.WIDE,
            scene_description="Sleek futuristic spaceship interior, viewport showing stars and nebula, soft ambient lighting",
            mood=Mood.PEACEFUL,
            art_style=ArtStyle.MANHWA,
            character_position="none",
            image_url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        ),
        Panel(
            id="future_2",
            type=PanelType.FULL,
            scene_description="Silhouette of person looking out at stars, contemplative pose, soft blue lighting from viewport",
            mood=Mood.MYSTERIOUS,
            art_style=ArtStyle.MANHWA,
            character_position="center",
            image_url="https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=1200&q=80",
        ),
        Panel(
            id="future_3",
            type=PanelType.FULL,
            scene_description="Glowing AI orb companion floating, warm purple light, friendly presence",
            mood=Mood.WARM,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.PARTICLES],
            image_url="https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?w=1200&q=80",
        ),
    ],

    "intro_hologram": [
        Panel(
            id="holo_1",
            type=PanelType.WIDE,
            scene_description="Holographic display showing feudal Japan map, blue projection light, futuristic UI elements",
            mood=Mood.MYSTERIOUS,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.PARTICLES],
            image_url="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=80",
        ),
        Panel(
            id="holo_2",
            type=PanelType.FULL,
            scene_description="Hologram close-up: samurai warriors, castle, cherry blossoms, feudal era Japan",
            mood=Mood.DRAMATIC,
            art_style=ArtStyle.MANHWA,
            image_url="https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=1200&q=80",
        ),
    ],

    "intro_drop": [
        Panel(
            id="drop_1",
            type=PanelType.FULL,
            scene_description="White flash, temporal vortex, swirling energy",
            mood=Mood.DRAMATIC,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.RADIAL_ZOOM, VisualEffect.PARTICLES],
            duration_ms=1000,
            image_url="https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1200&q=80",
        ),
        Panel(
            id="drop_2",
            type=PanelType.FULL,
            scene_description="Blur of motion, falling sensation, glimpses of stormy ocean",
            mood=Mood.TENSE,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.SPEED_LINES],
            duration_ms=800,
            image_url="https://images.unsplash.com/photo-1505142468610-359e7d316be0?w=1200&q=80",
        ),
    ],

    "intro_beach": [
        Panel(
            id="beach_1",
            type=PanelType.WIDE,
            scene_description="Stormy beach at night, shipwreck debris, rain, crashing waves, dark clouds",
            mood=Mood.TENSE,
            art_style=ArtStyle.DRAMATIC,
            effects=[VisualEffect.RAIN, VisualEffect.VIGNETTE],
            image_url="https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=1200&q=80",
        ),
        Panel(
            id="beach_2",
            type=PanelType.FULL,
            scene_description="Close-up: rough hands grabbing, blurred background, disoriented POV",
            mood=Mood.TENSE,
            art_style=ArtStyle.DRAMATIC,
            effects=[VisualEffect.VIGNETTE],
            image_url="https://images.unsplash.com/photo-1527525443983-6e60c75fff46?w=1200&q=80",
        ),
        Panel(
            id="beach_3",
            type=PanelType.IMPACT,
            scene_description="Samurai face close-up, rain-soaked, suspicious expression, torchlight, intense eyes",
            mood=Mood.TENSE,
            art_style=ArtStyle.DRAMATIC,
            character_expression="suspicious",
            effects=[VisualEffect.RAIN],
            image_url="https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?w=1200&q=80",
        ),
        Panel(
            id="beach_4",
            type=PanelType.IMPACT,
            scene_description="Katana blade close-up, gleaming in torchlight, pointed at viewer, threatening",
            mood=Mood.DRAMATIC,
            art_style=ArtStyle.DRAMATIC,
            effects=[VisualEffect.IMPACT_BURST],
            image_url="https://images.unsplash.com/photo-1555169062-013468b47731?w=1200&q=80",
        ),
    ],

    "time_freeze": [
        Panel(
            id="freeze_1",
            type=PanelType.FULL,
            scene_description="Same beach scene but frozen, rain suspended in air, desaturated colors, purple glow at edges",
            mood=Mood.MYSTERIOUS,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.FROZEN, VisualEffect.PARTICLES],
            image_url="https://images.unsplash.com/photo-1507400492013-162706c8c05e?w=1200&q=80",
        ),
        Panel(
            id="freeze_2",
            type=PanelType.FULL,
            scene_description="AI orb glowing warmly in frozen scene, only source of color, reassuring presence",
            mood=Mood.HOPEFUL,
            art_style=ArtStyle.MANHWA,
            effects=[VisualEffect.FROZEN, VisualEffect.PARTICLES],
            image_url="https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200&q=80",
        ),
    ],

    "success_moment": [
        Panel(
            id="success_1",
            type=PanelType.FULL,
            scene_description="Samurai's expression softening, blade lowering, surprise and respect in eyes",
            mood=Mood.HOPEFUL,
            art_style=ArtStyle.MANHWA,
            character_expression="surprised_respectful",
            image_url="https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=1200&q=80",
        ),
        Panel(
            id="success_2",
            type=PanelType.WIDE,
            scene_description="Beach scene, storm clearing, first light of dawn on horizon, sense of survival",
            mood=Mood.HOPEFUL,
            art_style=ArtStyle.MANHWA,
            image_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",
        ),
    ],
}


def get_intro_panels() -> List[Panel]:
    """Get the complete panel sequence for the intro."""
    panels = []
    for template_key in ["intro_future", "intro_hologram", "intro_drop", "intro_beach", "time_freeze", "success_moment"]:
        if template_key in NARRATIVE_TEMPLATES:
            panels.extend(NARRATIVE_TEMPLATES[template_key])
    return panels
