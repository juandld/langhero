"""
Panel generation using the Story Manifest system.

Ensures character consistency by:
1. Using all character references for each panel
2. Including detailed character descriptions in prompts
3. Tracking which characters appear where
"""

import asyncio
from image_gen_google import generate_image
from story_manifest import (
    SHOGUN_CHARACTERS,
    SHOGUN_LOCATIONS,
    SHOGUN_PANELS,
    get_panel_references,
    get_panel_character_descriptions,
    PanelSpec,
)
from prompt_builder import (
    BASE_STYLE,
    HOLOGRAPHIC_STYLE,
    CINEMATIC_STYLE,
    TIME_FREEZE_STYLE,
    UNIVERSAL_CONSTRAINTS,
    HISTORICAL_CONSTRAINTS,
    HOLOGRAPHIC_CONSTRAINTS,
)
import os

PANEL_DIR = os.path.join(os.path.dirname(__file__), "..", "image_cache", "panels")


def build_manifest_prompt(panel: PanelSpec) -> str:
    """Build a constraint-based prompt from panel spec."""

    # Determine aspect ratio based on panel type
    aspect_map = {
        "establishing": ("wide", "16:9"),
        "pov": ("wide", "16:9"),
        "dialogue": ("square", "1:1"),
        "emotional": ("square", "1:1"),
        "action": ("tall", "9:16"),
        "time_freeze": ("tall", "9:16"),
    }
    aspect_name, aspect_ratio = aspect_map.get(panel.panel_type, ("square", "1:1"))

    # WORK SURFACE
    work_surface = f"Create a single manhwa panel. {aspect_ratio} aspect ratio, {aspect_name} composition."

    # LAYOUT based on panel type
    layout_map = {
        "establishing": "Wide establishing shot, POV perspective. Environment focus.",
        "pov": "First-person POV shot. The viewer IS the protagonist looking at the scene.",
        "dialogue": "Medium shot, POV perspective. Focus on character(s) facing the viewer.",
        "emotional": "Close-up shot. Intense focus on facial expression and emotion.",
        "action": "Dynamic action shot, POV. Movement and energy. The action comes toward the viewer.",
        "time_freeze": "Time freeze moment. Frozen world (blue tint) with Bimbo as only color/motion.",
    }
    layout = layout_map.get(panel.panel_type, "Standard composition.")

    # COMPONENTS - characters with full descriptions
    components = []
    char_descriptions = get_panel_character_descriptions(panel, SHOGUN_CHARACTERS)
    if char_descriptions:
        components.append(char_descriptions)

    # Add location
    if panel.location:
        loc = SHOGUN_LOCATIONS.get(panel.location)
        if loc:
            components.append(f"• Location: {loc.description}")

    components_str = "\n".join(components) if components else "• Scene as described"

    # STYLE
    if panel.is_holographic:
        style = f"{BASE_STYLE}\n{HOLOGRAPHIC_STYLE}"
    elif panel.is_time_freeze:
        style = f"{BASE_STYLE}\n{TIME_FREEZE_STYLE}"
    else:
        style = f"{BASE_STYLE}\n{CINEMATIC_STYLE}"

    # CONSTRAINTS
    constraints = UNIVERSAL_CONSTRAINTS
    if not panel.is_holographic:
        constraints += HISTORICAL_CONSTRAINTS
    if panel.is_holographic or panel.is_time_freeze:
        constraints += HOLOGRAPHIC_CONSTRAINTS

    # SOURCE MATERIAL
    source = panel.description
    if panel.additional_notes:
        source += f"\n\n{panel.additional_notes}"

    # INTERPRETATION
    mood_interpretations = {
        "contemplative": "Convey quiet reflection, solitude, peace in stillness.",
        "warm": "Convey warmth, connection, comfort despite circumstances.",
        "tense": "Convey tension, stakes rising, pivotal moment.",
        "disoriented": "Convey confusion, vulnerability, waking to danger.",
        "threatening": "Convey threat, survival instinct, danger approaching.",
        "terror": "Convey raw fear, fight or flight, moment of truth.",
        "tense_hope": "Convey desperate hope, words as survival, tension breaking.",
        "judgment": "Convey being evaluated, fate in another's hands.",
        "hopeful": "Convey relief, connection made, first success.",
        "cautious_hope": "Convey guarded optimism, journey beginning, trust forming.",
    }
    interpretation = mood_interpretations.get(panel.mood, "Convey the scene naturally.")

    # Assemble prompt
    prompt = f"""WORK SURFACE: {work_surface}

LAYOUT: {layout}

COMPONENTS:
{components_str}

STYLE: {style}

CONSTRAINTS:
{constraints}

SOURCE MATERIAL:
{source}

INTERPRETATION:
{interpretation}"""

    return prompt


async def generate_panel_from_manifest(panel: PanelSpec, force: bool = False) -> dict:
    """Generate a panel using the manifest system."""

    # Get all reference images for this panel
    references = get_panel_references(panel, SHOGUN_CHARACTERS, SHOGUN_LOCATIONS)

    # Build prompt
    prompt = build_manifest_prompt(panel)

    # Output path
    chapter_dir = os.path.join(PANEL_DIR, panel.chapter)
    os.makedirs(chapter_dir, exist_ok=True)
    output_path = os.path.join(chapter_dir, f"{panel.id}.png")

    # Check cache
    if not force and os.path.exists(output_path):
        return {"panel_id": panel.id, "path": output_path, "cached": True}

    # Generate
    result = await generate_image(
        prompt=prompt,
        reference_images=references if references else None,
        output_path=output_path,
        force=force,
    )

    return {
        "panel_id": panel.id,
        "path": result["path"],
        "cached": result["cached"],
        "references_used": len(references),
    }


async def generate_all_panels(force: bool = False):
    """Generate all panels from the manifest."""

    results = []

    for panel in SHOGUN_PANELS:
        refs = get_panel_references(panel, SHOGUN_CHARACTERS, SHOGUN_LOCATIONS)
        print(f"Generating {panel.id}...")
        print(f"  Characters: {panel.characters}")
        print(f"  References: {len(refs)} images")

        try:
            result = await generate_panel_from_manifest(panel, force)
            results.append(result)
            cached_str = "(cached)" if result.get("cached") else ""
            print(f"  -> {result['path']} {cached_str}")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results.append({"panel_id": panel.id, "error": str(e)})

    return results


async def generate_single_panel(panel_id: str, force: bool = False):
    """Generate a single panel by ID."""

    panel = next((p for p in SHOGUN_PANELS if p.id == panel_id), None)
    if not panel:
        print(f"Panel not found: {panel_id}")
        return None

    refs = get_panel_references(panel, SHOGUN_CHARACTERS, SHOGUN_LOCATIONS)
    prompt = build_manifest_prompt(panel)

    print(f"Generating {panel_id}...")
    print(f"Characters: {panel.characters}")
    print(f"References: {[os.path.basename(r) for r in refs]}")
    print(f"\nPrompt preview:\n{prompt[:600]}...")

    try:
        result = await generate_panel_from_manifest(panel, force)
        print(f"\n  -> {result['path']}")
        return result
    except Exception as e:
        print(f"  -> ERROR: {e}")
        return {"panel_id": panel_id, "error": str(e)}


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]

    if args:
        # Generate single panel
        panel_id = args[0]
        asyncio.run(generate_single_panel(panel_id, force))
    else:
        # Generate all panels
        results = asyncio.run(generate_all_panels(force))
        success = len([r for r in results if "error" not in r])
        print(f"\nGenerated {success}/{len(SHOGUN_PANELS)} panels")
