/**
 * Story Manager - Manages narrative flow through tutorial → story transitions.
 *
 * State machine:
 *   'loading' → 'intro' → 'tutorial' → 'tutorial_complete' → 'story_intro' → 'drop' → 'playing'
 */

import { writable, derived, get } from 'svelte/store';
import { apiFetch } from '$lib/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Storage keys
const STORY_PROGRESS_KEY = 'LANGHERO_STORY_PROGRESS_V1';

// Story states
export const STORY_STATES = {
  LOADING: 'loading',
  INTRO: 'intro',
  TUTORIAL: 'tutorial',
  TUTORIAL_COMPLETE: 'tutorial_complete',
  STORY_INTRO: 'story_intro',
  DROP: 'drop',
  AWAKENING: 'awakening',      // Beach awakening cutscene
  TIME_FREEZE: 'time_freeze',  // Bimbo teaches first phrase
  FIRST_CHALLENGE: 'first_challenge',  // Interactive speaking moment
  FIRST_SUCCESS: 'first_success',      // Success celebration
  PLAYING: 'playing',
};

// Create the main store
function createStoryManager() {
  const initial = {
    state: STORY_STATES.LOADING,
    story: null,
    dialogues: {},
    tutorialProgress: {
      completed: [],
      current: null,
    },
    currentDialogue: null,
    currentDialogueKey: null,
    dialogueIndex: 0,
  };

  const { subscribe, set, update } = writable(initial);

  // Load saved progress from localStorage
  function loadProgress() {
    try {
      const saved = localStorage.getItem(STORY_PROGRESS_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load story progress:', e);
    }
    return null;
  }

  // Save progress to localStorage
  function saveProgress(storyId, data) {
    try {
      const all = loadProgress() || {};
      all[storyId] = data;
      localStorage.setItem(STORY_PROGRESS_KEY, JSON.stringify(all));
    } catch (e) {
      console.warn('Failed to save story progress:', e);
    }
  }

  // Clear progress for a story (for replay)
  function clearProgress(storyId) {
    try {
      const all = loadProgress() || {};
      delete all[storyId];
      localStorage.setItem(STORY_PROGRESS_KEY, JSON.stringify(all));
    } catch (e) {
      console.warn('Failed to clear story progress:', e);
    }
  }

  return {
    subscribe,

    /**
     * Load a story by ID and initialize state
     */
    async loadStory(storyId, forceRestart = false) {
      update(s => ({ ...s, state: STORY_STATES.LOADING }));

      try {
        // Fetch story data
        const storyRes = await apiFetch(`${API_BASE}/api/stories/${storyId}`);
        if (!storyRes.ok) throw new Error('Failed to load story');
        const story = await storyRes.json();

        // Fetch dialogues
        const dialoguesRes = await apiFetch(`${API_BASE}/api/stories/${storyId}/dialogues`);
        const dialoguesData = dialoguesRes.ok ? await dialoguesRes.json() : { dialogues: {} };

        // Check for saved progress
        const savedProgress = forceRestart ? null : loadProgress()?.[storyId];

        let initialState = STORY_STATES.INTRO;
        let tutorialProgress = { completed: [], current: null };

        if (savedProgress && !forceRestart) {
          // Resume from saved state
          if (savedProgress.state === 'playing') {
            initialState = STORY_STATES.PLAYING;
          } else if (savedProgress.tutorialCompleted) {
            initialState = STORY_STATES.PLAYING;
          }
          tutorialProgress = savedProgress.tutorialProgress || tutorialProgress;
        }

        // Get the intro dialogue
        const introDialogueKey = story.tutorial?.intro_dialogue;
        const introDialogue = dialoguesData.dialogues?.[introDialogueKey] || [];

        update(() => ({
          state: initialState,
          story,
          dialogues: dialoguesData.dialogues || {},
          tutorialProgress,
          currentDialogue: initialState === STORY_STATES.INTRO ? introDialogue : null,
          currentDialogueKey: initialState === STORY_STATES.INTRO ? introDialogueKey : null,
          dialogueIndex: 0,
        }));

        return story;
      } catch (e) {
        console.error('Failed to load story:', e);
        update(s => ({ ...s, state: STORY_STATES.LOADING }));
        throw e;
      }
    },

    /**
     * Load story by language (gets default story for that language)
     */
    async loadStoryForLanguage(language, forceRestart = false) {
      try {
        const res = await apiFetch(`${API_BASE}/api/stories/language/${encodeURIComponent(language)}`);
        if (!res.ok) throw new Error('No story for language');
        const story = await res.json();
        return this.loadStory(story.id, forceRestart);
      } catch (e) {
        console.error('Failed to load story for language:', e);
        throw e;
      }
    },

    /**
     * Advance dialogue by one line
     */
    advanceDialogue() {
      update(s => {
        if (!s.currentDialogue) return s;
        const nextIndex = s.dialogueIndex + 1;
        if (nextIndex >= s.currentDialogue.length) {
          // Dialogue complete
          return { ...s, dialogueIndex: nextIndex };
        }
        return { ...s, dialogueIndex: nextIndex };
      });
    },

    /**
     * Go back one dialogue line
     */
    goBackDialogue() {
      update(s => {
        if (!s.currentDialogue) return s;
        const prevIndex = Math.max(0, s.dialogueIndex - 1);
        return { ...s, dialogueIndex: prevIndex };
      });
    },

    /**
     * Check if current dialogue is complete
     */
    isDialogueComplete() {
      const s = get({ subscribe });
      if (!s.currentDialogue) return true;
      return s.dialogueIndex >= s.currentDialogue.length;
    },

    /**
     * Get current dialogue line
     */
    getCurrentLine() {
      const s = get({ subscribe });
      if (!s.currentDialogue) return null;
      return s.currentDialogue[s.dialogueIndex] || null;
    },

    /**
     * Transition to tutorial phase (after intro dialogue)
     */
    startTutorial() {
      update(s => {
        const tutorialScenarios = s.story?.tutorial?.scenarios || [];
        const firstScenario = tutorialScenarios[0] || null;

        return {
          ...s,
          state: STORY_STATES.TUTORIAL,
          tutorialProgress: {
            ...s.tutorialProgress,
            current: firstScenario,
          },
          currentDialogue: null,
          currentDialogueKey: null,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Mark a tutorial scenario as complete
     */
    completeTutorialScenario(scenarioId) {
      update(s => {
        const completed = [...s.tutorialProgress.completed];
        if (!completed.includes(scenarioId)) {
          completed.push(scenarioId);
        }

        const minComplete = s.story?.tutorial?.min_complete || 2;
        const tutorialDone = completed.length >= minComplete;

        // Save progress
        if (s.story?.id) {
          saveProgress(s.story.id, {
            tutorialProgress: { ...s.tutorialProgress, completed },
            tutorialCompleted: tutorialDone,
            state: tutorialDone ? 'tutorial_complete' : 'tutorial',
          });
        }

        if (tutorialDone) {
          // Load transition dialogue
          const transitionKey = s.story?.tutorial?.transition_dialogue;
          const transitionDialogue = s.dialogues?.[transitionKey] || [];

          return {
            ...s,
            state: STORY_STATES.TUTORIAL_COMPLETE,
            tutorialProgress: { ...s.tutorialProgress, completed },
            currentDialogue: transitionDialogue,
            currentDialogueKey: transitionKey,
            dialogueIndex: 0,
          };
        }

        return {
          ...s,
          tutorialProgress: { ...s.tutorialProgress, completed },
        };
      });
    },

    /**
     * Transition to story intro (after tutorial transition dialogue)
     */
    startStoryIntro() {
      update(s => {
        const storyIntroKey = s.story?.main?.intro_dialogue;
        const storyIntroDialogue = s.dialogues?.[storyIntroKey] || [];

        return {
          ...s,
          state: STORY_STATES.STORY_INTRO,
          currentDialogue: storyIntroDialogue,
          currentDialogueKey: storyIntroKey,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Trigger the drop sequence
     */
    startDrop() {
      update(s => {
        const dropKey = s.story?.main?.drop_sequence;
        const dropDialogue = s.dialogues?.[dropKey] || [];

        return {
          ...s,
          state: STORY_STATES.DROP,
          currentDialogue: dropDialogue,
          currentDialogueKey: dropKey,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Start awakening cutscene (after drop)
     */
    startAwakening() {
      update(s => {
        const awakeningKey = 'awakening';
        const awakeningDialogue = s.dialogues?.[awakeningKey] || [];

        return {
          ...s,
          state: STORY_STATES.AWAKENING,
          currentDialogue: awakeningDialogue,
          currentDialogueKey: awakeningKey,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Start time freeze lesson (after awakening)
     * Bimbo teaches the first phrase while time is frozen
     */
    startTimeFreeze() {
      update(s => {
        const lessonKey = 'time_freeze_lesson';
        const lessonDialogue = s.dialogues?.[lessonKey] || [];

        return {
          ...s,
          state: STORY_STATES.TIME_FREEZE,
          currentDialogue: lessonDialogue,
          currentDialogueKey: lessonKey,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Start first interactive challenge (after time freeze lesson)
     * Player must speak the learned phrase
     */
    startFirstChallenge() {
      update(s => ({
        ...s,
        state: STORY_STATES.FIRST_CHALLENGE,
        currentDialogue: null,
        currentDialogueKey: null,
        dialogueIndex: 0,
      }));
    },

    /**
     * Start first success celebration (after completing challenge)
     */
    startFirstSuccess() {
      update(s => {
        const successKey = 'first_success';
        const successDialogue = s.dialogues?.[successKey] || [];

        return {
          ...s,
          state: STORY_STATES.FIRST_SUCCESS,
          currentDialogue: successDialogue,
          currentDialogueKey: successKey,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Begin main story gameplay
     */
    startPlaying() {
      update(s => {
        // Save that we're now in playing state
        if (s.story?.id) {
          saveProgress(s.story.id, {
            tutorialProgress: s.tutorialProgress,
            tutorialCompleted: true,
            state: 'playing',
          });
        }

        return {
          ...s,
          state: STORY_STATES.PLAYING,
          currentDialogue: null,
          currentDialogueKey: null,
          dialogueIndex: 0,
        };
      });
    },

    /**
     * Get the first scenario ID for the main story
     */
    getFirstScenarioId() {
      const s = get({ subscribe });
      return s.story?.main?.first_scenario_id || null;
    },

    /**
     * Get tutorial scenario IDs
     */
    getTutorialScenarios() {
      const s = get({ subscribe });
      return s.story?.tutorial?.scenarios || [];
    },

    /**
     * Get time freeze lesson dialogue
     */
    getTimeFreezeLesson() {
      const s = get({ subscribe });
      return s.dialogues?.['time_freeze_lesson'] || [];
    },

    /**
     * Get first success dialogue
     */
    getFirstSuccessDialogue() {
      const s = get({ subscribe });
      return s.dialogues?.['first_success'] || [];
    },

    /**
     * Reset story progress (for replay)
     */
    reset(storyId) {
      if (storyId) {
        clearProgress(storyId);
      }
      set({
        state: STORY_STATES.LOADING,
        story: null,
        dialogues: {},
        tutorialProgress: { completed: [], current: null },
        currentDialogue: null,
        currentDialogueKey: null,
        dialogueIndex: 0,
      });
    },

    /**
     * Skip directly to playing state (dev mode)
     */
    skipToPlaying() {
      update(s => ({
        ...s,
        state: STORY_STATES.PLAYING,
        currentDialogue: null,
        currentDialogueKey: null,
        dialogueIndex: 0,
      }));
    },
  };
}

export const storyManager = createStoryManager();

// Derived stores for convenience
export const storyState = derived(storyManager, $s => $s.state);
export const currentStory = derived(storyManager, $s => $s.story);
export const currentDialogue = derived(storyManager, $s => $s.currentDialogue);
export const currentDialogueKey = derived(storyManager, $s => $s.currentDialogueKey);
export const dialogueIndex = derived(storyManager, $s => $s.dialogueIndex);
export const tutorialProgress = derived(storyManager, $s => $s.tutorialProgress);

export const currentDialogueLine = derived(storyManager, $s => {
  if (!$s.currentDialogue) return null;
  return $s.currentDialogue[$s.dialogueIndex] || null;
});

export const isDialogueComplete = derived(storyManager, $s => {
  if (!$s.currentDialogue) return true;
  return $s.dialogueIndex >= $s.currentDialogue.length;
});

export const canGoBack = derived(storyManager, $s => {
  return $s.dialogueIndex > 0;
});
