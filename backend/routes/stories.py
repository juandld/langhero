"""
Story API endpoints.

Stories define the narrative structure including tutorial, transitions, and main content.
"""
from fastapi import APIRouter, HTTPException
from services.stories import (
    list_stories,
    get_story,
    get_story_for_language,
    get_dialogue,
    get_story_dialogues,
    get_story_panels,
)

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.get("")
async def api_list_stories():
    """List all available stories.

    Returns: {stories: [{id, title, language, description, cover_image}]}
    """
    stories = list_stories()
    return {"stories": stories}


@router.get("/{story_id}")
async def api_get_story(story_id: str):
    """Get a story by ID with full details.

    Returns: Story object with tutorial, main, chapters structure
    """
    story = get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="story_not_found")
    return story


@router.get("/language/{language}")
async def api_get_story_by_language(language: str):
    """Get the default story for a language.

    Returns: Story object or 404
    """
    story = get_story_for_language(language)
    if not story:
        raise HTTPException(status_code=404, detail="no_story_for_language")
    return story


@router.get("/{story_id}/dialogues")
async def api_get_story_dialogues(story_id: str):
    """Get all dialogues referenced by a story.

    Returns: {dialogue_key: [dialogue lines]}
    """
    story = get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="story_not_found")

    dialogues = get_story_dialogues(story_id)
    return {"dialogues": dialogues}


@router.get("/{story_id}/dialogues/{dialogue_key}")
async def api_get_dialogue(story_id: str, dialogue_key: str):
    """Get a specific dialogue sequence.

    Returns: {dialogue: [lines]}
    """
    dialogue = get_dialogue(dialogue_key)
    if not dialogue:
        raise HTTPException(status_code=404, detail="dialogue_not_found")
    return {"dialogue": dialogue}


@router.get("/{story_id}/panels")
async def api_get_story_panels(story_id: str):
    """Get all panel definitions for a story.

    Returns: {panels: {panel_id: panel_data}}
    """
    panels = get_story_panels(story_id)
    return {"panels": panels}
