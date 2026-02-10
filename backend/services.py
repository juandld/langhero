"""
Services module - Re-exports from modular services package.

This file maintains backward compatibility with existing imports.
All functionality has been moved to the services/ package.
"""

# Re-export all services for backward compatibility
from services import (
    # Scenario management
    get_scenario_by_id,
    list_scenarios,
    reload_scenarios,
    list_scenario_versions,
    save_scenarios_version,
    activate_scenario_version,

    # Interaction processing
    process_interaction,
    imitate_say,

    # Transcription
    transcribe_and_save,

    # Notes
    get_notes,

    # Suggestions
    generate_option_suggestions,

    # Video processing
    generate_scenarios_from_video,
    generate_scenarios_from_transcript,

    # Feedback
    generate_social_feedback,
)

# For any code that imports VOICE_NOTES_DIR directly
import os
VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))
