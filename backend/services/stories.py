"""
Story management service.

Stories define the narrative structure including tutorial, transitions, and main content.
"""
from __future__ import annotations

import os
import json
from typing import Optional, List, Dict, Any

# Load stories data
STORIES_PATH = os.path.join(os.path.dirname(__file__), '..', 'stories.json')
_stories_cache: Optional[Dict[str, Any]] = None


def _load_stories() -> Dict[str, Any]:
    """Load stories data from JSON file."""
    global _stories_cache
    if _stories_cache is not None:
        return _stories_cache

    try:
        with open(STORIES_PATH, 'r', encoding='utf-8') as f:
            _stories_cache = json.load(f)
    except Exception as e:
        print(f"Error loading stories.json: {e}")
        _stories_cache = {"stories": [], "dialogues": {}, "panels": {}}

    return _stories_cache


def reload_stories() -> None:
    """Force reload of stories data."""
    global _stories_cache
    _stories_cache = None
    _load_stories()


def list_stories() -> List[Dict[str, Any]]:
    """Get list of all available stories."""
    data = _load_stories()
    stories = data.get("stories", [])
    # Return summary info only
    return [
        {
            "id": s.get("id"),
            "title": s.get("title"),
            "language": s.get("language"),
            "description": s.get("description"),
            "cover_image": s.get("cover_image"),
        }
        for s in stories
    ]


def get_story(story_id: str) -> Optional[Dict[str, Any]]:
    """Get a story by ID with full details."""
    data = _load_stories()
    stories = data.get("stories", [])
    for s in stories:
        if s.get("id") == story_id:
            return s
    return None


def get_story_for_language(language: str) -> Optional[Dict[str, Any]]:
    """Get the default story for a language."""
    data = _load_stories()
    stories = data.get("stories", [])
    lang_lower = language.lower()
    for s in stories:
        if s.get("language", "").lower() == lang_lower:
            return s
    return None


def get_dialogue(dialogue_key: str) -> List[Dict[str, Any]]:
    """Get a dialogue sequence by key."""
    data = _load_stories()
    dialogues = data.get("dialogues", {})
    return dialogues.get(dialogue_key, [])


def get_story_dialogues(story_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get all dialogues referenced by a story."""
    story = get_story(story_id)
    if not story:
        return {}

    data = _load_stories()
    all_dialogues = data.get("dialogues", {})
    result = {}

    # Collect dialogue keys from story
    keys_to_fetch = set()

    tutorial = story.get("tutorial", {})
    if tutorial.get("intro_dialogue"):
        keys_to_fetch.add(tutorial["intro_dialogue"])
    if tutorial.get("transition_dialogue"):
        keys_to_fetch.add(tutorial["transition_dialogue"])

    main = story.get("main", {})
    if main.get("intro_dialogue"):
        keys_to_fetch.add(main["intro_dialogue"])
    if main.get("drop_sequence"):
        keys_to_fetch.add(main["drop_sequence"])
    if main.get("awakening_dialogue"):
        keys_to_fetch.add(main["awakening_dialogue"])
    if main.get("time_freeze_lesson"):
        keys_to_fetch.add(main["time_freeze_lesson"])
    if main.get("first_success"):
        keys_to_fetch.add(main["first_success"])

    # Also include standard dialogue keys that may be referenced
    standard_keys = ["awakening", "time_freeze_lesson", "first_success"]
    for key in standard_keys:
        if key in all_dialogues:
            keys_to_fetch.add(key)

    # Fetch the dialogues
    for key in keys_to_fetch:
        if key in all_dialogues:
            result[key] = all_dialogues[key]

    return result


def get_panel(story_id: str, panel_id: str) -> Optional[Dict[str, Any]]:
    """Get a panel definition for a story."""
    data = _load_stories()
    panels = data.get("panels", {})
    story_panels = panels.get(story_id, {})
    return story_panels.get(panel_id)


def get_story_panels(story_id: str) -> Dict[str, Dict[str, Any]]:
    """Get all panels for a story."""
    data = _load_stories()
    panels = data.get("panels", {})
    return panels.get(story_id, {})
