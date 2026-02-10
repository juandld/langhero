"""
Constraint-Based Prompt Builder for Manhwa Panel Generation.

Follows the Nano Banana Pro guide structure:
- WORK SURFACE
- LAYOUT
- COMPONENTS
- STYLE
- CONSTRAINTS
- SOURCE MATERIAL
- INTERPRETATION
"""

import os
from typing import Optional
from dataclasses import dataclass, field

# Base paths
IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache")
CHARACTER_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "characters")
LOCATION_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "locations")


# ============================================================
# REFERENCE REGISTRY
# ============================================================

@dataclass
class CharacterRef:
    """Character reference with all variants."""
    id: str
    name: str
    description: str
    base_path: str
    variants: dict = field(default_factory=dict)

    def get_path(self, variant: str = None) -> str:
        """Get path to reference image."""
        if variant and variant in self.variants:
            return self.variants[variant]
        return self.base_path

    def exists(self, variant: str = None) -> bool:
        """Check if reference exists."""
        return os.path.exists(self.get_path(variant))


@dataclass
class LocationRef:
    """Location reference."""
    id: str
    name: str
    description: str
    path: str
    mood: str = "neutral"
    time_of_day: str = "day"

    def exists(self) -> bool:
        return os.path.exists(self.path)


# Character registry
CHARACTERS = {
    "bimbo": CharacterRef(
        id="bimbo",
        name="Bimbo",
        description="Young woman AI hologram companion. Long hair with purple-to-cyan gradient. Warm expression. Holographic glow with floating particles. Manhwa style.",
        base_path=os.path.join(CHARACTER_REF_DIR, "bimbo.png"),
        variants={
            "casual": os.path.join(CHARACTER_REF_DIR, "bimbo_casual.png"),
            "danger": os.path.join(CHARACTER_REF_DIR, "bimbo_danger.png"),
            "kimono": os.path.join(CHARACTER_REF_DIR, "bimbo_kimono.png"),
            "teaching": os.path.join(CHARACTER_REF_DIR, "bimbo_teaching.png"),
        }
    ),
    "hana": CharacterRef(
        id="hana",
        name="Hana",
        description="Elderly Japanese village woman. Weathered face with deep wrinkles. Gray hair pulled back. Sharp evaluating eyes. Simple peasant clothes. Sengoku period (1600s Japan).",
        base_path=os.path.join(CHARACTER_REF_DIR, "hana.png"),
    ),
    "kenji": CharacterRef(
        id="kenji",
        name="Kenji",
        description="Young Japanese farmer. Wary but curious expression. Simple work clothes. Muscular from farm labor. Sengoku period.",
        base_path=os.path.join(CHARACTER_REF_DIR, "kenji.png"),
    ),
    "mariko": CharacterRef(
        id="mariko",
        name="Mariko",
        description="Elegant Japanese noblewoman. Refined features, composed expression. Elaborate kimono. Hair pinned with ornaments. Graceful bearing. Sengoku period.",
        base_path=os.path.join(CHARACTER_REF_DIR, "mariko.png"),
    ),
    "samurai": CharacterRef(
        id="samurai",
        name="Samurai (Hostile)",
        description="Japanese samurai warrior. Stern threatening expression. Traditional armor or formal samurai attire. Hand near sword. Authority and danger. Sengoku period.",
        base_path=os.path.join(CHARACTER_REF_DIR, "samurai_hostile.png"),
    ),
    "eikou": CharacterRef(
        id="eikou",
        name="Eikou",
        description="Buddhist monk. Shaved head, calm wise expression. Simple monk robes. Weathered but peaceful face. Sengoku period.",
        base_path=os.path.join(CHARACTER_REF_DIR, "eikou.png"),
    ),
    "takeshi": CharacterRef(
        id="takeshi",
        name="Takeshi",
        description="Young samurai, more refined than hostile samurai. Intelligent eyes, measured expression. Formal attire. Sengoku period.",
        base_path=os.path.join(CHARACTER_REF_DIR, "takeshi.png"),
    ),
}

# Location registry
LOCATIONS = {
    "ship_observation": LocationRef(
        id="ship_observation",
        name="Spaceship Observation Deck",
        description="Spaceship observation deck interior. Wide curved window showing stars and void of space. Purple and cyan ambient lighting. Minimalist futuristic furniture.",
        path=os.path.join(LOCATION_REF_DIR, "ship_observation.png"),
        mood="contemplative",
        time_of_day="night",
    ),
    "beach_dawn": LocationRef(
        id="beach_dawn",
        name="Japanese Beach at Dawn",
        description="Japanese beach at dawn after a storm. Bruised sky with purple and amber colors. Waves washing on sand. Shipwreck debris scattered.",
        path=os.path.join(LOCATION_REF_DIR, "beach_dawn.png"),
        mood="dangerous",
        time_of_day="dawn",
    ),
    "village_day": LocationRef(
        id="village_day",
        name="Japanese Village",
        description="Small Japanese village, Sengoku period. Cluster of wooden buildings around muddy central path. Smoke from cook fires. Farmers at work.",
        path=os.path.join(LOCATION_REF_DIR, "village_day.png"),
        mood="peaceful",
        time_of_day="day",
    ),
    "village_samurai": LocationRef(
        id="village_samurai",
        name="Village with Samurai",
        description="Japanese village with tension. Samurai have arrived. Villagers clearing path, fearful. Atmosphere of danger and oppression.",
        path=os.path.join(LOCATION_REF_DIR, "village_samurai.png"),
        mood="tense",
        time_of_day="day",
    ),
    "forest_road": LocationRef(
        id="forest_road",
        name="Forest Road",
        description="Forest road in feudal Japan. Cedar trees thick on both sides. Mountain path with switchbacks. Rain and mist.",
        path=os.path.join(LOCATION_REF_DIR, "forest_road.png"),
        mood="isolated",
        time_of_day="overcast",
    ),
    "castle_exterior": LocationRef(
        id="castle_exterior",
        name="Castle Exterior",
        description="Japanese castle on a hill above a river. Gray stone walls rising from mist. Solid and permanent. Statement of power.",
        path=os.path.join(LOCATION_REF_DIR, "castle_exterior.png"),
        mood="imposing",
        time_of_day="afternoon",
    ),
    "castle_interior": LocationRef(
        id="castle_interior",
        name="Castle Interior",
        description="Interior of Japanese castle, tatami room. Sliding paper screens (shoji). Minimal furnishing. Window overlooking valley.",
        path=os.path.join(LOCATION_REF_DIR, "castle_interior.png"),
        mood="elegant",
        time_of_day="day",
    ),
    "garden_koi": LocationRef(
        id="garden_koi",
        name="Koi Garden",
        description="Small Japanese garden within castle grounds. Koi pond with gold and white fish. Arranged rocks, bent pine tree. Autumn colors.",
        path=os.path.join(LOCATION_REF_DIR, "garden_koi.png"),
        mood="peaceful",
        time_of_day="afternoon",
    ),
    "temple_exterior": LocationRef(
        id="temple_exterior",
        name="Mountain Temple",
        description="Small Buddhist temple in the mountains. Weathered wooden building with mossy roof. Bell in wooden frame. Surrounded by forest and mist.",
        path=os.path.join(LOCATION_REF_DIR, "temple_exterior.png"),
        mood="serene",
        time_of_day="morning",
    ),
    "sekigahara_sunset": LocationRef(
        id="sekigahara_sunset",
        name="Sekigahara Battlefield",
        description="Sekigahara battlefield, months after the battle. Wide valley between mountains. Trampled grass recovering. Remnants of war. Sunset light.",
        path=os.path.join(LOCATION_REF_DIR, "sekigahara_sunset.png"),
        mood="melancholic",
        time_of_day="sunset",
    ),
}


# ============================================================
# PANEL TYPES
# ============================================================

PANEL_TYPES = {
    "establishing": {
        "description": "Wide establishing shot showing location and atmosphere",
        "aspect": "wide",
        "camera": "Wide establishing shot, panoramic view",
        "focus": "Environment and atmosphere",
    },
    "dialogue": {
        "description": "Character conversation moment",
        "aspect": "square",
        "camera": "Medium shot, character focus",
        "focus": "Character expressions and interaction",
    },
    "action": {
        "description": "Dynamic movement or action",
        "aspect": "tall",
        "camera": "Dynamic angle with motion",
        "focus": "Movement, impact, energy",
    },
    "time_freeze": {
        "description": "Bimbo's time freeze teaching moment",
        "aspect": "tall",
        "camera": "Mixed - frozen world with Bimbo in motion",
        "focus": "Contrast between frozen and active elements",
    },
    "emotional": {
        "description": "Close-up emotional beat",
        "aspect": "square",
        "camera": "Close-up on face or hands",
        "focus": "Emotion, subtle expression",
    },
    "transition": {
        "description": "Scene transition or passage of time",
        "aspect": "wide",
        "camera": "Environmental or symbolic shot",
        "focus": "Mood shift, new context",
    },
    "pov": {
        "description": "First-person point of view",
        "aspect": "wide",
        "camera": "POV shot, player's perspective",
        "focus": "Immersion, what player sees",
    },
    "reaction": {
        "description": "Character reaction shot",
        "aspect": "square",
        "camera": "Medium or close shot on reacting character",
        "focus": "Surprise, fear, understanding, relief",
    },
}


# ============================================================
# STYLE DEFINITIONS
# ============================================================

BASE_STYLE = """Korean manhwa/webtoon aesthetic. Clean linework with confident strokes.
Soft cel-shading with defined shadows. Full color, slightly desaturated palette.
Expressive eyes, elegant character proportions. Professional quality."""

HOLOGRAPHIC_STYLE = """Futuristic holographic effects. Purple and cyan color palette.
Glowing edges, floating particles. Clean sci-fi aesthetic mixed with manhwa style."""

CINEMATIC_STYLE = """Cinematic composition. Dramatic lighting with strong shadows.
Period-accurate Sengoku Japan (1600s). Earth tones, muted colors.
Historical manhwa aesthetic. No modern elements."""

TIME_FREEZE_STYLE = """Magical time freeze effect. Frozen elements have blue desaturated tint.
Bimbo is the only element in full warm color with glow.
Suspended motion - waves frozen mid-curl, people frozen like statues.
Surreal but clear visual distinction between frozen and active."""


# ============================================================
# CONSTRAINTS
# ============================================================

UNIVERSAL_CONSTRAINTS = """
- NO TEXT, SPEECH BUBBLES, OR WRITTEN WORDS IN THE IMAGE
- No modern items in historical scenes (no glasses, watches, etc.)
- Maintain character design consistency with provided references
- Clean panel composition suitable for vertical webtoon reading
- No floating portraits or surreal additions unless specified
- No AI-generated text artifacts
- NEVER show the player character - all scenes are POV (first-person perspective)
- Player's hands or arms may be visible when contextually appropriate (defensive gesture, pointing)
- The viewer IS the protagonist - frame shots as if looking through their eyes
"""

HISTORICAL_CONSTRAINTS = """
- Period-accurate Sengoku Japan (1600s)
- No anachronistic elements
- Traditional Japanese clothing and architecture
- Realistic human anatomy and proportions
"""

HOLOGRAPHIC_CONSTRAINTS = """
- Clear distinction between holographic and physical elements
- Bimbo always has her signature purple-cyan hair gradient
- Holographic glow and particle effects on AI characters
- Futuristic but warm, not cold/clinical
"""


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_panel_prompt(
    panel_type: str,
    scene_description: str,
    characters: list[str] = None,
    location: str = None,
    mood: str = None,
    is_holographic: bool = False,
    is_time_freeze: bool = False,
    additional_constraints: str = None,
    interpretation: str = None,
) -> dict:
    """
    Build a constraint-based prompt for panel generation.

    Args:
        panel_type: Type of panel (establishing, dialogue, action, etc.)
        scene_description: What's happening in the scene
        characters: List of character IDs to include
        location: Location ID for background reference
        mood: Emotional mood of the scene
        is_holographic: True if scene is in holographic/ship setting
        is_time_freeze: True if this is a time freeze moment
        additional_constraints: Extra constraints for this specific panel
        interpretation: Emotional/thematic guidance

    Returns:
        dict with 'prompt' string and 'reference_images' list of paths
    """

    panel_config = PANEL_TYPES.get(panel_type, PANEL_TYPES["dialogue"])
    reference_images = []

    # Build WORK SURFACE
    aspect_map = {"wide": "16:9", "square": "1:1", "tall": "9:16"}
    aspect = panel_config["aspect"]
    work_surface = f"Create a single manhwa panel. {aspect_map[aspect]} aspect ratio, {aspect} composition."

    # Build LAYOUT
    layout = f"{panel_config['camera']}. {panel_config['description']}."

    # Build COMPONENTS
    components = []

    # Add characters
    if characters:
        for char_id in characters:
            char = CHARACTERS.get(char_id)
            if char:
                # Choose variant based on context
                variant = None
                if char_id == "bimbo":
                    if is_time_freeze:
                        variant = "teaching"
                    elif is_holographic:
                        variant = "casual"

                if char.exists(variant):
                    reference_images.append(char.get_path(variant))

                components.append(f"• {char.name}: {char.description}")

    # Add location
    if location:
        loc = LOCATIONS.get(location)
        if loc:
            if loc.exists():
                reference_images.append(loc.path)
            components.append(f"• Background: {loc.description}")
            if not mood:
                mood = loc.mood

    components_str = "\n".join(components) if components else "• Scene elements as described"

    # Build STYLE
    if is_holographic:
        style = f"{BASE_STYLE}\n{HOLOGRAPHIC_STYLE}"
    elif is_time_freeze:
        style = f"{BASE_STYLE}\n{TIME_FREEZE_STYLE}"
    else:
        style = f"{BASE_STYLE}\n{CINEMATIC_STYLE}"

    # Build CONSTRAINTS
    constraints = UNIVERSAL_CONSTRAINTS
    if not is_holographic:
        constraints += HISTORICAL_CONSTRAINTS
    if is_holographic or is_time_freeze:
        constraints += HOLOGRAPHIC_CONSTRAINTS
    if additional_constraints:
        constraints += f"\n{additional_constraints}"

    # Build SOURCE MATERIAL
    source_material = scene_description

    # Build INTERPRETATION
    if not interpretation:
        mood_interpretations = {
            "contemplative": "Convey quiet reflection, the weight of solitude, peace in stillness.",
            "dangerous": "Convey threat, survival instinct, beautiful danger.",
            "peaceful": "Convey calm normalcy, fragile peace, everyday life.",
            "tense": "Convey fear, oppression, held breath.",
            "isolated": "Convey loneliness, journey into unknown, nature's indifference.",
            "imposing": "Convey power, permanence, new chapter beginning.",
            "elegant": "Convey refined beauty, comfortable captivity, gilded cage.",
            "serene": "Convey sanctuary, timelessness, spiritual peace.",
            "melancholic": "Convey ghosts of the past, remembrance, the weight of history.",
            "neutral": "Convey the scene naturally with appropriate emotional weight.",
        }
        interpretation = mood_interpretations.get(mood, mood_interpretations["neutral"])

    # Assemble final prompt
    prompt = f"""WORK SURFACE: {work_surface}

LAYOUT: {layout}

COMPONENTS:
{components_str}

STYLE: {style}

CONSTRAINTS:
{constraints}

SOURCE MATERIAL:
{source_material}

INTERPRETATION:
{interpretation}"""

    return {
        "prompt": prompt,
        "reference_images": reference_images,
        "aspect": aspect,
        "panel_type": panel_type,
    }


def build_time_freeze_prompt(
    scene_description: str,
    frozen_characters: list[str] = None,
    location: str = None,
    teaching_topic: str = None,
) -> dict:
    """
    Specialized builder for time freeze moments.

    Bimbo freezes time to teach the player.
    The world is frozen (blue tint, statues).
    Bimbo is the only thing in full color and motion.
    """

    frozen_desc = ""
    if frozen_characters:
        chars = [CHARACTERS.get(c) for c in frozen_characters if c in CHARACTERS]
        if chars:
            names = ", ".join([c.name for c in chars])
            frozen_desc = f"\n{names} frozen like statues, blue desaturated tint."

    enhanced_scene = f"""TIME FREEZE MOMENT.

The world is FROZEN:
- All motion suspended like a paused video
- Blue desaturated color filter on frozen elements
- Waves frozen mid-curl, people frozen mid-motion{frozen_desc}

ONLY Bimbo is ACTIVE:
- Full warm color (purple-cyan hair, glowing)
- In motion, gesturing, teaching
- Holographic particles floating around her

SCENE: {scene_description}"""

    if teaching_topic:
        enhanced_scene += f"\n\nBimbo is teaching about: {teaching_topic}"

    return build_panel_prompt(
        panel_type="time_freeze",
        scene_description=enhanced_scene,
        characters=["bimbo"],
        location=location,
        is_time_freeze=True,
        interpretation="Convey calm amidst chaos, learning within danger, Bimbo as guide and protector.",
    )


def build_establishing_prompt(
    location: str,
    scene_context: str = None,
    mood_override: str = None,
    include_figure: bool = False,
) -> dict:
    """
    Specialized builder for establishing shots.
    """

    loc = LOCATIONS.get(location)
    if not loc:
        raise ValueError(f"Unknown location: {location}")

    scene = loc.description
    if scene_context:
        scene = f"{scene}\n\n{scene_context}"

    if include_figure:
        scene += "\n\nA lone figure is small in frame, emphasizing the scale of the environment."

    return build_panel_prompt(
        panel_type="establishing",
        scene_description=scene,
        location=location,
        mood=mood_override or loc.mood,
        is_holographic=(location == "ship_observation"),
    )


def build_dialogue_prompt(
    characters: list[str],
    scene_description: str,
    location: str = None,
    speaker: str = None,
    emotion: str = None,
    is_holographic: bool = False,
) -> dict:
    """
    Specialized builder for dialogue panels.
    """

    enhanced_scene = scene_description

    if speaker and speaker in CHARACTERS:
        char = CHARACTERS[speaker]
        enhanced_scene += f"\n\n{char.name} is speaking. Focus on their expression."

    if emotion:
        enhanced_scene += f"\n\nEmotion: {emotion}"

    return build_panel_prompt(
        panel_type="dialogue",
        scene_description=enhanced_scene,
        characters=characters,
        location=location,
        is_holographic=is_holographic,
    )


def build_action_prompt(
    scene_description: str,
    characters: list[str] = None,
    location: str = None,
    action_type: str = "dynamic",
) -> dict:
    """
    Specialized builder for action panels.
    """

    action_modifiers = {
        "dynamic": "Dynamic motion, speed lines radiating from action.",
        "impact": "Impact moment, shockwave effects, debris flying.",
        "tension": "Frozen tension before action, held breath.",
        "chase": "Movement through space, blur effects, urgency.",
        "confrontation": "Face-off, two forces opposing, dramatic standoff.",
    }

    modifier = action_modifiers.get(action_type, action_modifiers["dynamic"])
    enhanced_scene = f"{scene_description}\n\n{modifier}"

    return build_panel_prompt(
        panel_type="action",
        scene_description=enhanced_scene,
        characters=characters,
        location=location,
        additional_constraints="Extreme dynamic composition. Motion blur where appropriate. High energy.",
    )


def build_emotional_prompt(
    character: str,
    emotion: str,
    scene_context: str = None,
    location: str = None,
) -> dict:
    """
    Specialized builder for emotional close-ups.
    """

    char = CHARACTERS.get(character)
    if not char:
        raise ValueError(f"Unknown character: {character}")

    emotion_guides = {
        "fear": "Eyes wide, trembling, pale complexion.",
        "determination": "Set jaw, focused eyes, inner fire.",
        "sadness": "Downcast eyes, subtle tears, weight of sorrow.",
        "surprise": "Wide eyes, parted lips, sudden realization.",
        "relief": "Softening expression, exhale, tension releasing.",
        "anger": "Narrowed eyes, clenched jaw, barely contained fury.",
        "hope": "Eyes lifting, slight smile forming, dawn of possibility.",
        "confusion": "Furrowed brow, searching eyes, trying to understand.",
    }

    emotion_detail = emotion_guides.get(emotion, f"Expressing {emotion}.")

    scene = f"Close-up on {char.name}'s face.\n{char.description}\n\nEmotion: {emotion_detail}"
    if scene_context:
        scene += f"\n\nContext: {scene_context}"

    return build_panel_prompt(
        panel_type="emotional",
        scene_description=scene,
        characters=[character],
        location=location,
        interpretation=f"Convey {emotion} through subtle facial expression. Let the viewer feel what the character feels.",
    )


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_character_refs(character_ids: list[str]) -> list[str]:
    """Get paths to character reference images."""
    paths = []
    for char_id in character_ids:
        char = CHARACTERS.get(char_id)
        if char and char.exists():
            paths.append(char.base_path)
    return paths


def get_location_ref(location_id: str) -> Optional[str]:
    """Get path to location reference image."""
    loc = LOCATIONS.get(location_id)
    if loc and loc.exists():
        return loc.path
    return None


def list_available_characters() -> list[str]:
    """List all character IDs with existing references."""
    return [cid for cid, char in CHARACTERS.items() if char.exists()]


def list_available_locations() -> list[str]:
    """List all location IDs with existing references."""
    return [lid for lid, loc in LOCATIONS.items() if loc.exists()]


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=== Available Characters ===")
    for cid in list_available_characters():
        char = CHARACTERS[cid]
        print(f"  {cid}: {char.name}")
        for variant in char.variants:
            if char.exists(variant):
                print(f"    - {variant}")

    print("\n=== Available Locations ===")
    for lid in list_available_locations():
        loc = LOCATIONS[lid]
        print(f"  {lid}: {loc.name} ({loc.mood})")

    print("\n=== Test Prompt: Time Freeze ===")
    result = build_time_freeze_prompt(
        scene_description="Beach scene. Farmers approaching with farming tools raised. Waves crashing.",
        frozen_characters=["hana"],
        location="beach_dawn",
        teaching_topic="How to say 'I am a castaway' in Japanese",
    )
    print(result["prompt"][:500] + "...")
    print(f"\nReferences: {result['reference_images']}")
