import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import ScenarioOptionsPanel from './ScenarioOptionsPanel.svelte';

describe('ScenarioOptionsPanel', () => {
  it('renders time-stop prep banner + safe translate copy', () => {
    const { html } = render(ScenarioOptionsPanel, {
      props: {
        mode: 'beginner',
        judgeFocus: 0,
        languageOverride: '',
        requireRepeat: false,
        selectedOption: null,
        lastHeard: '',
        evaluating: false,
        lives: 3,
        localSuggestions: null,
        speakingSuggestions: null,
        myNativeText: '',
        translating: false,
        isNativeRecording: false,
        fallbackOptions: [{ text: 'Yes', next_scenario: 2 }]
      }
    });
    expect(html).toContain('Time Stop tools');
    expect(html).toContain('Judge focus');
    expect(html).toContain('Learning-first');
    expect(html).toContain('Target language');
    expect(html).toContain('Translates while time is frozen — no lives at risk.');
    expect(html).toContain('Quick options');
    expect(html).toContain('Yes');
  });

  it('renders live-mode prep banner + safe translate copy', () => {
    const { html } = render(ScenarioOptionsPanel, {
      props: {
        mode: 'advanced',
        judgeFocus: 1,
        languageOverride: 'Spanish',
        requireRepeat: false,
        selectedOption: null,
        lastHeard: '',
        evaluating: false,
        lives: 3,
        localSuggestions: null,
        speakingSuggestions: null,
        myNativeText: '',
        translating: false,
        isNativeRecording: false,
        fallbackOptions: []
      }
    });
    expect(html).toContain('Live mode tools');
    expect(html).toContain('Judge focus');
    expect(html).toContain('Story-first');
    expect(html).toContain('Target language');
    expect(html).toContain('Translates without costing lives even while the live mic is active.');
  });

  it('renders repeat panel when repeat expected', () => {
    const { html } = render(ScenarioOptionsPanel, {
      props: {
        mode: 'beginner',
        judgeFocus: 0.5,
        languageOverride: '',
        requireRepeat: true,
        selectedOption: { next_scenario: 2, example: { native: 'Hello', target: 'こんにちは', pronunciation: 'konnichiwa' } },
        lastHeard: 'Hello',
        evaluating: true,
        lives: 2,
        localSuggestions: { question: 'What do you say?', options: [] },
        speakingSuggestions: null,
        myNativeText: '',
        translating: false,
        isNativeRecording: false,
        fallbackOptions: []
      }
    });
    expect(html).toContain('Say this');
    expect(html).toContain('こんにちは');
    expect(html).toContain('Lives: 2');
    expect(html).toContain('Heard: <em>Hello</em> …');
  });
});
