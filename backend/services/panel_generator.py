"""
Panel Generator - Converts narrative dialogue into visual panel descriptions.

Takes story dialogues and generates structured panel descriptions that can be used for:
- AI image generation (DALL-E, Midjourney, Stable Diffusion)
- Art direction for artists
- Storyboard creation

Each panel includes:
- Scene description
- Characters present
- Mood/atmosphere
- Camera/composition
- Lighting notes
- Image generation prompt
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

import config
import providers


class ShotType(str, Enum):
    """Camera shot types for visual storytelling."""
    EXTREME_WIDE = "extreme_wide"      # Establishing shot, full environment
    WIDE = "wide"                       # Full scene with characters
    MEDIUM = "medium"                   # Waist-up, conversational
    MEDIUM_CLOSE = "medium_close"       # Chest-up, emotional
    CLOSE_UP = "close_up"               # Face, intense emotion
    EXTREME_CLOSE = "extreme_close"     # Eyes, detail focus
    OVER_SHOULDER = "over_shoulder"     # POV conversation
    POV = "pov"                         # First person view
    BIRDS_EYE = "birds_eye"             # Top-down
    LOW_ANGLE = "low_angle"             # Looking up, power
    HIGH_ANGLE = "high_angle"           # Looking down, vulnerability


class Mood(str, Enum):
    """Visual mood/atmosphere."""
    TENSE = "tense"
    PEACEFUL = "peaceful"
    MYSTERIOUS = "mysterious"
    DRAMATIC = "dramatic"
    HOPEFUL = "hopeful"
    DARK = "dark"
    WARM = "warm"
    COLD = "cold"
    CHAOTIC = "chaotic"
    SERENE = "serene"
    THREATENING = "threatening"
    ROMANTIC = "romantic"
    MELANCHOLIC = "melancholic"
    ENERGETIC = "energetic"


class TimeOfDay(str, Enum):
    """Lighting based on time."""
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    GOLDEN_HOUR = "golden_hour"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


@dataclass
class Character:
    """Character in a panel."""
    name: str
    role: str                           # protagonist, antagonist, npc, narrator
    position: str = "center"            # left, center, right, background
    expression: str = "neutral"         # emotional expression
    action: str = ""                    # what they're doing
    facing: str = "camera"              # camera, left, right, away


@dataclass
class PanelDescription:
    """Complete panel description for visual generation."""
    panel_id: str
    dialogue_key: str
    line_index: int

    # Scene
    location: str
    location_detail: str = ""
    time_of_day: TimeOfDay = TimeOfDay.MIDDAY
    weather: str = "clear"

    # Composition
    shot_type: ShotType = ShotType.MEDIUM
    camera_angle: str = "eye_level"
    focus_point: str = ""

    # Mood
    mood: Mood = Mood.PEACEFUL
    atmosphere: str = ""
    color_palette: List[str] = field(default_factory=list)

    # Characters
    characters: List[Character] = field(default_factory=list)

    # Visual elements
    key_objects: List[str] = field(default_factory=list)
    background_elements: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)  # rain, fog, particles, etc.

    # Style
    art_style: str = "cinematic"        # cinematic, manga, watercolor, etc.
    reference_notes: str = ""

    # Generated prompt
    image_prompt: str = ""
    negative_prompt: str = ""

    # Source
    original_text: str = ""
    speaker: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['shot_type'] = self.shot_type.value
        data['mood'] = self.mood.value
        data['time_of_day'] = self.time_of_day.value
        return data


# Story context for consistent panel generation
@dataclass
class StoryContext:
    """Maintains context across panels for consistency."""
    story_id: str
    title: str
    era: str = ""                       # "1600 Japan", "modern Tokyo", etc.
    primary_location: str = ""
    art_style: str = "cinematic"
    color_palette: List[str] = field(default_factory=list)
    recurring_characters: Dict[str, Character] = field(default_factory=dict)
    visual_themes: List[str] = field(default_factory=list)


def analyze_dialogue_line(
    line: dict,
    context: StoryContext,
    prev_panel: Optional[PanelDescription] = None,
) -> dict:
    """Analyze a single dialogue line for visual elements.

    Returns a dict with extracted visual information.
    """
    text = line.get("text", "")
    speaker = line.get("speaker", "").lower()
    sentiment = line.get("sentiment", "neutral")

    analysis = {
        "text": text,
        "speaker": speaker,
        "sentiment": sentiment,
        "is_narration": speaker in ("narration", "narrator", ""),
        "is_dialogue": speaker not in ("narration", "narrator", ""),
        "suggests_action": False,
        "suggests_location_change": False,
        "emotional_intensity": "medium",
        "visual_keywords": [],
    }

    # Extract visual keywords from text
    visual_keywords = []
    text_lower = text.lower()

    # Location hints
    location_words = ["beach", "shore", "ship", "castle", "village", "forest",
                      "mountain", "river", "road", "room", "hall", "temple",
                      "market", "street", "garden", "cliff", "cave", "port"]
    for word in location_words:
        if word in text_lower:
            visual_keywords.append(f"location:{word}")
            analysis["suggests_location_change"] = True

    # Weather/atmosphere hints
    weather_words = ["storm", "rain", "sun", "fog", "mist", "snow", "wind",
                     "thunder", "lightning", "clouds"]
    for word in weather_words:
        if word in text_lower:
            visual_keywords.append(f"weather:{word}")

    # Action hints
    action_words = ["run", "fight", "fall", "jump", "grab", "strike", "bow",
                    "kneel", "stand", "walk", "flee", "attack", "defend"]
    for word in action_words:
        if word in text_lower:
            visual_keywords.append(f"action:{word}")
            analysis["suggests_action"] = True

    # Emotional hints
    emotion_words = {
        "angry": "intense", "furious": "intense", "rage": "intense",
        "scared": "high", "terrified": "intense", "fear": "high",
        "happy": "medium", "joy": "high", "excited": "high",
        "sad": "medium", "crying": "high", "tears": "high",
        "calm": "low", "peaceful": "low", "quiet": "low",
        "shocked": "high", "surprised": "high", "stunned": "high",
    }
    for word, intensity in emotion_words.items():
        if word in text_lower:
            visual_keywords.append(f"emotion:{word}")
            analysis["emotional_intensity"] = intensity

    analysis["visual_keywords"] = visual_keywords

    return analysis


def determine_shot_type(analysis: dict, prev_panel: Optional[PanelDescription]) -> ShotType:
    """Determine the best camera shot based on content analysis."""

    # Narration often uses wider shots for scene-setting
    if analysis["is_narration"]:
        if analysis["suggests_location_change"]:
            return ShotType.EXTREME_WIDE
        return ShotType.WIDE

    # High emotional intensity = closer shots
    intensity = analysis["emotional_intensity"]
    if intensity == "intense":
        return ShotType.CLOSE_UP
    elif intensity == "high":
        return ShotType.MEDIUM_CLOSE

    # Action scenes
    if analysis["suggests_action"]:
        return ShotType.WIDE

    # Dialogue defaults to medium shots
    # But vary from previous to avoid monotony
    if prev_panel and prev_panel.shot_type == ShotType.MEDIUM:
        return ShotType.MEDIUM_CLOSE

    return ShotType.MEDIUM


def determine_mood(analysis: dict, sentiment: str) -> Mood:
    """Determine visual mood from analysis and sentiment."""

    sentiment_mood_map = {
        "warm": Mood.WARM,
        "friendly": Mood.WARM,
        "encouraging": Mood.HOPEFUL,
        "happy": Mood.WARM,
        "excited": Mood.ENERGETIC,
        "suspicious": Mood.MYSTERIOUS,
        "stern": Mood.TENSE,
        "angry": Mood.DRAMATIC,
        "threatening": Mood.THREATENING,
        "worried": Mood.TENSE,
        "sad": Mood.MELANCHOLIC,
        "calm": Mood.SERENE,
        "dramatic": Mood.DRAMATIC,
        "urgent": Mood.TENSE,
    }

    if sentiment in sentiment_mood_map:
        return sentiment_mood_map[sentiment]

    # Check visual keywords for mood hints
    keywords = analysis.get("visual_keywords", [])
    for kw in keywords:
        if "storm" in kw or "thunder" in kw:
            return Mood.DRAMATIC
        if "peaceful" in kw or "calm" in kw:
            return Mood.SERENE
        if "fear" in kw or "terror" in kw:
            return Mood.DARK

    return Mood.PEACEFUL


def generate_image_prompt(panel: PanelDescription, context: StoryContext) -> str:
    """Generate an AI image prompt from panel description."""

    parts = []

    # Art style
    parts.append(f"{context.art_style} style illustration")

    # Era/setting
    if context.era:
        parts.append(f"set in {context.era}")

    # Location
    location_desc = panel.location
    if panel.location_detail:
        location_desc += f", {panel.location_detail}"
    parts.append(location_desc)

    # Time and weather
    parts.append(f"{panel.time_of_day.value} lighting")
    if panel.weather != "clear":
        parts.append(panel.weather)

    # Characters
    for char in panel.characters:
        char_desc = f"{char.name}"
        if char.expression != "neutral":
            char_desc += f" with {char.expression} expression"
        if char.action:
            char_desc += f" {char.action}"
        parts.append(char_desc)

    # Mood/atmosphere
    parts.append(f"{panel.mood.value} atmosphere")
    if panel.atmosphere:
        parts.append(panel.atmosphere)

    # Shot type
    shot_descriptions = {
        ShotType.EXTREME_WIDE: "extreme wide shot, establishing shot",
        ShotType.WIDE: "wide shot, full scene",
        ShotType.MEDIUM: "medium shot, waist up",
        ShotType.MEDIUM_CLOSE: "medium close-up, chest up",
        ShotType.CLOSE_UP: "close-up, face focus",
        ShotType.EXTREME_CLOSE: "extreme close-up, detail shot",
        ShotType.OVER_SHOULDER: "over the shoulder shot",
        ShotType.POV: "first person POV",
        ShotType.LOW_ANGLE: "low angle shot, looking up",
        ShotType.HIGH_ANGLE: "high angle shot, looking down",
    }
    parts.append(shot_descriptions.get(panel.shot_type, "medium shot"))

    # Key objects
    if panel.key_objects:
        parts.append(f"featuring {', '.join(panel.key_objects)}")

    # Effects
    if panel.effects:
        parts.append(", ".join(panel.effects))

    # Color palette
    if panel.color_palette:
        parts.append(f"color palette: {', '.join(panel.color_palette)}")

    # Quality markers
    parts.append("highly detailed, cinematic composition, dramatic lighting")

    return ", ".join(parts)


def generate_negative_prompt(panel: PanelDescription) -> str:
    """Generate negative prompt for AI image generation."""
    negatives = [
        "blurry", "low quality", "distorted", "deformed",
        "bad anatomy", "bad proportions", "extra limbs",
        "text", "watermark", "signature", "logo",
        "modern elements", "anachronistic items",
    ]
    return ", ".join(negatives)


async def generate_panel_with_ai(
    line: dict,
    context: StoryContext,
    dialogue_key: str,
    line_index: int,
    prev_panel: Optional[PanelDescription] = None,
) -> PanelDescription:
    """Use AI to generate a detailed panel description."""

    text = line.get("text", "")
    speaker = line.get("speaker", "")
    sentiment = line.get("sentiment", "neutral")

    # Build prompt for AI
    prompt = f"""Analyze this dialogue line and generate a visual panel description for a {context.art_style} story set in {context.era}.

Dialogue: "{text}"
Speaker: {speaker or "Narration"}
Sentiment: {sentiment}
Story: {context.title}
Current location context: {context.primary_location}

Generate a JSON response with these fields:
{{
    "location": "specific location name",
    "location_detail": "additional environment details",
    "time_of_day": "dawn|morning|midday|afternoon|golden_hour|dusk|night|midnight",
    "weather": "weather conditions",
    "shot_type": "extreme_wide|wide|medium|medium_close|close_up|extreme_close|over_shoulder|pov|low_angle|high_angle",
    "mood": "tense|peaceful|mysterious|dramatic|hopeful|dark|warm|cold|chaotic|serene|threatening|romantic|melancholic|energetic",
    "atmosphere": "description of the atmosphere",
    "color_palette": ["color1", "color2", "color3"],
    "characters": [
        {{"name": "character name", "role": "protagonist|antagonist|npc", "position": "left|center|right", "expression": "emotion", "action": "what they're doing"}}
    ],
    "key_objects": ["important visual elements"],
    "background_elements": ["background details"],
    "effects": ["visual effects like rain, fog, particles"],
    "focus_point": "where the eye should be drawn",
    "reference_notes": "art direction notes"
}}

Return ONLY valid JSON, no other text."""

    try:
        # Use OpenAI for better JSON handling
        response = providers.openai_chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            temperature=0.3,
        )

        # Parse JSON response
        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        data = json.loads(response)

        # Build panel from AI response
        panel = PanelDescription(
            panel_id=f"{dialogue_key}_{line_index}",
            dialogue_key=dialogue_key,
            line_index=line_index,
            location=data.get("location", context.primary_location),
            location_detail=data.get("location_detail", ""),
            time_of_day=TimeOfDay(data.get("time_of_day", "midday")),
            weather=data.get("weather", "clear"),
            shot_type=ShotType(data.get("shot_type", "medium")),
            mood=Mood(data.get("mood", "peaceful")),
            atmosphere=data.get("atmosphere", ""),
            color_palette=data.get("color_palette", []),
            key_objects=data.get("key_objects", []),
            background_elements=data.get("background_elements", []),
            effects=data.get("effects", []),
            focus_point=data.get("focus_point", ""),
            art_style=context.art_style,
            reference_notes=data.get("reference_notes", ""),
            original_text=text,
            speaker=speaker,
        )

        # Parse characters
        for char_data in data.get("characters", []):
            panel.characters.append(Character(
                name=char_data.get("name", "Unknown"),
                role=char_data.get("role", "npc"),
                position=char_data.get("position", "center"),
                expression=char_data.get("expression", "neutral"),
                action=char_data.get("action", ""),
            ))

        # Generate image prompt
        panel.image_prompt = generate_image_prompt(panel, context)
        panel.negative_prompt = generate_negative_prompt(panel)

        return panel

    except Exception as e:
        print(f"AI panel generation failed: {e}")
        # Fallback to rule-based generation
        return generate_panel_fallback(line, context, dialogue_key, line_index, prev_panel)


def generate_panel_fallback(
    line: dict,
    context: StoryContext,
    dialogue_key: str,
    line_index: int,
    prev_panel: Optional[PanelDescription] = None,
) -> PanelDescription:
    """Fallback rule-based panel generation when AI is unavailable."""

    text = line.get("text", "")
    speaker = line.get("speaker", "")
    sentiment = line.get("sentiment", "neutral")

    # Analyze the line
    analysis = analyze_dialogue_line(line, context, prev_panel)

    # Determine visual properties
    shot_type = determine_shot_type(analysis, prev_panel)
    mood = determine_mood(analysis, sentiment)

    # Build character list
    characters = []
    if speaker and speaker.lower() not in ("narration", "narrator"):
        characters.append(Character(
            name=speaker.title(),
            role="protagonist" if speaker.lower() in ("player", "bimbo") else "npc",
            expression=sentiment if sentiment != "neutral" else "neutral",
        ))

    panel = PanelDescription(
        panel_id=f"{dialogue_key}_{line_index}",
        dialogue_key=dialogue_key,
        line_index=line_index,
        location=context.primary_location or "unspecified location",
        shot_type=shot_type,
        mood=mood,
        art_style=context.art_style,
        original_text=text,
        speaker=speaker,
        characters=characters,
        color_palette=context.color_palette,
    )

    # Generate prompts
    panel.image_prompt = generate_image_prompt(panel, context)
    panel.negative_prompt = generate_negative_prompt(panel)

    return panel


async def generate_panels_for_dialogue(
    dialogue_key: str,
    dialogue_lines: List[dict],
    context: StoryContext,
    use_ai: bool = True,
    consolidate: bool = True,
) -> List[PanelDescription]:
    """Generate panels for an entire dialogue sequence.

    Args:
        dialogue_key: Identifier for this dialogue sequence
        dialogue_lines: List of dialogue line dicts
        context: Story context for consistency
        use_ai: Whether to use AI for generation
        consolidate: Whether to merge similar consecutive panels

    Returns:
        List of panel descriptions
    """
    panels = []
    prev_panel = None

    for i, line in enumerate(dialogue_lines):
        if use_ai:
            panel = await generate_panel_with_ai(line, context, dialogue_key, i, prev_panel)
        else:
            panel = generate_panel_fallback(line, context, dialogue_key, i, prev_panel)

        panels.append(panel)
        prev_panel = panel

    if consolidate:
        panels = consolidate_panels(panels)

    return panels


def consolidate_panels(panels: List[PanelDescription]) -> List[PanelDescription]:
    """Merge consecutive panels with the same location/mood to reduce image count."""

    if len(panels) <= 1:
        return panels

    consolidated = []
    current_group = [panels[0]]

    for panel in panels[1:]:
        prev = current_group[-1]

        # Check if panels can be merged
        same_location = panel.location == prev.location
        same_mood = panel.mood == prev.mood
        same_shot_type = panel.shot_type == prev.shot_type

        # Similar panels can share an image
        if same_location and same_mood and len(current_group) < 3:
            current_group.append(panel)
        else:
            # Emit the representative panel for this group
            representative = current_group[0]
            representative.panel_id = f"{representative.dialogue_key}_{representative.line_index}-{current_group[-1].line_index}"
            consolidated.append(representative)
            current_group = [panel]

    # Don't forget the last group
    if current_group:
        representative = current_group[0]
        if len(current_group) > 1:
            representative.panel_id = f"{representative.dialogue_key}_{representative.line_index}-{current_group[-1].line_index}"
        consolidated.append(representative)

    return consolidated


def create_shogun_context() -> StoryContext:
    """Create the context for the Shogun story."""
    return StoryContext(
        story_id="shogun",
        title="The Shogun's Path",
        era="1600 Sengoku Japan",
        primary_location="coastal Japan",
        art_style="cinematic, film grain, Kurosawa-inspired",
        color_palette=["muted earth tones", "deep reds", "stormy grays", "gold accents"],
        visual_themes=["samurai", "shipwreck", "survival", "cultural clash"],
        recurring_characters={
            "player": Character(name="Player", role="protagonist", expression="determined"),
            "bimbo": Character(name="Bimbo", role="guide", expression="helpful"),
            "samurai": Character(name="Samurai", role="antagonist", expression="stern"),
        }
    )


# Export for API usage
def panels_to_json(panels: List[PanelDescription]) -> str:
    """Convert panels to JSON string."""
    return json.dumps([p.to_dict() for p in panels], indent=2, ensure_ascii=False)
