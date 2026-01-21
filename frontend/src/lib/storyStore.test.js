import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { storyStore } from './storyStore.js';

describe('storyStore', () => {
  beforeEach(() => {
    storyStore.useBuiltInScenarios();
  });

  it('exposes normalized scenario defaults', () => {
    const scenario = get(storyStore);
    expect(scenario).toHaveProperty('id');
    expect(typeof scenario.mode).toBe('string');
    expect(typeof scenario.lives).toBe('number');
    expect(typeof scenario.reward_points).toBe('number');
    expect(scenario.penalties && typeof scenario.penalties).toBe('object');
  });

  it('goToScenario + goBack track history', () => {
    const first = get(storyStore);
    storyStore.goToScenario(4);
    expect(get(storyStore).id).toBe(4);
    storyStore.goBack();
    expect(get(storyStore).id).toBe(first.id);
  });

  it('does not change state when scenario id is unknown', () => {
    const before = get(storyStore);
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    storyStore.goToScenario(999999);
    expect(get(storyStore).id).toBe(before.id);
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });

  it('loadScenarios swaps active list', () => {
    const imported = [
      { id: 10, mode: 'beginner', lives: 3, reward_points: 10, penalties: {}, options: [] },
      { id: 11, mode: 'advanced', lives: 2, reward_points: 15, penalties: {}, options: [] },
    ];
    storyStore.loadScenarios(imported);
    expect(get(storyStore).id).toBe(10);
    storyStore.goToScenario(11);
    expect(get(storyStore).id).toBe(11);
    storyStore.goBack();
    expect(get(storyStore).id).toBe(10);
  });
});
