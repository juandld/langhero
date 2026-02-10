"""
Story Manifest System - Tracks characters, locations, and their appearances.

Ensures character consistency by:
1. Defining all characters (named + recurring unnamed) with references
2. Tracking which characters appear in each panel
3. Always including relevant references during generation
"""

import os
from dataclasses import dataclass, field
from typing import Optional

# Paths
IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache")
CHARACTER_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "characters")
LOCATION_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "locations")


@dataclass
class Character:
    """Character definition with visual consistency info."""
    id: str
    name: str
    description: str  # Detailed visual description for prompts
    reference_path: Optional[str] = None
    variants: dict = field(default_factory=dict)

    def get_ref_path(self, variant: str = None) -> Optional[str]:
        if variant and variant in self.variants:
            path = self.variants[variant]
        else:
            path = self.reference_path
        return path if path and os.path.exists(path) else None

    def prompt_description(self) -> str:
        """Get description formatted for prompts."""
        return f"{self.name}: {self.description}"


@dataclass
class Location:
    """Location definition."""
    id: str
    name: str
    description: str
    reference_path: Optional[str] = None

    def get_ref_path(self) -> Optional[str]:
        return self.reference_path if self.reference_path and os.path.exists(self.reference_path) else None


@dataclass
class PanelSpec:
    """Panel specification with character/location tracking."""
    id: str
    chapter: str
    panel_type: str  # establishing, dialogue, action, time_freeze, emotional, pov
    description: str  # Scene description
    characters: list[str] = field(default_factory=list)  # Character IDs in this panel
    location: str = None
    speaker: str = None  # Who is speaking (for dialogue panels)
    mood: str = None
    is_time_freeze: bool = False
    is_holographic: bool = False
    additional_notes: str = None  # Extra prompt instructions


# ============================================================
# SHOGUN STORY MANIFEST
# ============================================================

SHOGUN_CHARACTERS = {
    # === MAIN CHARACTERS ===
    "bimbo": Character(
        id="bimbo",
        name="Bimbo",
        description="Young woman AI hologram. Long straight hair with purple-to-cyan gradient (purple at roots, cyan at tips). Warm friendly expression. Soft holographic glow emanating from her form. Floating particles trail behind her. Manhwa style with large expressive eyes.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "bimbo.png"),
        variants={
            "teaching": os.path.join(CHARACTER_REF_DIR, "bimbo_teaching.png"),
            "casual": os.path.join(CHARACTER_REF_DIR, "bimbo_casual.png"),
            "danger": os.path.join(CHARACTER_REF_DIR, "bimbo_danger.png"),
        }
    ),

    "hana": Character(
        id="hana",
        name="Hana",
        description="Elderly Japanese village woman, 60s. Deeply weathered face with prominent wrinkles around eyes and mouth. Gray hair pulled back tightly in a simple bun. Sharp intelligent eyes that miss nothing. Thin lips, strong jaw. Simple brown peasant clothes. Carries herself with quiet authority despite humble appearance.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "hana.png"),
    ),

    # === RECURRING UNNAMED CHARACTERS ===
    "farmer_hostile": Character(
        id="farmer_hostile",
        name="Hostile Farmer",
        description="Japanese farmer, 40s, the threat. Muscular from labor. Angry suspicious expression, teeth bared. Carries farming hoe as weapon. Simple roughspun clothes, bare feet. Tanned weathered skin. Short cropped black hair. He is the one who almost kills you.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "farmer_hostile.png"),
    ),

    "farmer_young": Character(
        id="farmer_young",
        name="Young Farmer",
        description="Young Japanese farmer, early 20s. Less aggressive than the hostile farmer, more curious than angry. Slim build. Simple peasant clothes. Black hair tied back. Uncertain expression - follows the group but hesitant about violence.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "farmer_young.png"),
    ),

    "farmer_old": Character(
        id="farmer_old",
        name="Old Farmer",
        description="Older Japanese farmer, 50s. Weathered but not as harsh as Hana. Cautious expression. Carries a wooden staff. Gray-streaked hair. Worn clothes patched many times. Hangs back from confrontation.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "farmer_old.png"),
    ),
}

SHOGUN_LOCATIONS = {
    "ship_observation": Location(
        id="ship_observation",
        name="Spaceship Observation Deck",
        description="Spaceship observation deck. Wide curved window showing infinite stars and void of space. Purple and cyan ambient lighting. Minimalist futuristic furniture. Contemplative atmosphere.",
        reference_path=os.path.join(LOCATION_REF_DIR, "ship_observation.png"),
    ),

    "beach_dawn": Location(
        id="beach_dawn",
        name="Japanese Beach at Dawn",
        description="Japanese beach at dawn after a storm. Bruised sky with purple and amber colors. Waves washing on sand. Shipwreck debris scattered. Mountains visible in distance. Dangerous beautiful atmosphere.",
        reference_path=os.path.join(LOCATION_REF_DIR, "beach_dawn.png"),
    ),

    "village_path": Location(
        id="village_path",
        name="Path to Village",
        description="Sandy path leading from beach toward small Japanese fishing village. Thatched roof buildings visible in distance. Dawn light. Mountains behind village.",
        reference_path=os.path.join(LOCATION_REF_DIR, "beach_dawn.png"),  # Reuse beach for now
    ),
}

# Panel specifications with character tracking
SHOGUN_PANELS = [
    # === PROLOGUE ===
    PanelSpec(
        id="pro_01_stars",
        chapter="prologue",
        panel_type="establishing",
        description="POV looking out through the curved observation window. The infinite void of space stretches before you. Stars drift like ash. You are alone with your thoughts.",
        characters=[],  # No characters - just environment
        location="ship_observation",
        mood="contemplative",
        is_holographic=True,
    ),

    PanelSpec(
        id="pro_02_bimbo_appears",
        chapter="prologue",
        panel_type="dialogue",
        description="POV looking at Bimbo floating before you. She looks directly at the viewer with gentle concern. Stars visible through the observation window behind her. She's speaking to YOU.",
        characters=["bimbo"],
        location="ship_observation",
        speaker="bimbo",
        mood="warm",
        is_holographic=True,
    ),

    PanelSpec(
        id="pro_03_decision",
        chapter="prologue",
        panel_type="emotional",
        description="Close-up on Bimbo's face. Her expression has shifted to serious concern. The stakes are being raised. She's about to offer something dangerous. Her eyes meet yours directly.",
        characters=["bimbo"],
        location="ship_observation",
        speaker="bimbo",
        mood="tense",
        is_holographic=True,
    ),

    # === CHAPTER 1: THE BEACH ===
    PanelSpec(
        id="ch1_01_wake",
        chapter="ch01",
        panel_type="pov",
        description="POV waking up on Japanese beach. Blurred edges suggesting disorientation. Your legs visible in foreground, waves washing over them. Bruised purple-amber sky, sun clearing mountains. Sand and shipwreck debris around you.",
        characters=[],  # No characters yet
        location="beach_dawn",
        mood="disoriented",
    ),

    PanelSpec(
        id="ch1_02_farmers_approach",
        chapter="ch01",
        panel_type="action",
        description="POV from ground looking up. Four figures approaching - farmers silhouetted against bruised sky. The hostile farmer in front with hoe raised like weapon. They loom large and threatening above you.",
        characters=["farmer_hostile", "farmer_young", "farmer_old", "hana"],
        location="beach_dawn",
        mood="threatening",
        additional_notes="Hostile farmer is most prominent, in front. Others behind him. Hana visible but not leading yet.",
    ),

    PanelSpec(
        id="ch1_03_time_freeze",
        chapter="ch01",
        panel_type="time_freeze",
        description="POV of the beach scene FROZEN. Ocean wave suspended mid-curl. The hostile farmer frozen mid-charge, hoe raised. Other farmers frozen behind him. Bimbo appears as the only thing in color and motion, gesturing calmly.",
        characters=["bimbo", "farmer_hostile", "farmer_young", "farmer_old", "hana"],
        location="beach_dawn",
        is_time_freeze=True,
        additional_notes="Frozen characters have blue desaturated tint. Only Bimbo is warm colored and moving.",
    ),

    PanelSpec(
        id="ch1_04_bimbo_teaches",
        chapter="ch01",
        panel_type="dialogue",
        description="POV looking at Bimbo in teaching mode. She faces you directly with patient encouraging expression. Holographic glow around her hands. Frozen beach scene softly visible in background (blue tint).",
        characters=["bimbo"],
        location="beach_dawn",
        speaker="bimbo",
        is_time_freeze=True,
        is_holographic=True,
        additional_notes="Background shows frozen scene with blue desaturated tint.",
    ),

    PanelSpec(
        id="ch1_05_time_resumes",
        chapter="ch01",
        panel_type="action",
        description="POV - The hostile farmer rushing directly AT YOU. Hoe raised high overhead, face contorted with aggression. Your hands visible at bottom of frame in desperate defensive gesture. Time has resumed - vivid colors, motion blur.",
        characters=["farmer_hostile"],
        location="beach_dawn",
        mood="terror",
        additional_notes="Extreme dynamic shot. Farmer coming straight at camera. Motion lines. Terror moment.",
    ),

    PanelSpec(
        id="ch1_06_speak",
        chapter="ch01",
        panel_type="dialogue",
        description="POV seeing the farmers react to your words. Your hands visible raised in surrender. The hostile farmer hesitating, hoe lowering slightly. Others' expressions shifting from threat to surprise/confusion.",
        characters=["farmer_hostile", "farmer_young", "farmer_old", "hana"],
        location="beach_dawn",
        mood="tense_hope",
        additional_notes="Focus on their changing expressions. The hostile farmer is key - his hesitation.",
    ),

    PanelSpec(
        id="ch1_07_hana_steps",
        chapter="ch01",
        panel_type="dialogue",
        description="POV - Hana steps forward from the group, now taking charge. She studies you with sharp evaluating eyes. The other farmers visible behind her, deferring to her. Dawn light illuminating her weathered face.",
        characters=["hana", "farmer_hostile", "farmer_young", "farmer_old"],
        location="beach_dawn",
        speaker="hana",
        mood="judgment",
        additional_notes="Hana is now the focus. Others have stepped back. She's the decision maker.",
    ),

    PanelSpec(
        id="ch1_08_freeze_doko",
        chapter="ch01",
        panel_type="time_freeze",
        description="POV - Beach frozen again. Hana frozen mid-speech directly facing you, mouth slightly open. Bimbo appears in your field of view, explaining urgently.",
        characters=["bimbo", "hana"],
        location="beach_dawn",
        speaker="bimbo",
        is_time_freeze=True,
        additional_notes="Hana frozen with blue tint. Bimbo warm and glowing.",
    ),

    PanelSpec(
        id="ch1_09_umi_kara",
        chapter="ch01",
        panel_type="dialogue",
        description="POV - Your arm visible at edge of frame, gesturing toward the ocean. Hana directly in front watching your gesture, understanding dawning on her weathered face. The tension is breaking.",
        characters=["hana"],
        location="beach_dawn",
        mood="hopeful",
        additional_notes="Focus on Hana's expression changing to understanding.",
    ),

    PanelSpec(
        id="ch1_10_kite",
        chapter="ch01",
        panel_type="establishing",
        description="POV following Hana. She walks ahead up the sandy path toward the village, glancing back and gesturing for you to follow. Village visible in distance. Dawn light warming the scene.",
        characters=["hana"],
        location="village_path",
        speaker="hana",
        mood="cautious_hope",
        additional_notes="Hana ahead on path, looking back at us. We are following her into the unknown.",
    ),
]


def get_panel_references(panel: PanelSpec, characters: dict, locations: dict) -> list[str]:
    """Get all reference image paths for a panel."""
    refs = []

    # Add character references
    for char_id in panel.characters:
        char = characters.get(char_id)
        if char:
            # Choose variant based on context
            variant = None
            if char_id == "bimbo":
                if panel.is_time_freeze:
                    variant = "teaching"
                elif panel.is_holographic:
                    variant = "casual"

            ref_path = char.get_ref_path(variant)
            if ref_path:
                refs.append(ref_path)

    # Add location reference
    if panel.location:
        loc = locations.get(panel.location)
        if loc:
            ref_path = loc.get_ref_path()
            if ref_path:
                refs.append(ref_path)

    return refs


def get_panel_character_descriptions(panel: PanelSpec, characters: dict) -> str:
    """Get formatted character descriptions for a panel's prompt."""
    descriptions = []
    for char_id in panel.characters:
        char = characters.get(char_id)
        if char:
            descriptions.append(f"• {char.prompt_description()}")
    return "\n".join(descriptions)


def check_missing_references(characters: dict, locations: dict) -> dict:
    """Check which references are missing and need to be generated."""
    missing = {"characters": [], "locations": []}

    for char_id, char in characters.items():
        if not char.get_ref_path():
            missing["characters"].append(char_id)

    for loc_id, loc in locations.items():
        if not loc.get_ref_path():
            missing["locations"].append(loc_id)

    return missing


# ============================================================
# GENERATION HELPERS
# ============================================================

def generate_missing_character_refs():
    """Generate prompts for missing character references."""
    from image_gen_google import generate_character_ref
    import asyncio

    missing = check_missing_references(SHOGUN_CHARACTERS, SHOGUN_LOCATIONS)

    if not missing["characters"]:
        print("All character references exist!")
        return

    print(f"Missing character references: {missing['characters']}")

    for char_id in missing["characters"]:
        char = SHOGUN_CHARACTERS[char_id]
        prompt = f"""Manhwa/Korean webtoon style character portrait.

{char.description}

Portrait shot, shoulders up, facing slightly toward camera.
Clean background. Professional character design reference quality.
Expressive manhwa eyes, clean linework, soft cel-shading.

NO TEXT IN IMAGE."""

        print(f"\nGenerating {char_id}...")
        print(f"Prompt: {prompt[:200]}...")

        result = asyncio.run(generate_character_ref(char_id, prompt, force=True))
        print(f"  -> {result['path']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        missing = check_missing_references(SHOGUN_CHARACTERS, SHOGUN_LOCATIONS)
        print("Missing references:")
        print(f"  Characters: {missing['characters']}")
        print(f"  Locations: {missing['locations']}")

    elif len(sys.argv) > 1 and sys.argv[1] == "generate":
        generate_missing_character_refs()

    else:
        print("Usage: python story_manifest.py [check|generate]")
        print("\nShogun Story Manifest:")
        print(f"  Characters: {len(SHOGUN_CHARACTERS)}")
        print(f"  Locations: {len(SHOGUN_LOCATIONS)}")
        print(f"  Panels: {len(SHOGUN_PANELS)}")

        print("\nCharacters:")
        for char_id, char in SHOGUN_CHARACTERS.items():
            has_ref = "✓" if char.get_ref_path() else "✗"
            print(f"  [{has_ref}] {char_id}: {char.name}")
