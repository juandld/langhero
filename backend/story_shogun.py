"""
SHOGUN STORY - Japan 1600, Sengoku Period

The player is a foreigner washed ashore, learning Japanese to survive.
Bimbo (AI companion) can freeze time to teach vocabulary.
"""

import os
import asyncio
from story_manifest import Character, Location, PanelSpec, get_panel_references
from image_gen_google import generate_character_ref, generate_location_ref

# Paths
IMAGE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache")
CHARACTER_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "characters")
LOCATION_REF_DIR = os.path.join(IMAGE_CACHE_DIR, "locations")


# ============================================================
# STORY METADATA
# ============================================================

STORY_ID = "shogun_test"
STORY_TITLE = "The Weight of Words"
STORY_SUBTITLE = "Shogun Era, Japan 1600"


# ============================================================
# CHARACTERS
# ============================================================

CHARACTERS = {
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

    # === CHARACTERS FOR LATER CHAPTERS ===
    "mariko": Character(
        id="mariko",
        name="Mariko",
        description="Elegant Japanese noblewoman. Refined features, composed expression. Elaborate kimono with subtle patterns. Hair pinned with ornaments. Graceful bearing. She speaks softly but commands attention. Sengoku period nobility.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "mariko.png"),
    ),

    "samurai": Character(
        id="samurai",
        name="Samurai (Hostile)",
        description="Japanese samurai warrior. Stern threatening expression. Traditional armor or formal samurai attire. Hand near sword. Authority and danger. Sengoku period.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "samurai_hostile.png"),
    ),

    "eikou": Character(
        id="eikou",
        name="Eikou",
        description="Buddhist monk. Shaved head, calm wise expression. Simple monk robes. Weathered but peaceful face. Sengoku period.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "eikou.png"),
    ),

    "takeshi": Character(
        id="takeshi",
        name="Takeshi",
        description="Young samurai, more refined than hostile samurai. Intelligent eyes, measured expression. Formal attire. Sengoku period.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "takeshi.png"),
    ),

    "kenji": Character(
        id="kenji",
        name="Kenji",
        description="Young Japanese farmer. Wary but curious expression. Simple work clothes. Muscular from farm labor. Sengoku period.",
        reference_path=os.path.join(CHARACTER_REF_DIR, "kenji.png"),
    ),
}


# ============================================================
# LOCATIONS
# ============================================================

LOCATIONS = {
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

    "village_day": Location(
        id="village_day",
        name="Japanese Village",
        description="Small Japanese village, Sengoku period. Cluster of wooden buildings around muddy central path. Smoke from cook fires. Farmers at work.",
        reference_path=os.path.join(LOCATION_REF_DIR, "village_day.png"),
    ),

    "village_samurai": Location(
        id="village_samurai",
        name="Village with Samurai",
        description="Japanese village with tension. Samurai have arrived. Villagers clearing path, fearful. Atmosphere of danger and oppression.",
        reference_path=os.path.join(LOCATION_REF_DIR, "village_samurai.png"),
    ),

    "forest_road": Location(
        id="forest_road",
        name="Forest Road",
        description="Forest road in feudal Japan. Cedar trees thick on both sides. Mountain path with switchbacks. Rain and mist.",
        reference_path=os.path.join(LOCATION_REF_DIR, "forest_road.png"),
    ),

    "castle_exterior": Location(
        id="castle_exterior",
        name="Castle Exterior",
        description="Japanese castle on a hill above a river. Gray stone walls rising from mist. Solid and permanent. Statement of power.",
        reference_path=os.path.join(LOCATION_REF_DIR, "castle_exterior.png"),
    ),

    "castle_interior": Location(
        id="castle_interior",
        name="Castle Interior",
        description="Interior of Japanese castle, tatami room. Sliding paper screens (shoji). Minimal furnishing. Window overlooking valley.",
        reference_path=os.path.join(LOCATION_REF_DIR, "castle_interior.png"),
    ),

    "garden_koi": Location(
        id="garden_koi",
        name="Koi Garden",
        description="Small Japanese garden within castle grounds. Koi pond with gold and white fish. Arranged rocks, bent pine tree. Autumn colors.",
        reference_path=os.path.join(LOCATION_REF_DIR, "garden_koi.png"),
    ),

    "temple_exterior": Location(
        id="temple_exterior",
        name="Mountain Temple",
        description="Small Buddhist temple in the mountains. Weathered wooden building with mossy roof. Bell in wooden frame. Surrounded by forest and mist.",
        reference_path=os.path.join(LOCATION_REF_DIR, "temple_exterior.png"),
    ),

    "sekigahara_sunset": Location(
        id="sekigahara_sunset",
        name="Sekigahara Battlefield",
        description="Sekigahara battlefield, months after the battle. Wide valley between mountains. Trampled grass recovering. Remnants of war. Sunset light.",
        reference_path=os.path.join(LOCATION_REF_DIR, "sekigahara_sunset.png"),
    ),
}


# ============================================================
# PANELS - PROLOGUE + CHAPTER 1
# ============================================================

PANELS = [
    # === PROLOGUE ===
    PanelSpec(
        id="pro_01_stars",
        chapter="prologue",
        panel_type="establishing",
        description="POV looking out through the curved observation window. The infinite void of space stretches before you. Stars drift like ash. You are alone with your thoughts.",
        characters=[],
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
        characters=[],
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
        location="beach_dawn",
        speaker="hana",
        mood="cautious_hope",
        additional_notes="Hana ahead on path, looking back at us. We are following her into the unknown.",
    ),
]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def check_missing():
    """Check which references need to be generated."""
    missing = {"characters": [], "locations": []}

    for char_id, char in CHARACTERS.items():
        if not char.reference_path or not os.path.exists(char.reference_path):
            missing["characters"].append(char_id)

    for loc_id, loc in LOCATIONS.items():
        if not loc.reference_path or not os.path.exists(loc.reference_path):
            missing["locations"].append(loc_id)

    return missing


def print_summary():
    """Print story summary."""
    print(f"\n{'='*50}")
    print(f"STORY: {STORY_TITLE}")
    print(f"ID: {STORY_ID}")
    print(f"{'='*50}")
    print(f"\nCharacters: {len(CHARACTERS)}")
    for cid, char in CHARACTERS.items():
        has_ref = "✓" if char.reference_path and os.path.exists(char.reference_path) else "✗"
        print(f"  [{has_ref}] {cid}: {char.name}")

    print(f"\nLocations: {len(LOCATIONS)}")
    for lid, loc in LOCATIONS.items():
        has_ref = "✓" if loc.reference_path and os.path.exists(loc.reference_path) else "✗"
        print(f"  [{has_ref}] {lid}: {loc.name}")

    print(f"\nPanels: {len(PANELS)}")
    chapters = {}
    for p in PANELS:
        chapters[p.chapter] = chapters.get(p.chapter, 0) + 1
    for ch, count in chapters.items():
        print(f"  {ch}: {count} panels")


async def generate_references(force=False):
    """Generate missing character and location references."""
    missing = check_missing()

    for char_id in missing["characters"]:
        char = CHARACTERS[char_id]
        prompt = f"""Manhwa/Korean webtoon style character portrait.

{char.description}

Portrait shot, shoulders up, facing camera.
Clean background. Professional character design reference quality.
Expressive manhwa style, clean linework, soft cel-shading.

NO TEXT IN IMAGE."""

        print(f"Generating character: {char_id}...")
        result = await generate_character_ref(char_id, prompt, force=force)
        print(f"  -> {result['path']}")

    for loc_id in missing["locations"]:
        loc = LOCATIONS[loc_id]
        prompt = f"""Manhwa/Korean webtoon style environment.

{loc.description}

Wide establishing shot. Rich detail.
Clean manhwa aesthetic, soft lighting.

NO TEXT IN IMAGE."""

        print(f"Generating location: {loc_id}...")
        result = await generate_location_ref(loc_id, prompt, force=force)
        print(f"  -> {result['path']}")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys
    from story_panels_test import generate_all_panels

    if len(sys.argv) < 2:
        print_summary()
        print("\nUsage:")
        print("  python story_shogun.py check    - Check missing references")
        print("  python story_shogun.py generate - Generate character/location refs")
        print("  python story_shogun.py panels   - Generate all panels")
        print("  python story_shogun.py all      - Generate everything")
        sys.exit(0)

    cmd = sys.argv[1]
    force = "--force" in sys.argv

    if cmd == "check":
        missing = check_missing()
        print("Missing references:")
        print(f"  Characters: {missing['characters']}")
        print(f"  Locations: {missing['locations']}")

    elif cmd == "generate":
        asyncio.run(generate_references(force))

    elif cmd == "panels":
        # Update the manifest with our data
        import story_manifest
        story_manifest.SHOGUN_CHARACTERS = CHARACTERS
        story_manifest.SHOGUN_LOCATIONS = LOCATIONS
        story_manifest.SHOGUN_PANELS = PANELS
        asyncio.run(generate_all_panels(force))

    elif cmd == "all":
        asyncio.run(generate_references(force))
        import story_manifest
        story_manifest.SHOGUN_CHARACTERS = CHARACTERS
        story_manifest.SHOGUN_LOCATIONS = LOCATIONS
        story_manifest.SHOGUN_PANELS = PANELS
        asyncio.run(generate_all_panels(force))

    else:
        print(f"Unknown command: {cmd}")
