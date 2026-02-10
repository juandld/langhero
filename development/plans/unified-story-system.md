# Unified Story System Architecture

## Core Principle
**The built-in Shogun story must use the EXACT same loading, rendering, and voice systems as user-imported stories.** No special-casing for built-in content.

---

## Story Package Format

Every story (built-in or imported) is a **Story Package**:

```
stories/
├── shogun/                     # Built-in Japanese story
│   ├── manifest.json           # Story metadata & configuration
│   ├── dialogues.json          # All dialogue sequences
│   ├── scenarios.json          # Interactive scenarios
│   ├── panels.json             # Visual panel definitions
│   └── assets/                 # Optional local assets
│       ├── cover.jpg
│       └── audio/
│
├── spanish-cafe/               # Example: Built-in Spanish story
│   ├── manifest.json
│   ├── dialogues.json
│   └── ...
│
└── user-imported/              # User-created stories
    ├── my-french-adventure/
    │   ├── manifest.json
    │   └── ...
    └── tokyo-night/
        └── ...
```

---

## Manifest Schema (manifest.json)

```json
{
  "$schema": "langhero-story-v1",
  "id": "shogun",
  "title": "The Shogun's Path",
  "language": "Japanese",
  "native_language": "English",
  "description": "1600 Japan. Shipwrecked. Survive.",
  "author": "LangHero",
  "version": "1.0.0",
  "cover_image": "assets/cover.jpg",

  "companion": {
    "name": "Bimbo",
    "voice": {
      "id": "shimmer",
      "instructions": "Speak with a bright, fairy-like quality - helpful and encouraging but slightly urgent, like Navi from Zelda.",
      "playback_rate": 1.1
    },
    "personality": "Helpful AI companion with fairy-like energy"
  },

  "narrator": {
    "voice": {
      "id": "alloy",
      "instructions": "Speak calmly and cinematically, with gravitas.",
      "playback_rate": 1.0
    }
  },

  "npc_voices": {
    "samurai": {
      "voice_id": "onyx",
      "instructions": "Speak with stern authority and warrior dignity."
    },
    "merchant": {
      "voice_id": "echo",
      "instructions": "Speak warmly and invitingly."
    },
    "default": {
      "voice_id": "alloy",
      "instructions": null
    }
  },

  "aesthetics": {
    "tutorial": {
      "mode": "holographic",
      "palette": {
        "primary": "#8b5cf6",
        "secondary": "#06b6d4",
        "background": "#0a0a1a"
      },
      "effects": ["scan-lines", "grid-overlay"]
    },
    "main": {
      "mode": "cinematic",
      "palette": {
        "primary": "#dc2626",
        "secondary": "#f59e0b",
        "background": "#1a1515"
      },
      "effects": ["film-grain", "letterbox"]
    }
  },

  "flow": {
    "tutorial": {
      "intro_dialogue": "tutorial_intro",
      "scenarios": [1, 2, 3, 4, 5],
      "min_complete": 2,
      "transition_dialogue": "tutorial_to_story"
    },
    "main": {
      "intro_dialogue": "story_intro",
      "drop_sequence": "drop",
      "awakening_dialogue": "awakening",
      "time_freeze_lesson": "time_freeze_lesson",
      "first_success": "first_success",
      "first_scenario_id": 100
    },
    "chapters": [
      {
        "id": "ch1",
        "title": "Shipwreck",
        "description": "Washed ashore in a foreign land",
        "scenarios": [100, 101, 102, 103]
      }
    ]
  },

  "settings": {
    "lives_per_scenario": 3,
    "time_freeze_enabled": true,
    "hint_system": true,
    "difficulty_scaling": true
  }
}
```

---

## Implementation: Backend Services

### 1. Story Loader Service (`services/story_loader.py`)

```python
class StoryLoader:
    """Universal story loader - same code path for all stories."""

    STORIES_DIR = "stories/"
    USER_STORIES_DIR = "stories/user-imported/"

    def list_stories(self) -> List[StoryManifest]:
        """List all available stories (built-in + user)."""
        pass

    def load_story(self, story_id: str) -> Story:
        """Load complete story package."""
        pass

    def load_manifest(self, story_id: str) -> StoryManifest:
        """Load just the manifest for quick access."""
        pass

    def load_dialogues(self, story_id: str) -> Dict[str, List[DialogueLine]]:
        """Load all dialogues for a story."""
        pass

    def load_scenarios(self, story_id: str) -> List[Scenario]:
        """Load all scenarios for a story."""
        pass

    def import_story(self, package: StoryPackage) -> str:
        """Import a new story, returns story_id."""
        pass

    def validate_story(self, package: StoryPackage) -> ValidationResult:
        """Validate story package before import."""
        pass
```

### 2. Voice Service (`services/story_voices.py`)

```python
class StoryVoiceService:
    """Get voice configuration from story manifest."""

    def get_companion_voice(self, story_id: str) -> VoiceConfig:
        """Get companion (Bimbo) voice for this story."""
        manifest = story_loader.load_manifest(story_id)
        return manifest.companion.voice

    def get_narrator_voice(self, story_id: str) -> VoiceConfig:
        """Get narrator voice for this story."""
        pass

    def get_npc_voice(self, story_id: str, npc_type: str) -> VoiceConfig:
        """Get NPC voice based on type/role."""
        pass

    def get_tts_params(self, story_id: str, speaker: str) -> TTSParams:
        """Get complete TTS parameters for any speaker."""
        pass
```

### 3. Aesthetic Service (`services/story_aesthetics.py`)

```python
class StoryAestheticService:
    """Get aesthetic configuration from story manifest."""

    def get_aesthetic(self, story_id: str, phase: str) -> AestheticConfig:
        """Get aesthetic for tutorial/main phase."""
        pass

    def get_palette(self, story_id: str, phase: str) -> ColorPalette:
        """Get color palette for current phase."""
        pass

    def get_effects(self, story_id: str, phase: str) -> List[str]:
        """Get visual effects for current phase."""
        pass
```

---

## Implementation: Frontend

### 1. Story Context Provider

```svelte
<!-- StoryProvider.svelte -->
<script>
  import { setContext, onMount } from 'svelte';
  import { writable } from 'svelte/store';

  export let storyId;

  const story = writable(null);
  const voiceConfig = writable(null);
  const aestheticConfig = writable(null);

  setContext('story', story);
  setContext('voiceConfig', voiceConfig);
  setContext('aestheticConfig', aestheticConfig);

  onMount(async () => {
    // Load story manifest
    const manifest = await loadStoryManifest(storyId);
    story.set(manifest);
    voiceConfig.set(manifest.companion.voice);
    aestheticConfig.set(manifest.aesthetics);
  });
</script>

<slot />
```

### 2. Voice-Aware Dialogue Component

```svelte
<!-- VoicedDialogue.svelte -->
<script>
  import { getContext } from 'svelte';
  import { getTTS } from '$lib/api';

  export let line;

  const story = getContext('story');
  const voiceConfig = getContext('voiceConfig');

  // Auto-play TTS using story's voice configuration
  $: if (line && $voiceConfig) {
    playTTS(line, $story.id, $voiceConfig);
  }

  async function playTTS(dialogueLine, storyId, config) {
    const speaker = dialogueLine.speaker?.toLowerCase();

    // Get voice config from story manifest
    const response = await getTTS({
      text: dialogueLine.text,
      story_id: storyId,
      speaker: speaker,
      sentiment: dialogueLine.sentiment,
    });

    // Play audio...
  }
</script>
```

### 3. Dynamic Aesthetic Loading

```svelte
<!-- DynamicAesthetic.svelte -->
<script>
  import { getContext } from 'svelte';

  export let phase = 'tutorial'; // or 'main'

  const aestheticConfig = getContext('aestheticConfig');

  $: currentAesthetic = $aestheticConfig?.[phase] || {};
  $: cssVars = buildCssVars(currentAesthetic.palette);
</script>

<div class="aesthetic-wrapper" style={cssVars} data-mode={currentAesthetic.mode}>
  {#if currentAesthetic.effects?.includes('scan-lines')}
    <div class="scan-lines"></div>
  {/if}
  {#if currentAesthetic.effects?.includes('film-grain')}
    <div class="film-grain"></div>
  {/if}
  <slot />
</div>
```

---

## API Endpoints

```
# Story Management
GET  /api/stories                      # List all stories
GET  /api/stories/{id}                 # Get story manifest
GET  /api/stories/{id}/dialogues       # Get all dialogues
GET  /api/stories/{id}/scenarios       # Get all scenarios
GET  /api/stories/{id}/voice-config    # Get voice configuration

# Story Import
POST /api/stories/import               # Import from JSON body
POST /api/stories/import/url           # Import from URL
POST /api/stories/import/upload        # Import from file upload
POST /api/stories/validate             # Validate without importing

# TTS (Story-Aware)
POST /api/tts                          # Now accepts story_id parameter
  {
    "text": "...",
    "story_id": "shogun",              # Uses story's voice config
    "speaker": "companion",            # companion, narrator, npc, samurai, etc.
    "sentiment": "excited"
  }
```

---

## Migration: Current → New System

### Step 1: Convert Shogun to Story Package
```bash
stories/
└── shogun/
    ├── manifest.json    # Extract from stories.json
    ├── dialogues.json   # Extract dialogues section
    ├── scenarios.json   # Copy from scenarios.json
    └── panels.json      # Extract panels section
```

### Step 2: Update Backend
1. Create `StoryLoader` service
2. Update `/api/stories` to use StoryLoader
3. Update `/api/tts` to accept `story_id`
4. Keep backward compatibility during transition

### Step 3: Update Frontend
1. Create `StoryProvider` context
2. Update `StoryOrchestrator` to use context
3. Update `DialogueOverlay` to use story voice config
4. Update `AestheticProvider` to use story aesthetic config

### Step 4: Remove Old System
1. Remove hardcoded `stories.json` loading
2. Remove `get_bimbo_voice()` hardcoding
3. All voice/aesthetic comes from story manifest

---

## Import Flow (User Stories)

```
User provides:
  - JSON file, URL, or paste

      ↓

Validation:
  - Schema validation
  - Required fields check
  - Scenario references valid
  - No malicious content

      ↓

Processing:
  - Generate unique story_id
  - Store in user-imported/
  - Index for discovery

      ↓

Available:
  - Appears in story list
  - Uses same systems as built-in
  - Can be shared via export
```

---

## Example: Creating a Spanish Story

```json
{
  "$schema": "langhero-story-v1",
  "id": "barcelona-cafe",
  "title": "Café Barcelona",
  "language": "Spanish",
  "description": "Navigate daily life in a Barcelona café",

  "companion": {
    "name": "Luna",
    "voice": {
      "id": "nova",
      "instructions": "Speak warmly like a friendly local showing you around. Light Spanish accent.",
      "playback_rate": 1.0
    }
  },

  "aesthetics": {
    "tutorial": {
      "mode": "holographic",
      "palette": {
        "primary": "#f59e0b",
        "secondary": "#ef4444",
        "background": "#1a1a2e"
      }
    },
    "main": {
      "mode": "cinematic",
      "palette": {
        "primary": "#ef4444",
        "secondary": "#f59e0b",
        "background": "#2d1f1f"
      }
    }
  },

  "flow": {
    "tutorial": {
      "intro_dialogue": "luna_intro",
      "scenarios": [1, 2],
      "min_complete": 1,
      "transition_dialogue": "first_day"
    },
    "main": {
      "intro_dialogue": "barcelona_intro",
      "first_scenario_id": 10
    }
  }
}
```

---

## Benefits

1. **Consistency**: Shogun uses same code as user imports
2. **Extensibility**: Easy to add new built-in stories
3. **User Empowerment**: Import/create custom stories
4. **Maintainability**: Single code path for all stories
5. **Customization**: Per-story voices, aesthetics, settings
6. **Sharing**: Stories are self-contained packages

---

## Priority Implementation Order

### Phase 1: Core Infrastructure (Required)
- [ ] Story manifest schema definition
- [ ] StoryLoader service
- [ ] Convert Shogun to story package
- [ ] Update API endpoints

### Phase 2: Voice Integration (Required)
- [ ] StoryVoiceService
- [ ] Update TTS to use story_id
- [ ] Frontend voice context

### Phase 3: Aesthetic Integration (Important)
- [ ] StoryAestheticService
- [ ] Dynamic palette loading
- [ ] Effect system

### Phase 4: Import System (Important)
- [ ] Import validation
- [ ] Import API endpoints
- [ ] Import UI in frontend

### Phase 5: Sharing (Nice to Have)
- [ ] Export story package
- [ ] Community gallery
- [ ] Story ratings/reviews
