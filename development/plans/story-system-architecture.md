# Story System Architecture Plan

## Goal
Create a replicable, extensible story system that works for:
1. Built-in stories (Shogun, future storylines)
2. User-imported custom stories
3. Community-shared stories

---

## Current Structure (stories.json)

```json
{
  "stories": [...],      // Story metadata + structure
  "dialogues": {...},    // Dialogue sequences by key
  "panels": {...}        // Visual panels by story/key
}
```

---

## Proposed Story Schema

### Story Definition
```typescript
interface Story {
  id: string;                    // Unique identifier
  title: string;                 // Display title
  language: string;              // Target language (Japanese, Spanish, etc.)
  description: string;           // Short description
  cover_image: string;           // Cover art URL
  author?: string;               // Creator attribution
  version?: string;              // Schema version for compatibility

  // Voice Configuration
  voices: {
    companion: VoiceConfig;      // Bimbo/guide character
    narrator: VoiceConfig;       // Narration voice
    default_npc: VoiceConfig;    // Default for NPCs
  };

  // Aesthetic Configuration
  aesthetics: {
    tutorial: 'holographic' | 'cinematic' | 'custom';
    main: 'holographic' | 'cinematic' | 'custom';
    custom?: CustomAesthetic;    // For user-defined themes
  };

  // Story Structure
  tutorial: TutorialConfig;
  main: MainStoryConfig;

  // References
  dialogue_refs: string[];       // List of dialogue keys used
  panel_refs: string[];          // List of panel keys used
}

interface VoiceConfig {
  voice: string;                 // OpenAI voice: alloy, shimmer, nova, etc.
  instructions?: string;         // TTS instructions for character
  playback_rate?: number;        // Speed adjustment (1.0 = normal)
}

interface TutorialConfig {
  intro_dialogue: string;        // Dialogue key for intro
  scenarios: number[];           // Tutorial scenario IDs
  min_complete: number;          // Required completions
  transition_dialogue: string;   // Dialogue key for transition
  aesthetic: string;
}

interface MainStoryConfig {
  intro_dialogue: string;        // Story intro dialogue key
  drop_sequence: string;         // Time travel transition
  awakening_dialogue: string;    // First cutscene
  time_freeze_lesson: string;    // Tutorial on time-freeze
  first_success: string;         // Success feedback
  first_scenario_id: number;     // Starting scenario
  aesthetic: string;
  chapters: Chapter[];
}

interface Chapter {
  id: string;
  title: string;
  description: string;
  scenarios: number[];
}
```

---

## Implementation Tasks

### Phase 1: Story Service Refactor
1. **Create `services/story_loader.py`**
   - Load stories from multiple sources (built-in, user, URL)
   - Validate against schema
   - Merge dialogues and panels

2. **Update `services/stories.py`**
   - Use story_loader for all story operations
   - Support story registration/unregistration
   - Handle story updates

### Phase 2: Voice System Integration
1. **Create `services/story_voices.py`**
   - Get voice config for any story character
   - Support per-story voice overrides
   - Fallback to defaults

2. **Update TTS routes**
   - Accept `story_id` parameter
   - Use story-specific voice configs
   - Cache per-story voice settings

### Phase 3: Import System
1. **Create story import format**
   ```
   story-package/
   ├── story.json          # Main story definition
   ├── dialogues.json      # All dialogues
   ├── scenarios.json      # Scenarios for this story
   ├── panels.json         # Panel definitions
   └── assets/             # Images, audio (optional)
   ```

2. **Import API endpoints**
   - `POST /api/stories/import` - Import from JSON
   - `POST /api/stories/import/url` - Import from URL
   - `POST /api/stories/import/file` - Import from upload

3. **Validation & sanitization**
   - Validate all required fields
   - Sanitize user content
   - Check scenario references

### Phase 4: Frontend Adaptation
1. **Story selection UI**
   - List available stories
   - Show import option
   - Preview before starting

2. **Dynamic aesthetic loading**
   - Load aesthetic config from story
   - Apply custom themes
   - Handle missing assets gracefully

3. **Voice configuration UI**
   - Allow voice testing
   - Save preferences per-story

---

## Migration Path

### Current stories.json → New Format
1. Split into separate files:
   - `stories/shogun/story.json`
   - `stories/shogun/dialogues.json`
   - `stories/shogun/scenarios.json`

2. Add voice configurations
3. Add aesthetic configs
4. Update API to load from new structure

### Backward Compatibility
- Keep supporting single stories.json
- Auto-detect format on load
- Migrate on first edit

---

## Voice Configuration Examples

### Shogun Story (Current)
```json
{
  "voices": {
    "companion": {
      "voice": "shimmer",
      "instructions": "Speak with a bright, fairy-like quality...",
      "playback_rate": 1.1
    },
    "narrator": {
      "voice": "alloy",
      "instructions": "Speak calmly and cinematically"
    },
    "default_npc": {
      "voice": "onyx",
      "instructions": "Speak with the dignity of a samurai"
    }
  }
}
```

### Spanish Travel Story (Example)
```json
{
  "voices": {
    "companion": {
      "voice": "nova",
      "instructions": "Speak warmly like a friendly tour guide",
      "playback_rate": 1.0
    },
    "narrator": {
      "voice": "echo",
      "instructions": "Speak with a warm, inviting tone"
    },
    "default_npc": {
      "voice": "nova",
      "instructions": "Speak naturally with native Spanish rhythm"
    }
  }
}
```

---

## API Endpoints (New)

```
GET  /api/stories                    # List all stories
GET  /api/stories/{id}               # Get story details
GET  /api/stories/{id}/dialogues     # Get all dialogues
GET  /api/stories/{id}/voice-config  # Get voice configuration
POST /api/stories/import             # Import new story
POST /api/stories/{id}/voice-config  # Update voice config (user prefs)
```

---

## Priority Order

1. **High**: Story schema definition + validation
2. **High**: Voice config per story
3. **Medium**: Story import from JSON
4. **Medium**: Story directory structure
5. **Low**: Import from URL
6. **Low**: Community sharing

---

## Notes

- Stories should be self-contained when exported
- User progress saved separately from story definition
- Voice configs can be overridden per-user
- Aesthetic themes loaded dynamically
- All text content should support localization keys
