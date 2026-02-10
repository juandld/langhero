"""
Story-to-Panels Adapter.

Converts any narrative (transcript, text, video description) into a
sequence of visual panels for manga/webtoon-style presentation.

Uses LLM to analyze narrative and generate appropriate panel descriptions.
"""

from __future__ import annotations

import json
import re
from typing import Optional, List
from dataclasses import asdict

from langchain_core.messages import HumanMessage

import config
import providers
from visual_styles import (
    Panel, VisualSequence, ArtStyle, PanelType,
    VisualEffect, Mood, build_image_prompt
)


def adapt_story_to_panels(
    narrative: str,
    *,
    title: str = "Scene",
    art_style: ArtStyle = ArtStyle.MANHWA,
    target_language: str = "Japanese",
    max_panels: int = 12,
    include_dialogue: bool = True,
) -> VisualSequence:
    """Convert a narrative text into a visual panel sequence.

    Args:
        narrative: The story text, transcript, or scene description
        title: Title for this sequence
        art_style: Default art style for panels
        target_language: The language being learned (for dialogue)
        max_panels: Maximum number of panels to generate
        include_dialogue: Whether to extract/generate dialogue

    Returns:
        VisualSequence with panels ready for image generation
    """
    prompt = f"""You are a manga/webtoon storyboard artist. Convert this narrative into a visual panel sequence.

NARRATIVE:
{narrative}

OUTPUT FORMAT:
Return a JSON array of panels. Each panel should have:
- "id": unique identifier (e.g., "panel_1")
- "type": one of "full", "wide", "tall", "split", "impact", "transition"
- "scene_description": detailed visual description for image generation (30-50 words)
- "mood": one of "warm", "cold", "tense", "peaceful", "mysterious", "dramatic", "hopeful"
- "effects": array of effects like "speed_lines", "impact_burst", "vignette", "rain", "frozen", "particles"
- "dialogue": the spoken line (in {target_language} if applicable), or null
- "dialogue_translation": English translation if dialogue is in another language, or null
- "speaker": who is speaking ("narrator", "bimbo", "npc", "player"), or null
- "character_expression": emotion shown ("angry", "surprised", "suspicious", "warm", "scared"), or null
- "duration_ms": how long to show (1000-5000, shorter for action, longer for dialogue)

GUIDELINES:
- Create {max_panels} or fewer panels
- Start with establishing shots, then move to details
- Use "impact" type for dramatic moments (blade, revelation)
- Use "wide" for establishing shots and environment
- Use "full" for character focus and emotional moments
- Use "transition" for scene changes (keep description simple)
- Vary panel types for visual interest
- Include effects sparingly for emphasis
- For tense moments: "vignette", "speed_lines"
- For magical/time-stop: "frozen", "particles"
- For weather: "rain"

Return ONLY valid JSON array, no markdown, no explanation."""

    try:
        # Try Gemini first
        response, _ = providers.invoke_google([
            HumanMessage(content=[{"type": "text", "text": prompt}])
        ])
        raw = str(getattr(response, "content", response))
    except Exception:
        # Fallback to OpenAI
        raw = providers.openai_chat([HumanMessage(content=prompt)])

    # Parse JSON response
    panels = _parse_panels_json(raw, art_style)

    return VisualSequence(
        id=f"seq_{hash(narrative) % 10000:04d}",
        title=title,
        panels=panels,
        default_style=art_style,
    )


def adapt_transcript_to_panels(
    transcript: str,
    *,
    speaker_map: Optional[dict] = None,
    art_style: ArtStyle = ArtStyle.MANHWA,
    max_panels: int = 15,
) -> VisualSequence:
    """Convert a dialogue transcript into visual panels.

    Args:
        transcript: Dialogue transcript with speaker labels
        speaker_map: Map speaker names to character types {"Speaker 1": "samurai"}
        art_style: Default art style
        max_panels: Maximum panels

    Returns:
        VisualSequence
    """
    speaker_info = ""
    if speaker_map:
        speaker_info = f"\nSpeaker mapping: {json.dumps(speaker_map)}"

    prompt = f"""You are a manga/webtoon storyboard artist. Convert this dialogue transcript into visual panels.

TRANSCRIPT:
{transcript}
{speaker_info}

Create a visual sequence that:
1. Shows the setting and characters
2. Captures key emotional moments
3. Visualizes the dialogue flow
4. Uses panel variety (wide for setting, impact for key moments)

OUTPUT: Return ONLY a JSON array of panels with these fields:
- "id", "type", "scene_description", "mood", "effects", "dialogue", "dialogue_translation", "speaker", "character_expression", "duration_ms"

Maximum {max_panels} panels. No markdown, just JSON."""

    try:
        response, _ = providers.invoke_google([
            HumanMessage(content=[{"type": "text", "text": prompt}])
        ])
        raw = str(getattr(response, "content", response))
    except Exception:
        raw = providers.openai_chat([HumanMessage(content=prompt)])

    panels = _parse_panels_json(raw, art_style)

    return VisualSequence(
        id=f"transcript_{hash(transcript) % 10000:04d}",
        title="Dialogue Scene",
        panels=panels,
        default_style=art_style,
    )


def adapt_scenario_to_panels(
    scenario: dict,
    *,
    art_style: ArtStyle = ArtStyle.MANHWA,
    include_options: bool = True,
) -> VisualSequence:
    """Convert a game scenario into visual panels.

    Args:
        scenario: Scenario dict with description, dialogue, options
        art_style: Art style
        include_options: Whether to show dialogue options

    Returns:
        VisualSequence for the scenario
    """
    setting = scenario.get("setting", "")
    description = scenario.get("description", "")
    dialogue_jp = scenario.get("character_dialogue_jp", "")
    dialogue_en = scenario.get("character_dialogue_en", "")
    options = scenario.get("options", []) if include_options else []

    prompt = f"""Convert this language learning scenario into manga/webtoon panels.

SCENARIO:
Setting: {setting}
Description: {description}
NPC says (Japanese): {dialogue_jp}
NPC says (English): {dialogue_en}
Player options: {json.dumps([o.get('text', '') for o in options])}

Create 3-5 panels that:
1. Establish the setting (wide shot)
2. Show the NPC speaking
3. Create tension/engagement for the player's response

OUTPUT: JSON array of panels with: id, type, scene_description, mood, effects, dialogue, dialogue_translation, speaker, character_expression, duration_ms

No markdown, just JSON."""

    try:
        response, _ = providers.invoke_google([
            HumanMessage(content=[{"type": "text", "text": prompt}])
        ])
        raw = str(getattr(response, "content", response))
    except Exception:
        raw = providers.openai_chat([HumanMessage(content=prompt)])

    panels = _parse_panels_json(raw, art_style)

    return VisualSequence(
        id=f"scenario_{scenario.get('id', 0)}",
        title=description[:50] if description else "Scene",
        panels=panels,
        default_style=art_style,
    )


def _parse_panels_json(raw: str, default_style: ArtStyle) -> List[Panel]:
    """Parse LLM response into Panel objects."""
    # Extract JSON array
    try:
        # Find JSON array in response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: create a single default panel
        return [Panel(
            id="panel_fallback",
            type=PanelType.FULL,
            scene_description="Scene from the narrative",
            art_style=default_style,
        )]

    panels = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        # Parse panel type
        panel_type = PanelType.FULL
        type_str = str(item.get("type", "full")).lower()
        try:
            panel_type = PanelType(type_str)
        except ValueError:
            pass

        # Parse mood
        mood = Mood.WARM
        mood_str = str(item.get("mood", "warm")).lower()
        try:
            mood = Mood(mood_str)
        except ValueError:
            pass

        # Parse effects
        effects = []
        for eff in item.get("effects", []):
            eff_str = str(eff).lower().replace(" ", "_")
            try:
                effects.append(VisualEffect(eff_str))
            except ValueError:
                pass

        panels.append(Panel(
            id=item.get("id", f"panel_{i}"),
            type=panel_type,
            scene_description=item.get("scene_description", ""),
            dialogue=item.get("dialogue"),
            dialogue_translation=item.get("dialogue_translation"),
            speaker=item.get("speaker"),
            art_style=default_style,
            mood=mood,
            effects=effects,
            character_expression=item.get("character_expression"),
            duration_ms=int(item.get("duration_ms", 3000)),
        ))

    return panels


def sequence_to_dict(sequence: VisualSequence) -> dict:
    """Convert a VisualSequence to a JSON-serializable dict."""
    return {
        "id": sequence.id,
        "title": sequence.title,
        "default_style": sequence.default_style.value,
        "default_mood": sequence.default_mood.value,
        "panels": [
            {
                "id": p.id,
                "type": p.type.value,
                "scene_description": p.scene_description,
                "dialogue": p.dialogue,
                "dialogue_translation": p.dialogue_translation,
                "speaker": p.speaker,
                "art_style": p.art_style.value,
                "mood": p.mood.value,
                "effects": [e.value for e in p.effects],
                "character_expression": p.character_expression,
                "character_position": p.character_position,
                "duration_ms": p.duration_ms,
                "transition": p.transition,
                "image_url": p.image_url,
            }
            for p in sequence.panels
        ],
    }


def adapt_dialogue_to_panels(
    dialogue_key: str,
    dialogue_lines: List[dict],
    *,
    story_context: str = "",
    aesthetic: str = "holographic",
    existing_panels: Optional[dict] = None,
) -> VisualSequence:
    """Convert story dialogue lines into visual panels.

    This analyzes dialogue content and generates appropriate panel descriptions
    for each beat of the narrative, considering speaker, sentiment, and flow.

    Args:
        dialogue_key: The dialogue identifier (e.g., "awakening")
        dialogue_lines: List of dialogue dicts with speaker, text, sentiment, sub
        story_context: Additional context about the story/setting
        aesthetic: "holographic" (tutorial) or "cinematic" (main story)
        existing_panels: Optional dict of pre-defined panels to reference

    Returns:
        VisualSequence with panels for each dialogue beat
    """
    # Build art style from aesthetic
    art_style = ArtStyle.MANHWA if aesthetic == "holographic" else ArtStyle.DRAMATIC

    # Build dialogue text for LLM
    dialogue_text = []
    for i, line in enumerate(dialogue_lines):
        speaker = line.get("speaker", "unknown")
        text = line.get("text", "")
        sentiment = line.get("sentiment", "")
        sub = line.get("sub", "")

        entry = f"{i+1}. [{speaker}] {text}"
        if sub:
            entry += f" (Translation hint: {sub})"
        if sentiment:
            entry += f" [mood: {sentiment}]"
        dialogue_text.append(entry)

    dialogue_str = "\n".join(dialogue_text)

    # Include existing panel info if available
    existing_info = ""
    if existing_panels:
        panel_descs = []
        for pid, pdata in existing_panels.items():
            desc = pdata.get("scene_description", "")
            mood = pdata.get("mood", "")
            panel_descs.append(f"- {pid}: {desc} (mood: {mood})")
        existing_info = f"\n\nAvailable pre-defined panels (you can reference these):\n" + "\n".join(panel_descs)

    # Aesthetic-specific guidance
    if aesthetic == "holographic":
        aesthetic_guide = """
Aesthetic: HOLOGRAPHIC (Tutorial/Future Setting)
- Blue/purple color palette, futuristic feel
- Soft glows, particle effects, clean lines
- Safe, simulation-like atmosphere
- Bimbo appears as a friendly glowing orb"""
    else:
        aesthetic_guide = """
Aesthetic: CINEMATIC (Main Story/Historical)
- Earth tones, dramatic lighting, film grain feel
- High tension, real stakes
- Characters are solid, no holographic shimmer
- Use vignette and rain effects for drama"""

    prompt = f"""You are a visual storytelling expert. Convert this dialogue sequence into manga/webtoon panel descriptions.

DIALOGUE KEY: {dialogue_key}
{aesthetic_guide}

STORY CONTEXT:
{story_context}

DIALOGUE LINES:
{dialogue_str}
{existing_info}

Generate panel descriptions for this dialogue. Consider:
1. Not every line needs its own panel - group related lines
2. Add establishing shots before dialogue starts
3. Create close-ups for emotional moments
4. Transition panels for scene changes
5. Match mood to speaker sentiment

OUTPUT: Return a JSON array of panels with:
- "id": unique identifier
- "type": "full" | "wide" | "tall" | "impact" | "transition"
- "scene_description": 30-50 word visual description for image generation
- "mood": "warm" | "cold" | "tense" | "peaceful" | "mysterious" | "dramatic" | "hopeful"
- "effects": array of "speed_lines" | "impact_burst" | "vignette" | "rain" | "frozen" | "particles"
- "dialogue_indices": which dialogue line numbers (1-indexed) this panel covers
- "speaker_focus": which speaker is featured (or "environment" for establishing)
- "character_expression": emotion shown if character visible
- "duration_ms": display time (2000-5000, longer for dialogue)

Generate 3-8 panels. Return ONLY valid JSON, no markdown."""

    try:
        response, _ = providers.invoke_google([
            HumanMessage(content=[{"type": "text", "text": prompt}])
        ])
        raw = str(getattr(response, "content", response))
    except Exception:
        raw = providers.openai_chat([HumanMessage(content=prompt)])

    panels = _parse_dialogue_panels_json(raw, art_style, dialogue_lines)

    return VisualSequence(
        id=f"dialogue_{dialogue_key}",
        title=dialogue_key.replace("_", " ").title(),
        panels=panels,
        default_style=art_style,
    )


def _parse_dialogue_panels_json(raw: str, default_style: ArtStyle, dialogue_lines: List[dict]) -> List[Panel]:
    """Parse LLM response for dialogue panels."""
    try:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: create one panel per speaker change
        return _generate_fallback_panels(dialogue_lines, default_style)

    panels = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        panel_type = PanelType.FULL
        type_str = str(item.get("type", "full")).lower()
        try:
            panel_type = PanelType(type_str)
        except ValueError:
            pass

        mood = Mood.WARM
        mood_str = str(item.get("mood", "warm")).lower()
        try:
            mood = Mood(mood_str)
        except ValueError:
            pass

        effects = []
        for eff in item.get("effects", []):
            eff_str = str(eff).lower().replace(" ", "_")
            try:
                effects.append(VisualEffect(eff_str))
            except ValueError:
                pass

        # Extract dialogue for this panel based on indices
        dialogue_indices = item.get("dialogue_indices", [])
        dialogue_text = None
        dialogue_translation = None
        speaker = item.get("speaker_focus")

        if dialogue_indices and len(dialogue_indices) > 0:
            # Get the first covered dialogue line
            idx = dialogue_indices[0] - 1  # Convert to 0-indexed
            if 0 <= idx < len(dialogue_lines):
                line = dialogue_lines[idx]
                dialogue_text = line.get("text")
                dialogue_translation = line.get("sub")
                if not speaker:
                    speaker = line.get("speaker")

        panels.append(Panel(
            id=item.get("id", f"panel_{i}"),
            type=panel_type,
            scene_description=item.get("scene_description", ""),
            dialogue=dialogue_text,
            dialogue_translation=dialogue_translation,
            speaker=speaker,
            art_style=default_style,
            mood=mood,
            effects=effects,
            character_expression=item.get("character_expression"),
            duration_ms=int(item.get("duration_ms", 3000)),
        ))

    return panels


def _generate_fallback_panels(dialogue_lines: List[dict], default_style: ArtStyle) -> List[Panel]:
    """Generate basic panels when LLM parsing fails."""
    panels = []
    prev_speaker = None

    for i, line in enumerate(dialogue_lines):
        speaker = line.get("speaker", "unknown")
        text = line.get("text", "")

        # Create panel on speaker change or every 2 lines
        if speaker != prev_speaker or i % 2 == 0:
            mood = Mood.WARM
            if speaker == "samurai":
                mood = Mood.TENSE
            elif speaker == "narration":
                mood = Mood.MYSTERIOUS

            panels.append(Panel(
                id=f"panel_{i}",
                type=PanelType.FULL,
                scene_description=f"{speaker} speaking: {text[:50]}...",
                dialogue=text,
                dialogue_translation=line.get("sub"),
                speaker=speaker,
                art_style=default_style,
                mood=mood,
                duration_ms=3000,
            ))

        prev_speaker = speaker

    return panels
