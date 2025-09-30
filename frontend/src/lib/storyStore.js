import { writable } from 'svelte/store';
import scenarios from '$lib/test/scenarios.json';

function createStoryStore() {
  const { subscribe, set, update } = writable(scenarios[0]);
  let history = [];

  return {
    subscribe,
    // Advance the story to a specific scenario ID and record history
    goToScenario: (id) => {
      const nextScenario = scenarios.find(s => s.id === id);
      if (nextScenario) {
        // record current id before moving
        let currentId;
        const unsub = subscribe(v => { currentId = v?.id; });
        unsub();
        if (currentId != null) history.push(currentId);
        set(nextScenario);
      } else {
        console.error(`Scenario with id ${id} not found.`);
      }
    },
    // Go back to the previous scenario (dev helper)
    goBack: () => {
      if (history.length === 0) return;
      const prevId = history.pop();
      const prev = scenarios.find(s => s.id === prevId);
      if (prev) set(prev);
    },
    // Reset to the beginning
    reset: () => { history = []; set(scenarios[0]); }
  };
}

export const storyStore = createStoryStore();
