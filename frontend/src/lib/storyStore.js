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

const BUILTIN_SCENARIOS = /** @type {Scenario[]} */ (scenarios);
let activeScenarios = BUILTIN_SCENARIOS;
let defaultScenario = /** @type {Scenario} */ (activeScenarios[0]);

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
  const { subscribe, set } = writable(normalizeScenario(defaultScenario));
  /** @type {number[]} */
  let history = [];

  /**
   * @param {Scenario[] | unknown} list
   * @returns {Scenario[]}
   */
  const coerceScenarioList = (list) => {
    if (!Array.isArray(list)) return [];
    /** @type {Scenario[]} */
    const out = [];
    for (const item of list) {
      if (item && typeof item === 'object' && typeof item.id === 'number') {
        out.push(/** @type {Scenario} */ (item));
      }
    }
    out.sort((a, b) => (a.id || 0) - (b.id || 0));
    return out;
  };

  return {
    subscribe,
    /**
     * Advance the story to a specific scenario ID and record history.
     * @param {number} id
     */
    goToScenario: (id) => {
      const nextScenario = /** @type {Scenario | undefined} */ (activeScenarios.find((s) => s.id === id));
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
      const prevScenario = /** @type {Scenario | undefined} */ (activeScenarios.find((s) => s.id === prevId));
      if (prevScenario) set(normalizeScenario(prevScenario));
    },
    reset: () => {
      history = [];
      set(normalizeScenario(defaultScenario));
    },
    /**
     * Load a new scenario list (e.g., imported story) and jump to its first scenario.
     * @param {Scenario[] | unknown} list
     * @param {{ startId?: number }} [opts]
     */
    loadScenarios: (list, opts = {}) => {
      const next = coerceScenarioList(list);
      if (!next.length) {
        console.error('loadScenarios: empty list');
        return;
      }
      activeScenarios = next;
      defaultScenario = /** @type {Scenario} */ (activeScenarios[0]);
      history = [];
      const startId = typeof opts?.startId === 'number' ? opts.startId : defaultScenario.id;
      const startScenario = /** @type {Scenario | undefined} */ (activeScenarios.find((s) => s.id === startId)) || defaultScenario;
      set(normalizeScenario(startScenario));
    },
    /** Switch back to the built-in demo scenarios. */
    useBuiltInScenarios: () => {
      activeScenarios = BUILTIN_SCENARIOS;
      defaultScenario = /** @type {Scenario} */ (activeScenarios[0]);
      history = [];
      set(normalizeScenario(defaultScenario));
    },
  };
}

export const storyStore = createStoryStore();
