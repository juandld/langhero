import { writable } from 'svelte/store';
import scenarios from '$lib/test/scenarios.json';

/**
 * @typedef {Object} Scenario
 * @property {number} id
 * @property {string} [mode]
 * @property {number} [lives]
 * @property {number} [reward_points]
 * @property {Record<string, Record<string, number>>} [penalties]
 */

const DEFAULT_SCENARIO = /** @type {Scenario} */ (scenarios[0]);

/**
 * Ensure mode, lives, reward, and penalties are present with sensible defaults.
 * @param {Scenario} raw
 * @returns {Scenario}
 */
function normalizeScenario(raw) {
  const mode = raw?.mode || 'beginner';
  const lives = typeof raw?.lives === 'number' ? raw.lives : mode === 'advanced' ? 2 : 3;
  const reward = typeof raw?.reward_points === 'number' ? raw.reward_points : mode === 'advanced' ? 15 : 10;
  const penalties = raw?.penalties || {};
  return {
    ...raw,
    mode,
    lives,
    reward_points: reward,
    penalties,
  };
}

function createStoryStore() {
  const { subscribe, set } = writable(normalizeScenario(DEFAULT_SCENARIO));
  /** @type {number[]} */
  let history = [];

  return {
    subscribe,
    /**
     * Advance the story to a specific scenario ID and record history.
     * @param {number} id
     */
    goToScenario: (id) => {
      const nextScenario = /** @type {Scenario | undefined} */ (scenarios.find((s) => s.id === id));
      if (!nextScenario) {
        console.error(`Scenario with id ${id} not found.`);
        return;
      }
      let currentId;
      const unsub = subscribe((value) => { currentId = value?.id; });
      unsub();
      if (typeof currentId === 'number') {
        history.push(currentId);
      }
      set(normalizeScenario(nextScenario));
    },
    /** Dev helper to step back */
    goBack: () => {
      const prevId = history.pop();
      if (typeof prevId !== 'number') return;
      const prevScenario = /** @type {Scenario | undefined} */ (scenarios.find((s) => s.id === prevId));
      if (prevScenario) set(normalizeScenario(prevScenario));
    },
    reset: () => {
      history = [];
      set(normalizeScenario(DEFAULT_SCENARIO));
    },
  };
}

export const storyStore = createStoryStore();
